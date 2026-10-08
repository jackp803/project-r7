"""Explicit isolated accelerated acceptance worker; never an installed runtime."""
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
import time


def publish(path, value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,sort_keys=True)+'\n',encoding='utf-8')
    # Ordinary Windows readers temporarily deny delete/replace sharing.
    # Keep publication atomic; a permanent lock still fails within five seconds.
    deadline=time.monotonic()+5
    while True:
        try:
            temporary.replace(path)
            return
        except PermissionError as exc:
            if os.name!='nt' or exc.winerror not in (5,32) or time.monotonic()>=deadline:
                raise
            time.sleep(.02)


def paper(root):
    from tests.product.test_paper_runtime_v02 import PaperRuntimeV02Tests
    from application.paper.scheduler import PaperScheduler
    from brokers.paper import PaperBroker
    fixture=PaperRuntimeV02Tests(); fixture.setUp()
    try:
        runtime=fixture.start(); runtime.on_market_event(fixture.event(0,bars=True))
        runtime.on_market_event(fixture.event(1)); scheduler=PaperScheduler(runtime)
        counter=0
        while not (root/'close-request').exists():
            fixture.clock[0]=fixture.initial_now+timedelta(seconds=2+counter)
            scheduler.tick(); counter+=1
            position=fixture.process.recover(runtime.run_id).state['runtime']['position']
            publish(root/'heartbeat.json',dict(pid=os.getpid(),counter=counter,lifecycle=position['lifecycle_state'],
                namespace='FIXTURE',mode='ACCELERATED_FIXTURE'))
            time.sleep(.03)
        fixture.clock[0]=fixture.initial_now+timedelta(seconds=3601)
        scheduler.tick()
        closed=runtime.on_market_event(fixture.event(3602))
        state=fixture.process.recover(runtime.run_id).state
        graph=fixture.canonical.recover(position_id=state['runtime']['position']['position_id'])
        publish(root/'paper-result.json',dict(status=closed.status,graph_status=graph.status,
            closed_trades=len(state['runtime']['closed_trades']),
            net_quantity=str(PaperBroker.from_state(state['broker']).query_position('BTC_USDT_PERP').net_quantity),
            heartbeat_count=counter,namespace='FIXTURE',mode='ACCELERATED_FIXTURE'))
        return 0
    finally: fixture.doCleanups()


def research(root,kind):
    from unittest.mock import patch
    from application.research.service import ResearchService
    from backtest.replay import HistoricalReplayEngine
    from tests.application.test_research_robustness import selected
    from tests.validation.robustness_fixtures import subject
    root.mkdir(); selected(root)
    def fault(*args,**kwargs):
        publish(root/'fault-entered.json',dict(kind=kind,stage='ACTUAL_E3_DEVELOPMENT_REPLAY',pid=os.getpid()))
        if kind=='memory': raise MemoryError('bounded deterministic allocation-failure injection')
        time.sleep(120)
        raise AssertionError('Owned deadline did not terminate the stalled research tree')
    with ResearchService(local_root=root,database_path=root/'research.sqlite',registry_path=root/'registry.sqlite',
                         namespace='FIXTURE',owner_id='fixture-resource-worker') as service:
        try:
            with patch.object(HistoricalReplayEngine,'run',fault):
                service.run(submission_id='fixture-resource',definition=subject(),dataset_ref='dataset.json',
                    split_policy_ref='split.json',cost_policy_ref='cost.json',research_policy_ref='research.json',
                    robustness_policy_ref='robustness.json',family_id='fixture-resource-family',seed=42)
        except MemoryError:
            publish(root/'fault-result.json',dict(status='MEMORY_ERROR_INJECTED',host_oom=False,provider_requests=0))
            return 3
        raise AssertionError('Research fault did not execute')


if __name__=='__main__':
    kind=sys.argv[1]; target=Path(sys.argv[2])
    raise SystemExit(paper(target) if kind=='paper' else research(target,kind))
