"""Cooperative service stop; signal handlers never interrupt an owner transaction."""
import math
import signal
import threading
import time


class ManagedStop:
    def __init__(self):
        self._event=threading.Event()
        self._signal_requested=False
        self._previous=None
        self._handler=self._on_signal
        self.first_signal=None

    @property
    def requested(self):return self._signal_requested or self._event.is_set()

    def request(self):self._event.set()

    def _on_signal(self,number,_frame):
        if self.first_signal is None:self.first_signal=number
        # No Event.set()/lock: a signal may interrupt Event.wait() while its
        # non-reentrant condition lock is held by this same main thread.
        self._signal_requested=True

    def wait(self,seconds):
        if (isinstance(seconds,bool) or not isinstance(seconds,(int,float))
                or not math.isfinite(seconds) or not 0<=seconds<=5):
            raise ValueError('BOUNDED_STOP_WAIT_REQUIRED')
        deadline=time.monotonic()+seconds
        while not self.requested:
            remaining=deadline-time.monotonic()
            if remaining<=0:return False
            self._event.wait(min(0.1,remaining))
        return True

    def __enter__(self):
        if threading.current_thread() is not threading.main_thread():
            raise ValueError('MANAGED_STOP_MAIN_THREAD_REQUIRED')
        if self._previous is not None:raise ValueError('MANAGED_STOP_ALREADY_ACTIVE')
        self._previous={}
        numbers=[signal.SIGINT,signal.SIGTERM]
        if hasattr(signal,'SIGBREAK'):numbers.append(signal.SIGBREAK)
        try:
            for number in numbers:self._previous[number]=signal.signal(number,self._handler)
        except BaseException:
            self.__exit__()
            raise
        return self

    def __exit__(self,*_):
        if self._previous is not None:
            for number,previous in reversed(list(self._previous.items())):signal.signal(number,previous)
            self._previous=None
