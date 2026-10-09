"""Public local staging of actual FIXTURE outboxes; no remote acknowledgment."""
from dataclasses import asdict

from application.config import load_config,product_namespace
from application.local_owners import validate_owner_selections
from application.datasets.catalog import read_local,decode
from application.cloud.synced_folder import SyncedFolderCloudTransport
from application.cloud.publisher import Publisher
from application.cloud.feedback import flush_feedback
from application.intake.ledger import IntakeLedger
from application.research.evidence import ResearchJournal
from application.platform.restoration import require_valid_restoration
from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from storage.paper_process import open_paper_process_journal
from storage.paper_feedback import PaperFeedbackOutbox
from .recipe import ROOT_ID


def publish_fixture_outbox(config_path,*,limit=10):
    if type(limit) is not int or not 1<=limit<=100:
        raise ValueError('Bounded FIXTURE publication batch required')
    config=load_config(config_path)
    if (product_namespace(config)!='FIXTURE' or config.cloud_root is None or
            require_valid_restoration(config)['status']!='NOT_RESTORED'):
        raise ValueError('Explicit non-restored isolated FIXTURE staging required')
    from application.entrypoints import _outside_installation
    _outside_installation(config.cloud_root)
    _outside_installation(config.local_data_root)
    selected=validate_owner_selections(decode(read_local(config.local_data_root,'owner-selections.json',65536)))
    if selected['cloud_root_id']!=ROOT_ID:
        raise ValueError('Product-owned synthetic FIXTURE staging root required')
    transport=SyncedFolderCloudTransport(config.cloud_root,expected_root_id=ROOT_ID)
    transport._check_root()
    counts=dict(attempted=0,local_staged=0,cloud_acknowledged=0,unavailable=0,conflicts=0)
    def add(summary):
        for name,value in asdict(summary).items():
            counts[name]+=value
    with ProcessScopeLock('cloud:'+config.product_instance_id,lock_root=operational_lock_root(config)):
        if load_config(config_path)!=config:
            raise ValueError('Unchanged FIXTURE publication profile required')
        intake=config.local_data_root/'intake.sqlite'
        if intake.is_file():
            with IntakeLedger(intake,instance_id=config.product_instance_id) as ledger:
                add(Publisher(ledger,transport).flush(limit,include_local_staged=False))
        remaining=limit-counts['attempted']
        research=config.local_data_root/'research.sqlite'
        if remaining and research.is_file():
            with ResearchJournal(research) as journal:
                add(flush_feedback(journal,transport,limit=remaining,include_local_staged=False))
        remaining=limit-counts['attempted']
        if remaining and config.database_path.is_file():
            with open_paper_process_journal(config.database_path,require_existing=True) as process:
                add(PaperFeedbackOutbox(process).flush(transport,limit=remaining,include_local_staged=False))
    return dict(status='INCOMPLETE' if counts['unavailable'] or counts['conflicts'] else 'LOCAL_STAGED',
        namespace='FIXTURE',transport='SYNTHETIC_LOCAL_FOLDER',**counts,provider_requests=0,
        credentials='NONE',capital='NONE',financial_authority='NONE',remote_verification='NOT_RUN')
