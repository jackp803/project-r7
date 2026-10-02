"""Bounded acquisition queue with deadline priority, independent of entry bars."""
from datetime import datetime, timedelta, timezone
from queue import Queue, Empty, Full

from execution.models import require_utc
from .service import PaperRuntime, PaperMarketEvent


class PaperScheduler:
    def __init__(self, runtime, *, maximum_pending_events=32):
        if not isinstance(runtime, PaperRuntime) or type(maximum_pending_events) is not int or not 1<=maximum_pending_events<=256:
            raise ValueError('Actual Paper runtime and bounded acquisition queue required')
        self.runtime=runtime; self._events=Queue(maximum_pending_events)
        self.interval=runtime.service.simulation.as_dict()['protection_poll_seconds']
        self.acquisition_status='NOT_CONNECTED'

    @property
    def pending_events(self): return self._events.qsize()

    def submit_event(self, event):
        if not isinstance(event, PaperMarketEvent): raise ValueError('Actual E1 market event required')
        try: self._events.put_nowait(event)
        except Full:
            self.acquisition_status='MARKET_QUEUE_FULL'
            return False
        self.acquisition_status='EVENT_QUEUED'
        return True

    def _deadlines(self, now):
        state=self.runtime.service.process.recover(self.runtime.run_id).state['runtime']
        due=[]
        if state['exit_anchor'] and state['position']['lifecycle_state']!='CLOSED':
            due.append(datetime.fromisoformat(state['exit_anchor']['payload']['hold_deadline'].replace('Z','+00:00')))
        if state['plan'] and state['position'] is None:
            due.append(datetime.fromisoformat(state['plan']['expires_at'].replace('Z','+00:00')))
        return tuple(due)

    def tick(self):
        now=self.runtime.service.clock(); require_utc(now,'scheduler now')
        epoch=datetime(1970,1,1,tzinfo=timezone.utc)
        slot=int((now-epoch).total_seconds())//self.interval*self.interval
        deadlines={epoch+timedelta(seconds=slot)}
        deadlines.update(due for due in self._deadlines(now) if due<=now)
        outcomes=[self.runtime.on_deadline(due) for due in sorted(deadlines)]
        # One bounded acquisition item per tick prevents a fast feed starving
        # protection. Network acquisition is supplied by a separate producer.
        try: event=self._events.get_nowait()
        except Empty: return tuple(outcomes)
        outcomes.append(self.runtime.on_market_event(event))
        self._events.task_done()
        return tuple(outcomes)

    def next_wait_seconds(self):
        now=self.runtime.service.clock(); require_utc(now,'scheduler now')
        epoch=datetime(1970,1,1,tzinfo=timezone.utc)
        seconds=(now-epoch).total_seconds()
        next_poll=epoch+timedelta(seconds=(int(seconds)//self.interval+1)*self.interval)
        future=[due for due in self._deadlines(now) if due>now]
        remaining=(min([next_poll]+future)-now).total_seconds()
        return max(.001,min(self.interval,remaining))

    def run(self, stop_event):
        if not callable(getattr(stop_event,'is_set',None)) or not callable(getattr(stop_event,'wait',None)):
            raise ValueError('Explicit scheduler stop signal required')
        while not stop_event.is_set():
            self.tick()
            stop_event.wait(.001 if self.pending_events else self.next_wait_seconds())
