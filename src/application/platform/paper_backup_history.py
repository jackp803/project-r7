"""Typed ordinary Paper inputs and software evidence for private backup only.

Archival validation preserves failed attempts. It never issues eligibility or
restoration permission and never imports a result into the software store.
"""
from dataclasses import asdict
from contextlib import closing
import re
from pathlib import Path

from application.datasets.catalog import decode,read_local
from application.cloud.manifest import safe_relative,safe_component,parse_manifest,byte_hash
from application.platform.backup import _connect,_deadline
from application.platform.private_files import _filesystem_path
from application.platform.supervision import _local_path
from application.platform.product_backup import ProductBackupError,TRANSIENT_ROOTS

HASH=re.compile(r'sha256:[0-9a-f]{64}')
EXECUTION=re.compile(r'pqr-[0-9a-f]{32}')

def ordinary_history_inventory(root,paths,canonical_database,end,*,sealed_database=False):
    """Only actual LOCAL_RESEARCH ledger references, including historical ones."""
    from storage.paper_selection import open_paper_selections,_TABLE as selection_table,_MIGRATION as selection_migration
    from storage.qualification import open_qualification_receipts,_TABLE as qualification_table,_MIGRATION as qualification_migration,_require_namespace,_signatures
    if canonical_database is None:return set(),{}
    _local_path(Path(canonical_database))
    if not _filesystem_path(canonical_database).is_file():return set(),{}
    with closing(_connect(Path(canonical_database),'ro',end,immutable=sealed_database)) as db:
        # Source integrations may explicitly use a FIXTURE E6 store with the
        # ordinary config shape. Immutable store namespace remains authoritative;
        # never reinterpret its empty ordinary tables as LOCAL_RESEARCH data.
        namespace=db.execute('SELECT singleton,namespace FROM registry_research_namespace').fetchall()
        if namespace==[(1,'FIXTURE')]:
            _require_namespace(db,'FIXTURE',_signatures()[1])
            return set(),{}
        _require_namespace(db,'LOCAL_RESEARCH',_signatures()[1])
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name IN (?,?)",(selection_table,qualification_table))}
        migrations={row[0] for row in db.execute('SELECT migration_name FROM schema_migrations WHERE migration_name IN (?,?)',(selection_migration,qualification_migration))}
    for table,migration in ((selection_table,selection_migration),(qualification_table,qualification_migration)):
        if (table in tables)!=(migration in migrations):raise ProductBackupError('PRODUCT_BACKUP_PAPER_SCHEMA_INVALID')
    allowed,hashes=set(),{}
    if selection_table in tables:
        with open_paper_selections(canonical_database,immutable=sealed_database) as reader:
            latest=reader.current()
            if latest is not None:
                if latest.generation>256:raise ProductBackupError('PRODUCT_BACKUP_PAPER_HISTORY_LIMIT')
                bindings={}
                for generation in range(1,latest.generation+1):
                    _deadline(end);record=reader.get(generation).as_dict()
                    for ref,binding in _ordinary_bindings(root,record).items():
                        if ref in bindings and bindings[ref]!=binding:
                            raise ProductBackupError('PRODUCT_BACKUP_ORDINARY_PAPER_HISTORY_CONFLICT')
                        bindings[ref]=binding
                for relative,(commitment,expected) in bindings.items():
                    _deadline(end);raw=read_local(root,relative,65536)
                    if byte_hash(raw)!=commitment or decode(raw)!=expected:
                        raise ProductBackupError('PRODUCT_BACKUP_ORDINARY_PAPER_INPUT_CHANGED')
                    allowed.add(relative);hashes[relative]=commitment
    if qualification_table in tables:
        with open_qualification_receipts(canonical_database,namespace='LOCAL_RESEARCH',immutable=sealed_database) as reader:
            receipts=reader.history(limit=256)
        for receipt in receipts:
            _deadline(end)
            if not EXECUTION.fullmatch(receipt.execution_id):continue
            refs,commitments=_qualification_bindings(root,receipt,end)
            allowed.update(refs);hashes.update(commitments)
    return allowed,hashes

def _ordinary_bindings(root,record):
    from application.paper.release import _historical_owner
    from application.paper.ordinary_setup import SOURCE_KEYS
    owner=_historical_owner(record,implementation_hash=record['simulator_profile']['implementation_hash'])
    source=record.get('source_subject');keys={'simulation_policy_ref','risk_policy_ref','promotion_policy_ref'}
    if (not isinstance(source,dict) or set(source)!=SOURCE_KEYS or source['schema_version']!='r7-local-paper-source-subject-v0.2'
            or not isinstance(source['input_refs'],dict) or set(source['input_refs'])!=keys
            or not isinstance(source['input_hashes'],dict) or set(source['input_hashes'])!=keys
            or not isinstance(source['manifest_hash'],str) or not HASH.fullmatch(source['manifest_hash'])):
        raise ProductBackupError('PRODUCT_BACKUP_ORDINARY_PAPER_SUBJECT_INVALID')
    identifier=safe_component(source['submission_id'])
    manifest=parse_manifest(read_local(root,'snapshots/'+identifier+'-'+source['manifest_hash'][7:]+'/manifest.json',65536))
    body=manifest.raw
    if (manifest.manifest_hash!=source['manifest_hash'] or source['strategy']!={
            'strategy_id':body['strategy_id'],'strategy_version':body['strategy_version'],'content_hash':body['strategy_content_hash']}
            or owner.as_dict()['submission_validity']!={key:body[key] for key in ('intent_class','validity')}):
        raise ProductBackupError('PRODUCT_BACKUP_ORDINARY_PAPER_MANIFEST_MISMATCH')
    bindings={};selected=owner.as_dict()
    for field,relative in source['input_refs'].items():
        safe_relative(relative);commitment=source['input_hashes'][field]
        if (not relative.endswith('.json') or relative.split('/')[0] in TRANSIENT_ROOTS
                or not isinstance(commitment,str) or not HASH.fullmatch(commitment)):
            raise ProductBackupError('PRODUCT_BACKUP_ORDINARY_PAPER_INPUT_INVALID')
        expected=selected[field.removesuffix('_ref')]
        if relative in bindings and bindings[relative]!=(commitment,expected):
            raise ProductBackupError('PRODUCT_BACKUP_ORDINARY_PAPER_INPUT_CONFLICT')
        bindings[relative]=(commitment,expected)
    return bindings

def _qualification_bindings(root,receipt,end):
    from application.paper.qualification import artifact_bytes,MAX_EXECUTION_ARTIFACTS,validate_qualified_receipt
    prefix='qualification/'+receipt.execution_id+'/'
    profile=receipt.profile_manifest;evidence=receipt.execution_evidence
    if (not isinstance(profile,dict) or not isinstance(evidence,dict)
            or set(evidence)!={'schema_version','provenance','members'}
            or evidence['schema_version']!='r7-qualified-paper-execution-evidence-v0.2'
            or evidence['provenance']!='FIXTURE_SOFTWARE_CHECKS_ONLY'
            or not isinstance(evidence['members'],list) or len(evidence['members'])!=len(receipt.checks)):
        raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_HISTORY_INVALID')
    allowed,hashes=set(),{}
    for check,member in zip(receipt.checks,evidence['members']):
        _deadline(end)
        if (not isinstance(member,dict) or set(member)!={'member_id','group_id','test_cases','artifacts','assertions'}
                or member['member_id']!=check.check_id or not isinstance(member['artifacts'],list)
                or not 1<=len(member['artifacts'])<=MAX_EXECUTION_ARTIFACTS):
            raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_HISTORY_INVALID')
        local={}
        for row in member['artifacts']:
            _deadline(end)
            if (not isinstance(row,dict) or set(row)!={'ref','hash'} or not isinstance(row['hash'],str)
                    or not HASH.fullmatch(row['hash'])):
                raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_ARTIFACT_INVALID')
            ref=safe_relative(row['ref']);commitment=row['hash']
            if ref in local or ref in ('preflight.json','result.json'):
                raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_ARTIFACT_CONFLICT')
            if byte_hash(artifact_bytes(root/'qualification'/receipt.execution_id,ref))!=commitment:
                raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_ARTIFACT_CHANGED')
            local[ref]=commitment
            relative=prefix+ref
            if relative in hashes and hashes[relative]!=commitment:
                raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_ARTIFACT_CONFLICT')
            allowed.add(relative);hashes[relative]=commitment
        if local.get(check.log_ref)!=check.log_hash:
            raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_LOG_UNBOUND')
    # These producer metadata companions are constrained by the actual receipt;
    # no arbitrary file under qualification is accepted as a durable artifact.
    directory=root/'qualification'/receipt.execution_id
    measured={key:value for key,value in asdict(receipt.subject).items() if key!='namespace'}
    measured['capability_hash']=profile.get('capability_hash')
    preflight=prefix+'preflight.json'
    if _filesystem_path(root/preflight).exists():
        raw=read_local(root,preflight,1048576);value=decode(raw)
        if (not isinstance(value,dict) or set(value)!={'profile','measured','execution_id','source_revision','source_worktree'}
                or value['profile']!=profile or value['execution_id']!=receipt.execution_id
                or value['source_revision']!=receipt.subject.executable_revision or value['source_worktree']!='CLEAN'
                or not isinstance(value['measured'],dict)
                or any(value['measured'].get(key)!=item for key,item in measured.items())
                or set(value['measured'])!=set(measured)|{'distribution_profile','financial_authority','worktree'}
                or value['measured']['distribution_profile']!='r7-native-distribution-v0.2'
                or value['measured']['financial_authority']!='NONE' or value['measured']['worktree']!='UNAVAILABLE'):
            raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_PREFLIGHT_INVALID')
        allowed.add(preflight);hashes[preflight]=byte_hash(raw)
    result=prefix+'result.json'
    if _filesystem_path(root/result).exists():
        try:validate_qualified_receipt(receipt,profile,artifact_root=directory,measured=measured);qualified=True
        except ValueError:qualified=False
        completed=sum(all(any(c.check_id==m['member_id'] and c.passed for c in receipt.checks) for m in group['members'])
            for group in profile['groups'])
        expected=dict(status='NATIVE_PAPER_SOFTWARE_QUALIFIED' if qualified else 'NATIVE_PAPER_SOFTWARE_NOT_QUALIFIED',
            receipt_ref=receipt.receipt_id,execution_id=receipt.execution_id,profile_hash=receipt.profile_hash,
            platform_id=receipt.subject.platform_id,executable_revision=receipt.subject.executable_revision,
            build_hash=receipt.subject.build_hash,groups_completed=completed,groups_required=7,provider_requests=0,
            credentials='NONE',capital='NONE',github_compute='NOT_USED',financial_authority='NONE')
        raw=read_local(root,result,65536)
        if decode(raw)!=expected:raise ProductBackupError('PRODUCT_BACKUP_QUALIFICATION_RESULT_INVALID')
        allowed.add(result);hashes[result]=byte_hash(raw)
    return allowed,hashes
