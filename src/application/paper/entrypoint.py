"""Public explicitly isolated Paper worker using the actual product owners."""
import json
from contextlib import contextmanager

from application.config import load_config,product_namespace
from application.local_owners import LocalOwners
from application.platform.restoration import require_valid_restoration
from application.platform.shutdown import ManagedStop
from application.fixtures.market import fixture_market_event,FixtureScenarioClock
from .setup import load_fixture_paper_owners,SELECTION_FILE
from .worker import PaperOwnerWorker


def paper_worker(config_path,*,maximum_ticks=None):
    if maximum_ticks is not None and (type(maximum_ticks) is not int or not 1<=maximum_ticks<=10000):
        raise ValueError('Explicit bounded FIXTURE tick count required')
    config=load_config(config_path)
    if product_namespace(config)!='FIXTURE':
        from .ordinary_setup import ordinary_paper_worker
        return ordinary_paper_worker(config_path,maximum_ticks=maximum_ticks)
    from application.entrypoints import _outside_installation
    _outside_installation(config.local_data_root)
    if (require_valid_restoration(config)['status']!='NOT_RESTORED' or
            not (config.local_data_root/SELECTION_FILE).is_file() or not config.database_path.is_file()):
        raise ValueError('Actual selected non-restored FIXTURE Paper store required')
    scenario_clock=FixtureScenarioClock()
    @contextmanager
    def actual_service():
        nonlocal scenario_clock
        # PaperOwnerWorker acquires the runtime scope before this factory opens
        # actual product stores. No caller-supplied factory/executable is exposed.
        local=LocalOwners(config,namespace='FIXTURE')
        owners=load_fixture_paper_owners(config,clock=local.clock,resolver=local.resolver)
        if owners is None:
            raise ValueError('Actual isolated FIXTURE Paper composition required')
        scenario_clock=FixtureScenarioClock(temporal=owners.fixture_temporal)
        # Seed only from actual accepted E6 starts and their durable owner
        # observations. No result, lifecycle, generation or approval is written.
        with local.registry_factory() as registry:
            accepted=registry.list_accepted_paper_starts(limit=200)
        if len(accepted)==200:
            raise ValueError('FIXTURE clock recovery inventory limit reached')
        from storage.paper_process import open_paper_process_journal
        with open_paper_process_journal(config.database_path,require_existing=True) as process:
            for proof in accepted:
                if proof.identity==owners.strategy_identity:
                    run=json.loads(proof.payload_json)['run_id']
                    scenario_clock.resume(process.recover(run).state['runtime']['forward']['observed_at'])
        owners.clock=scenario_clock
        with owners.service() as service:
            yield service
    with ManagedStop() as stop,PaperOwnerWorker(config,actual_service,namespace='FIXTURE',
            config_path=config_path,feedback_on_quiescence=True) as worker:
        ticks=0
        while not stop.requested:
            from application.platform.service_stop import observe_service_stop
            if observe_service_stop(worker.supervisor,stop):break
            worker.tick()
            for run_id in worker.snapshot()['active_runs']:
                state=worker.service.process.recover(run_id).state['runtime']
                worker.submit_event(run_id,fixture_market_event(state,worker.service.clock()))
            worker.tick()
            ticks+=1
            if maximum_ticks is not None and ticks>=maximum_ticks:
                stop.request()
            else:
                stop.wait(1)
                scenario_clock.advance()
        final=worker.snapshot()
        for run_id in final['active_runs']:
            worker.queue_feedback(run_id)
        final=worker.snapshot()
    print(json.dumps(dict(status='STOPPED',namespace='FIXTURE',ticks=ticks,
        market_source='SYNTHETIC_FIXTURE',mode='ACCELERATED_FIXTURE',
        observation_clock='SYNTHETIC_UTC_SECONDS',process_health_clock='ACTUAL_UTC',
        process_generation=final['process_generation'],run_failures=final['run_failures'],
        exposure_status='NOT_AGGREGATED',financial_authority='NONE',provider_requests=0,
        credentials='NONE',capital='NONE',real_forward_qualification='NOT_ISSUED')))
    return 0 if not final['run_failures'] else 2
