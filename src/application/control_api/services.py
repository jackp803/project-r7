"""Local service composition. Unconfigured owners are explicit delivery gaps."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3

from application.control_api.auth import _ClosingConnection, _stamp
from application.control_api.errors import APIError
from application.research.evidence import capture_provenance
from strategy.v02.capabilities import build_capability_snapshot


class LocalControlServices:
    """Actual local settings plus diagnostics. Operational owners added explicitly.

    Missing owners never produce successful queued/financial receipts. This is
    also the usable uncommissioned first-run state of the native product.
    """
    def __init__(self, config, *, namespace, clock):
        self.config, self.namespace, self.clock = config, namespace, clock
        self.path = config.local_data_root / 'control-settings.sqlite'
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.provenance = capture_provenance()
        self.capabilities = build_capability_snapshot()
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS control_settings(singleton INTEGER PRIMARY KEY CHECK(singleton=1),revision INTEGER NOT NULL,
                    config_generation INTEGER NOT NULL,display_timezone TEXT NOT NULL,scan_interval INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS settings_effects(command_id TEXT PRIMARY KEY,request_json TEXT NOT NULL,receipt_json TEXT NOT NULL);
            ''')
            db.execute("INSERT OR IGNORE INTO control_settings VALUES(1,0,1,'Asia/Taipei',?)", (config.scan_interval,))

    def _db(self):
        db = sqlite3.connect(self.path, timeout=5); db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=5000'); db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return _ClosingConnection(db)

    def settings(self):
        with self._db() as db:
            row = dict(db.execute('SELECT revision,config_generation,display_timezone,scan_interval FROM control_settings WHERE singleton=1').fetchone())
        row.update(local_data_root=str(self.config.local_data_root), cloud_root=None if self.config.cloud_root is None else str(self.config.cloud_root),
            database_path=str(self.config.database_path), control_api_host=self.config.control_api_host, control_api_port=self.config.control_api_port,
            diagnostic_only=self.config.diagnostic_only, paper_runtime_enabled=self.config.paper_runtime_enabled)
        return row

    def metadata(self, source, *, data=None):
        settings = self.settings()
        config = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(self.config).items()}
        raw = json.dumps(dict(config=config, selected_settings=settings), sort_keys=True, separators=(',', ':')).encode()
        return dict(source=source, observed_at=_stamp(self.clock()), as_of=_stamp(self.clock()), freshness='CURRENT',
            current_or_last_known='CURRENT', implementation_hash=self.provenance['implementation_hash'],
            executable_revision=self.provenance['executable_revision'], worktree=self.provenance['worktree'],
            config_hash='sha256:'+hashlib.sha256(raw).hexdigest(), config_generation=settings['config_generation'], namespace=self.namespace)

    def view(self, name, *, subject=None, limit=50, offset=0):
        if name == 'settings': return self.settings()
        if name == 'capabilities': return dict(snapshot_hash=self.capabilities.snapshot_hash, snapshot=self.capabilities.as_dict())
        if name == 'health': return dict(control='ONLINE', research='NOT_CONFIGURED', runtime='NOT_CONFIGURED', storage='CONTROL_STORE_AVAILABLE',
            cloud='NOT_CONNECTED', market='NOT_CONNECTED', provider='NOT_CONFIGURED', live_authorized=False, provider_requests=0,
            runtime_llm_calls=0, reason_codes=['OPERATIONAL_OWNERS_NOT_CONFIGURED'])
        if name == 'overview': return dict(mode='RESEARCH', live_authorized=False, queued_jobs=None, running_jobs=None, lifecycle_counts=None,
            exposure_quantity=None, realized_pnl_usdt=None, unrealized_pnl_usdt=None, runtime_status='NOT_CONFIGURED',
            cloud_status='NOT_CONNECTED', reason_codes=['OPERATIONAL_OWNERS_NOT_CONFIGURED'])
        if name == 'trading': return dict(mode='NOT_STARTED', status='NOT_CONFIGURED', broker_observed_at=None, position=None, protection=None,
            reconciliation='UNKNOWN', realized_pnl_usdt=None, unrealized_pnl_usdt=None, reason_codes=['RUNTIME_NOT_CONFIGURED'])
        if subject is not None: raise APIError('NOT_CONFIGURED', 'OWNER_NOT_CONFIGURED', 503)
        if name in ('submissions', 'research_runs', 'strategies', 'datasets', 'policies', 'alerts'):
            return dict(items=[], limit=limit, offset=offset, total=None, status='NOT_CONFIGURED', reason_codes=['OWNER_NOT_CONFIGURED'])
        raise APIError('UNAVAILABLE', 'VIEW_UNAVAILABLE', 404)

    def revision(self, operation, resource, arguments):
        if operation == 'SETTINGS_UPDATE': return self.settings()['revision']
        raise APIError('NOT_CONFIGURED', 'OWNER_NOT_CONFIGURED', 503)

    def execute(self, operation, resource, arguments, *, actor, human, command_id, expected_revision):
        if operation != 'SETTINGS_UPDATE': raise APIError('NOT_CONFIGURED', 'OWNER_NOT_CONFIGURED', 503)
        raw = json.dumps(dict(arguments=arguments, actor=actor, expected_revision=expected_revision), sort_keys=True, separators=(',', ':'))
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            cached = db.execute('SELECT * FROM settings_effects WHERE command_id=?', (command_id,)).fetchone()
            if cached:
                if cached['request_json'] != raw: raise APIError('CONFLICT', 'COMMAND_CONTENT_CONFLICT', 409)
                return json.loads(cached['receipt_json'])
            row = db.execute('SELECT revision FROM control_settings WHERE singleton=1').fetchone()
            if row['revision'] != expected_revision: raise APIError('CONFLICT', 'RESOURCE_REVISION_CONFLICT', 409)
            changed = db.execute('UPDATE control_settings SET revision=revision+1,config_generation=config_generation+1,display_timezone=?,scan_interval=? WHERE singleton=1 AND revision=?',
                (arguments['display_timezone'], arguments['scan_interval'], expected_revision))
            if changed.rowcount != 1: raise APIError('CONFLICT', 'RESOURCE_REVISION_CONFLICT', 409)
            receipt = dict(command_id=command_id, actor=actor, resource=resource, expected_revision=expected_revision,
                resource_revision=expected_revision+1, status='COMPLETE', effect_ref='local-settings:'+str(expected_revision+1),
                reason_codes=[], observed_at=_stamp(self.clock()))
            db.execute('INSERT INTO settings_effects VALUES(?,?,?)', (command_id, raw, json.dumps(receipt, sort_keys=True)))
            return receipt
