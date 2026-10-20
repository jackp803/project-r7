"""Actual intake/publisher/byte-readback fixture; destination is local fake copy."""
from dataclasses import replace
import json
from application.cloud.bridge_transport import RcloneCloudTransport
from application.cloud.manifest import canonical_bytes
from application.cloud.publisher import Publisher
from application.cloud.synced_folder import SyncedFolderCloudTransport
from strategy import compute_content_hash
from strategy.v02.capabilities import build_capability_snapshot
from tests.application.cloud_fixtures import package
from tests.application.test_cloud_bridge import CloudBridgeTests
from tests.validation.robustness_fixtures import subject


def prepare_delivery(fixture):
    for number in (1,2):
        definition=subject();definition['strategy_id']='fixture-delivery-'+str(number)
        definition['content_hash']=compute_content_hash(definition)
        folder,manifest,_=package(fixture.cloud,submission='fixture-delivery-'+str(number),version='0.2',definition=definition)
        manifest['capability_snapshot_hash']=build_capability_snapshot().snapshot_hash
        (folder/'manifest.json').write_bytes(canonical_bytes(manifest))
    fixture.scan()
    bridge=CloudBridgeTests(methodName='runTest');bridge.setUp();fixture.addCleanup(bridge.doCleanups)
    bridge.config=replace(bridge.config,cloud_root=fixture.cloud)
    bridge.payload['root_id']='fixture-cloud-root';bridge.write_settings()
    (bridge.remote/'.r7-root.json').write_bytes((fixture.cloud/'.r7-root.json').read_bytes())
    transport=RcloneCloudTransport(bridge.bridge())
    with fixture.intake_factory() as ledger:
        local=Publisher(ledger,SyncedFolderCloudTransport(fixture.cloud,expected_root_id='fixture-cloud-root')).flush(10)
        if local.local_staged!=3:raise AssertionError('Three actual local staged receipts required')
        staged_views=ledger.list_submissions(limit=10,offset=0)
        acknowledged=Publisher(ledger,transport).flush(1)
        if acknowledged.cloud_acknowledged!=1:raise AssertionError('Actual byte-verified local-copy ACK required')
        bridge.fake.corrupt_readback=True
        denied=Publisher(ledger,transport).flush(1)
        bridge.fake.corrupt_readback=False
        if denied.cloud_acknowledged or denied.unavailable+denied.conflicts!=1:
            raise AssertionError('Wrong destination readback must not acknowledge')
        views=[ledger.submission_view(row['submission_id']) for row in ledger.list_submissions(limit=10,offset=0)]
        for view in views:
            if view['publication']['state']=='CLOUD_ACKNOWLEDGED':
                # Actual artifact location comes from the original local outbox
                # receipt; never infer a new cloud acknowledgment from this scan.
                manifests=list((fixture.cloud/'receipts').rglob('manifest.json'))
                matches=[path for path in manifests if json.loads(path.read_bytes())['artifact_hash']==view['publication']['artifact_hash']]
                if len(matches)!=1:raise AssertionError('One exact acknowledged bundle required')
                folder=matches[0].parent
                for path in folder.iterdir():
                    remote=bridge.remote/path.relative_to(fixture.cloud)
                    if not remote.is_file() or path.read_bytes()!=remote.read_bytes():raise AssertionError('Actual destination bytes differ')
    return dict(source='LOCAL_COPY_FIXTURE_ONLY',real_cloud='NOT_RUN',
        local_staged=local.local_staged,acknowledged=acknowledged.cloud_acknowledged,
        wrong_readback_denied=denied.unavailable+denied.conflicts,staged_views=staged_views,views=views)
