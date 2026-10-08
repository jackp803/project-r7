"""Trusted local intake/research composition; HTTP and packages never select code."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib

from application.cloud.manifest import safe_component
from application.cloud.synced_folder import SyncedFolderCloudTransport
from application.config import ProductConfig
from application.control_api.owner_services import OwnerControlServices
from application.control_api.paper_ports import PaperReadControlPort
from application.datasets.catalog import decode, read_local
from application.intake.ledger import IntakeLedger
from application.intake.service import StrategyInboxService
from application.research.queue import ResearchQueue
from application.research.selection import ResearchRequestResolver, validate_research_selections
from application.research.service import ResearchService
from storage import open_sqlite_platform
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from strategy.v02.capabilities import build_capability_snapshot


def validate_owner_selections(value):
    """The same non-secret profile is used by CLI setup and normal startup."""
    if not isinstance(value, dict) or set(value) != {'schema_version','cloud_root_id','research_policies'}:
        raise ValueError('Exact bounded owner selection profile required')
    if value['schema_version'] != 'r7-owner-selections-v0.2':
        raise ValueError('Unsupported local owner selection profile')
    cloud_id=value['cloud_root_id']
    if cloud_id is not None:
        safe_component(cloud_id)
    return dict(schema_version=value['schema_version'],cloud_root_id=cloud_id,
                research_policies=validate_research_selections(value['research_policies']))


class LocalOwners:
    def __init__(self, config, *, namespace='LOCAL_RESEARCH', clock=None, worker_id=None):
        if not isinstance(config, ProductConfig) or namespace not in ('LOCAL_RESEARCH', 'FIXTURE'):
            raise ValueError('Trusted same-namespace local composition required')
        if not config.database_path.is_relative_to(config.local_data_root) or config.database_path == config.local_data_root:
            raise ValueError('Canonical store inside configured local root required')
        from application.platform.restoration import require_valid_restoration
        restoration = require_valid_restoration(config)
        self.config, self.namespace = config, namespace
        self.clock = clock if clock is not None else lambda: datetime.now(timezone.utc)
        if not callable(self.clock): raise ValueError('Actual UTC clock required')
        self.worker_id = safe_component(worker_id if worker_id is not None else
            'research-' + hashlib.sha256(config.product_instance_id.encode('utf-8')).hexdigest()[:24])
        selection_path = config.local_data_root / 'owner-selections.json'
        selected = dict(schema_version='r7-owner-selections-v0.2', cloud_root_id=None, research_policies={})
        if selection_path.exists():
            selected = decode(read_local(config.local_data_root, 'owner-selections.json', 65536))
        selected=validate_owner_selections(selected)
        cloud_id = selected['cloud_root_id']
        if cloud_id is not None:
            safe_component(cloud_id)
            if restoration['status']=='RESTORED_INHIBITED':
                cloud_id = None  # Preserve selected bytes; restored owners stay disconnected.
            elif config.cloud_root is None: raise ValueError('Explicit cloud staging root required')
        # Validate all policy selections before initializing any canonical database.
        self.registry_factory = lambda: open_sqlite_platform(config.database_path, research_namespace=namespace)
        self.intake_factory = lambda: IntakeLedger(config.local_data_root / 'intake.sqlite', instance_id=config.product_instance_id)
        self.snapshots = config.local_data_root / 'snapshots'
        resolver = ResearchRequestResolver(config.local_data_root, snapshot_root=self.snapshots,
            intake_factory=self.intake_factory, registry_factory=self.registry_factory, policies=selected['research_policies'])
        config.local_data_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        config.database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.registry_factory() as e6: e6.lifecycle_counts()
        self.resolver = resolver if resolver.policies else None
        self.queue = None
        if self.resolver is not None:
            self.queue = ResearchQueue(config.local_data_root / 'queue.sqlite', namespace=namespace,
                owner_id=self.worker_id, resolve_request=self.resolver.resolve, clock=self.clock,
                service_factory=lambda: ResearchService(local_root=config.local_data_root,
                    database_path=config.local_data_root / 'research.sqlite', registry_path=config.database_path,
                    namespace=namespace, owner_id=self.worker_id))
        self.inbox_factory = None
        if cloud_id is not None:
            @contextmanager
            def inbox():
                with self.intake_factory() as ledger, self.registry_factory() as e6:
                    yield StrategyInboxService(SyncedFolderCloudTransport(config.cloud_root, expected_root_id=cloud_id),
                        ledger, e6, snapshot_root=self.snapshots, owner_id='scan-' + config.product_instance_id,
                        capability_snapshot_hash=build_capability_snapshot().snapshot_hash)
            self.inbox_factory = inbox

    def control_services(self):
        reader = PaperReadControlPort(namespace=self.namespace, clock=self.clock,
            process_factory=lambda: open_paper_process_journal(self.config.database_path),
            canonical_factory=lambda: open_paper_runtime_journal(self.config.database_path))
        return OwnerControlServices(self.config, namespace=self.namespace, clock=self.clock,
            registry_factory=self.registry_factory, intake_factory=self.intake_factory,
            inbox_factory=self.inbox_factory, research_queue=self.queue, research_resolver=self.resolver,
            paper_reader=reader)
