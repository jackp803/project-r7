"""finite readonly supported SQLite schema preflight.
Only facts for an inhibited clone, never migration execution or financial authority.
"""
from contextlib import ExitStack, closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from application.platform.backup import (_connect,_database_facts,_deadline,_hash_file,
    _inventory,_profile_current)
from application.platform.private_files import require_private
from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from application.platform.supervision import PROCESS_ROLES
from storage._sqlite_registry import _MIGRATIONS_DIR,_apply_migrations,check_migration_compatibility
from registry.models import EvidenceGateError


class UpgradePreflightError(RuntimeError):
    def __init__(self,code): self.code=code;super().__init__(code)


def _fail(code): raise UpgradePreflightError(code)


def _schema(db):
    rows=db.execute('SELECT type,name,tbl_name,sql FROM main.sqlite_schema ORDER BY type,name').fetchmany(10001)
    if len(rows)>10000: _fail('UPGRADE_PREFLIGHT_SCHEMA_LIMIT')
    normalized=tuple(tuple(value.replace('\r\n','\n') if isinstance(value,str) else value
        for value in row) for row in rows)
    return normalized,db.execute('PRAGMA user_version').fetchone()[0]


def _model(scripts,end):
    # Trusted packaged DDL only, never instantiate RW operational owners or seed
    # user/auth/financial rows. No SQL from source stores/manifests is executed.
    with closing(sqlite3.connect(':memory:')) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.set_progress_handler(lambda:int(time.monotonic()>=end),1000)
        for script in scripts:
            _deadline(end);db.executescript(script)
        return _schema(db)


def _application_models(end):
    from application.control_api.auth import LOCAL_AUTH_SCHEMA_SQL
    from application.control_api.services import CONTROL_SETTINGS_SCHEMA_SQL
    from application.control_api.owner_services import CONTROL_SCANS_SCHEMA_SQL,CONTROL_SCAN_RECEIPTS_SCHEMA_SQL
    from application.platform.supervision import _SCHEMA_RECEIPT_SQL
    root=Path(__file__).parents[1]/'migrations'
    def script(name):
        _deadline(end)
        return (root/name).read_text(encoding='utf-8')
    intake=script('0001_intake_outbox.sql');queue=script('0005_research_queue.sql')
    journal=(script('0002_research_attempts.sql'),script('0007_research_feedback_outbox.sql'))
    trial=script('0003_research_trial_ledger.sql')
    legacy=script('0006_process_supervision.sql')
    runtime=script('0008_runtime_process_supervision.sql')
    coordinator=script('0009_coordinator_process_supervision.sql')
    models={
        'intake':(_model((intake,),end),),
        'queue':(_model((queue,),end),),
        'research':(_model(journal,end),_model((trial,),end),_model((*journal,trial),end)),
        'control':(_model((script('0004_control_commands.sql'),),end),),
        'auth':(_model((LOCAL_AUTH_SCHEMA_SQL,),end),),
        'settings':(_model((CONTROL_SETTINGS_SCHEMA_SQL,),end),
            _model((CONTROL_SETTINGS_SCHEMA_SQL,CONTROL_SCANS_SCHEMA_SQL,CONTROL_SCAN_RECEIPTS_SCHEMA_SQL),end)),
        'supervision':(_model((legacy,_SCHEMA_RECEIPT_SQL+';',runtime,coordinator),end),),
    }
    receipts=tuple((name,'sha256:'+hashlib.sha256(text.replace('\r\n','\n').encode()).hexdigest())
        for name,text in (('0008_runtime_process_supervision',runtime),('0009_coordinator_process_supervision',coordinator)))
    return models,receipts


def _canonical_model(applied,end):
    known=tuple(sorted(path.name for path in _MIGRATIONS_DIR.glob('*.sql')))
    if not applied: _fail('UPGRADE_PREFLIGHT_CANONICAL_UNINITIALIZED')
    # Minimum existing restore-fencing source contract, not arbitrary prefix.
    minimum='0019_paper_operational_selections.sql'
    if minimum not in known or applied[-1]<minimum:
        _fail('UPGRADE_PREFLIGHT_CANONICAL_PREFIX_UNSUPPORTED')
    with closing(sqlite3.connect(':memory:')) as model:
        model.row_factory=sqlite3.Row;model.execute('PRAGMA foreign_keys=ON')
        model.set_progress_handler(lambda:int(time.monotonic()>=end),1000)
        # Root owns new additive through_migration cap: exact packaged name only;
        # existing actual migrator stays the sole producer of schema models.
        _apply_migrations(model,through_migration=applied[-1])
        _deadline(end)
        unbound=_schema(model)
        # Registry/qualification owners add this same immutable namespace shape
        # after migrations. Both actual owner compositions are finite targets.
        from storage.qualification import _NAMESPACE_SQL
        for statement in _NAMESPACE_SQL:model.execute(statement)
        return unbound,_schema(model)


def _preflight_verified_databases(config,database_backup,manifest,end,*,include_settings=False):
    """Caller already holds all owner locks and verified this finite manifest.

    Rehash every sealed artifact before/after RO structural inspection. This is
    also the restore seam BEFORE any target-create/fence/migration operation.
    """
    inventory=_inventory(config,include_settings=include_settings)
    if (type(manifest) is not dict or type(manifest.get('databases')) is not list
            or type(manifest.get('absent_databases')) is not list):
        _fail('UPGRADE_PREFLIGHT_INVENTORY_INVALID')
    rows=manifest['databases'];absent=manifest['absent_databases']
    if not 1<=len(rows)<=len(inventory) or len(absent)>len(inventory):
        _fail('UPGRADE_PREFLIGHT_INVENTORY_INVALID')
    names=[row.get('logical_name') if type(row) is dict else None for row in rows]
    if (any(type(name) is not str for name in names+absent)
            or len(set(names))!=len(names) or len(set(absent))!=len(absent)
            or set(names)&set(absent) or set(names)|set(absent)!=set(inventory)
            or 'canonical' not in names):
        _fail('UPGRADE_PREFLIGHT_INVENTORY_INVALID')
    root=Path(database_backup);require_private(root,directory=True)
    models,supervision_receipts=_application_models(end)
    facts={name:dict(status='ABSENT') for name in absent}
    for row in rows:
        _deadline(end);role=row['logical_name']
        if (row.get('artifact')!=role+'.sqlite' or
                row.get('relative_path')!=inventory[role].relative_to(config.local_data_root).as_posix()):
            _fail('UPGRADE_PREFLIGHT_INVENTORY_INVALID')
        path=root/row['artifact'];require_private(path)
        expected={key:row[key] for key in ('bytes','sha256')}
        if _hash_file(path,end)!=expected: _fail('UPGRADE_PREFLIGHT_ARTIFACT_CHANGED')
        with closing(_connect(path,'ro',end,immutable=True)) as db:
            db.execute('PRAGMA query_only=ON')
            if _database_facts(db)!={key:row[key] for key in ('schema_hash','user_version')}:
                _fail('UPGRADE_PREFLIGHT_ARTIFACT_CHANGED')
            actual=_schema(db)
            if role=='canonical':
                try: compatible=check_migration_compatibility(db)
                except EvidenceGateError:
                    raise UpgradePreflightError('UPGRADE_PREFLIGHT_SCHEMA_UNSUPPORTED') from None
                if actual not in _canonical_model(compatible['applied'],end):
                    _fail('UPGRADE_PREFLIGHT_SCHEMA_UNSUPPORTED')
                facts[role]=dict(status='COMPATIBLE',applied=compatible['applied'],pending=compatible['pending'])
            else:
                if actual not in models[role]: _fail('UPGRADE_PREFLIGHT_SCHEMA_UNSUPPORTED')
                if role=='supervision':
                    receipts=tuple(tuple(row) for row in db.execute(
                        'SELECT migration,sha256 FROM process_supervision_schema ORDER BY migration LIMIT 3').fetchall())
                    if receipts!=supervision_receipts: _fail('UPGRADE_PREFLIGHT_SCHEMA_UNSUPPORTED')
                facts[role]=dict(status='COMPATIBLE')
        require_private(path)
        if _hash_file(path,end)!=expected: _fail('UPGRADE_PREFLIGHT_ARTIFACT_CHANGED')
    _deadline(end)
    return dict(status='COMPATIBLE_FOR_INHIBITED_CLONE',roles=dict(sorted(facts.items())),
        financial_authority='NONE',database_mutations=0,owner_starts=0)


def preflight_product_upgrade(config,backup,*,config_path=None,timeout_seconds=30):
    if type(timeout_seconds) is not int or not 5<=timeout_seconds<=300:
        _fail('UPGRADE_PREFLIGHT_DEADLINE_REQUIRED')
    end=time.monotonic()+timeout_seconds
    try:
        from application.platform.product_backup import _verified_manifest
        from application.platform.supervision import config_hash
        from application.research.evidence import capture_provenance
        _profile_current(config,config_path)
        with ExitStack() as stack:
            for role in PROCESS_ROLES:
                stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,
                    lock_root=operational_lock_root(config)))
            sealed=_verified_manifest(config,backup,end)
            result=_preflight_verified_databases(config,Path(backup)/'databases',sealed[3],end,
                include_settings=True)
            if _verified_manifest(config,backup,end)!=sealed:
                _fail('UPGRADE_PREFLIGHT_ARTIFACT_CHANGED')
            result.update(schema_version='r7-product-upgrade-preflight-v0.2',
                target_provenance=capture_provenance(),source_config_hash=config_hash(config),
                backup_id=sealed[0]['backup_id'],
                backup_manifest_sha256='sha256:'+hashlib.sha256(sealed[1]).hexdigest())
            _profile_current(config,config_path);_deadline(end)
        return result
    except UpgradePreflightError: raise
    except Exception:
        raise UpgradePreflightError('UPGRADE_PREFLIGHT_UNAVAILABLE') from None
