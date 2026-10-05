from pathlib import Path
import ctypes,json,sys
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.config import load_config
from application.cloud.rclone_bridge import load_bridge_profile,RcloneBridge
from application.cloud.bridge_transport import RcloneCloudTransport
from application.cloud.protocol import CloudError
from application.research.evidence import ResearchJournal
from application.intake.ledger import IntakeLedger
from application.cloud.protocol import ArtifactBundle
selected=project/'artifacts/r7-native-S13-recovery-research-30915c6'
config=load_config(selected/'研究 設定.json')
bridge=RcloneBridge(load_bridge_profile(config.local_data_root/'S14-bridge-private/bridge-profile.json',config))
facts=[]
with IntakeLedger(config.local_data_root/'intake.sqlite',instance_id=config.product_instance_id) as ledger:
    pending=ledger.pending_outbox(10)
    print(json.dumps(dict(intake_pending=[dict(state=item.state,logical_path_length=len(item.logical_path),
        staged_absolute_length=len(str(config.cloud_root/item.logical_path/'manifest.json')),
        temporary_stage_absolute_length=len(str(config.cloud_root/item.logical_path))+47) for item in pending])))
    for item in pending:
        bundle=ArtifactBundle(item.logical_path,{'receipt.json':item.payload})
        try:
            bridge.validate_publication(bundle.logical_path,bundle.payloads,512)
            print(json.dumps(dict(intake_prestage='PASS')))
            receipt=RcloneCloudTransport(bridge).publish(bundle,item.operation_id)
            print(json.dumps(dict(intake_retry=receipt.status)))
        except CloudError as error:print(json.dumps(dict(code=error.code,reason=error.reason,win32_last_error=ctypes.get_last_error())))
with ResearchJournal(config.local_data_root/'research.sqlite') as journal:
    for operation,bundle,expected in journal.pending_feedback_publications(10):
        fact=dict(scope='SYNTHETIC_LOCAL_FAKE_ONLY',local_relative_length=len(bundle.logical_path),
            staged_absolute_length=max(len(str(config.cloud_root/bundle.logical_path/name)) for name in (*bundle.payloads,'manifest.json')))
        try:
            bridge.validate_publication(bundle.logical_path,bundle.payloads,512)
            fact['prestage_validation']='PASS'
            receipt=RcloneCloudTransport(bridge).publish(bundle,operation)
            fact['actual_local_fake_retry']=receipt.status
        except CloudError as error:
            fact['code'],fact['reason']=error.code,error.reason
        facts.append(fact)
print(json.dumps(dict(scope='CONTROLLED_OFFLINE_DIAGNOSTIC_NOT_QUALIFICATION',facts=facts)))
