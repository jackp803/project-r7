"""non-TestCase existing owner/backup fixture.
No preflight module is imported here. All files/data are temporary synthetic.
"""
from contextlib import closing
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from application.platform.backup import _inventory
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.product_backup import create_product_backup, verify_product_backup
from tests.application import test_local_owner_composition

ROLES = frozenset(('canonical','intake','queue','research','control','auth','supervision','settings'))


def source_database_hashes(config):
    result={}
    for role,path in _inventory(config,include_settings=True).items():
        for suffix in ('','-wal','-shm'):
            artifact=Path(str(path)+suffix)
            if artifact.exists():
                result[role+suffix]=hashlib.sha256(artifact.read_bytes()).hexdigest()
    return result


def bundle_hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob('*')) if p.is_file()}


def make_verified_bundle(testcase,*,mismatched_queue=False):
    fixture=test_local_owner_composition.LocalOwnerCompositionTests()
    testcase.addCleanup(fixture.doCleanups)
    fixture.setUp()
    fixture.config=replace(fixture.config,execution_mode='FIXTURE')
    owners=fixture.configured()
    with owners.inbox_factory() as inbox:
        testcase.assertEqual(1,inbox.scan_once(fixture.clock()).accepted)
    # Normal actual base+owner settings DDL; no auth enrollment/research job,
    # provider calls, process start or fake financial results are needed.
    services=owners.control_services()
    testcase.assertEqual('E6_AND_CONTROL_STORES_AVAILABLE',services.view('health')['storage'])
    if mismatched_queue:
        # Schema-only adversarial mutation in a controlled test-owned source.
        # Normal actual backup must capture/verify these genuine changed bytes.
        with closing(sqlite3.connect(fixture.root/'queue.sqlite')) as db:
            db.execute('CREATE INDEX upgrade_unknown_queue_shape ON research_queue_jobs(state)')
            db.commit()
    profile_root=fixture.base/'private-source-profile'
    create_private_directory(profile_root)
    config_path=profile_root/'source-profile.json'
    config_values={key:str(value) if isinstance(value,Path) else value
        for key,value in asdict(fixture.config).items()}
    write_private_new(config_path,(json.dumps(config_values,sort_keys=True)+'\n').encode())
    backup=fixture.base/'verified-product-bundle'
    created=create_product_backup(fixture.config,backup,config_path=config_path)
    testcase.assertEqual('PRODUCT_DATA_BACKUP_VERIFIED',created['status'])
    verified=verify_product_backup(fixture.config,backup)
    testcase.assertEqual('PRODUCT_DATA_BACKUP_VERIFIED',verified['status'])
    manifest=json.loads((backup/'databases'/'manifest.json').read_bytes())
    present={row['logical_name'] for row in manifest['databases']}
    absent=set(manifest['absent_databases'])
    testcase.assertEqual(ROLES,present|absent)
    testcase.assertFalse(present&absent)
    testcase.assertEqual({'canonical','intake','queue','settings'},present)
    testcase.assertEqual({'auth','control','research','supervision'},absent)
    return SimpleNamespace(fixture=fixture,config=fixture.config,config_path=config_path,
        backup=backup,manifest=manifest,present=present,absent=absent,
        source_hashes=source_database_hashes(fixture.config),backup_hashes=bundle_hashes(backup))
