"""Actual report owners plus isolated byte-copy bridge, never real cloud."""
from application.cloud.bridge_transport import RcloneCloudTransport
from application.cloud.feedback import flush_feedback,queue_feedback
from application.cloud.manifest import canonical_bytes
from application.cloud.publication_history import ResearchPublicationReadPort
from application.cloud.synced_folder import SyncedFolderCloudTransport
from storage.paper_feedback import PaperFeedbackOutbox
from strategy import compute_content_hash
from strategy.v02.capabilities import build_capability_snapshot
from tests.application.cloud_fixtures import package
from tests.application import test_cloud_bridge as bridge_fixtures
from tests.validation.robustness_fixtures import subject


def _bridge(fixture):
    helper=bridge_fixtures.CloudBridgeTests(methodName='runTest');helper.setUp();fixture.addCleanup(helper.doCleanups)
    return helper


def _deliver(flush,bridge,stage):
    result=flush(SyncedFolderCloudTransport(bridge.stage,expected_root_id='bridge-fixture'))
    if result.local_staged!=1:raise AssertionError('One actual staged report required')
    if stage=='LOCAL_STAGED':return
    bridge.fake.corrupt_readback=stage=='CONFLICT'
    result=flush(RcloneCloudTransport(bridge.bridge()))
    bridge.fake.corrupt_readback=False
    if stage=='CLOUD_ACKNOWLEDGED' and result.cloud_acknowledged!=1:raise AssertionError('Actual byte readback ACK required')
    if stage=='CONFLICT' and (result.cloud_acknowledged or result.conflicts!=1):raise AssertionError('Wrong bytes must conflict')


def prepare_research_reports(fixture):
    for number in (1,2):
        definition=subject();definition['strategy_id']='fixture-report-'+str(number)
        definition['content_hash']=compute_content_hash(definition)
        folder,manifest,unused=package(fixture.cloud,submission='fixture-report-'+str(number),version='0.2',definition=definition)
        manifest['capability_snapshot_hash']=build_capability_snapshot().snapshot_hash
        (folder/'manifest.json').write_bytes(canonical_bytes(manifest))
    fixture.scan();bridge=_bridge(fixture)
    for submission,state in zip(('fixture-product','fixture-report-1','fixture-report-2'),
            ('CLOUD_ACKNOWLEDGED','CONFLICT','LOCAL_STAGED')):
        current=fixture.client.get('/api/v1/submissions/'+submission).json()['data']
        response=fixture.post('/api/v1/research/runs',dict(command_id='report-'+submission,expected_revision=current['revision'],
            submission_id=submission,policy_id='selected-fixture'))
        if response.status_code!=202:raise AssertionError(response.text)
        claim=fixture.queue.claim_next();job=fixture.queue.step(claim.run_id,claim.generation)
        if job['state']!='COMPLETE':raise AssertionError('Actual completed research owner required')
        with fixture.queue.service_factory() as owner:
            queue_feedback(owner,job['owner_run_id'])
            _deliver(lambda transport:flush_feedback(owner.journal,transport,limit=1),bridge,state)
    fixture.owners.research_publications=ResearchPublicationReadPort(queue_path=fixture.queue.path,
        research_path=fixture.root/'research.sqlite',namespace='FIXTURE')


def prepare_paper_reports(fixture):
    unused,unused,run_id=fixture.api_start();runtime=fixture.h.service.runtime(run_id)
    runtime.on_market_event(fixture.h.event(0,bars=True))
    for second in (1,2,3):runtime.on_market_event(fixture.h.event(second))
    outbox=PaperFeedbackOutbox(fixture.h.process);bridge=_bridge(fixture)
    for second,state in zip((4,5,6),('CLOUD_ACKNOWLEDGED','CONFLICT','LOCAL_STAGED')):
        runtime.on_market_event(fixture.h.event(second));outbox.queue(runtime)
        _deliver(lambda transport:outbox.flush(transport,limit=1),bridge,state)
