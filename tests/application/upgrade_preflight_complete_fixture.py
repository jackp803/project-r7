"""Actual test-owned synthetic setup. Real synthetic owners, no credential enrollment.
All outputs remain in TemporaryDirectory/private backup; no auth rows exported.
"""
from contextlib import closing
from dataclasses import asdict,replace
import json
from pathlib import Path
import sqlite3

from application.control_api.auth import LocalAuth
from application.control_api.commands import CommandLedger
from application.platform import supervision
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.product_backup import create_product_backup,verify_product_backup
from application.research.evidence import ResearchJournal
from application.research.holdout import ResearchTrialLedger
from storage._sqlite_registry import _connect,_apply_migrations
from tests.application.upgrade_preflight_fixture import (
    ROLES,make_verified_bundle,source_database_hashes,bundle_hashes)


def _seal(testcase,c,name):
    c.backup=c.fixture.base/name
    result=create_product_backup(c.config,c.backup,config_path=c.config_path)
    testcase.assertEqual('PRODUCT_DATA_BACKUP_VERIFIED',result['status'])
    testcase.assertEqual('PRODUCT_DATA_BACKUP_VERIFIED',verify_product_backup(c.config,c.backup)['status'])
    c.manifest=json.loads((c.backup/'databases'/'manifest.json').read_bytes())
    c.present={row['logical_name'] for row in c.manifest['databases']}
    c.absent=set(c.manifest['absent_databases'])
    testcase.assertEqual(ROLES,c.present|c.absent)
    testcase.assertFalse(c.present&c.absent)
    c.source_hashes=source_database_hashes(c.config)
    c.backup_hashes=bundle_hashes(c.backup)
    return c


def make_all_present_bundle(testcase,*,mutation=None):
    # Reuse existing valid baseline composition; final fresh backup is taken
    # AFTER all additional real owners initialized. Baseline bundle is preserved.
    c=make_verified_bundle(testcase)
    root=c.config.local_data_root
    with ResearchJournal(root/'research.sqlite'): pass
    with ResearchTrialLedger(root/'research.sqlite'): pass
    CommandLedger(root/'control-commands.sqlite',namespace='FIXTURE',clock=c.fixture.clock)
    LocalAuth(root/'local-auth.sqlite',namespace='FIXTURE',clock=c.fixture.clock)
    # Use actual schema owner only, not ProcessSupervisor.__enter__: no session,
    # generation, worker, subprocess or runtime start is issued.
    with supervision._db(root/'process-supervision.sqlite',writable=True) as db:
        supervision._apply_supervision_schema(db)
        testcase.assertEqual(0,db.execute('SELECT COUNT(*) FROM process_sessions').fetchone()[0])
    if mutation is not None:
        if mutation=='research-index':
            path=root/'research.sqlite';sql='CREATE INDEX unknown_upgrade_research_shape ON research_runs(created_at)';args=()
        elif mutation=='control-user-version':
            path=root/'control-commands.sqlite';sql='PRAGMA user_version=7';args=()
        elif mutation=='supervision-receipt':
            path=root/'process-supervision.sqlite'
            sql='UPDATE process_supervision_schema SET sha256=? WHERE migration=?'
            args=('sha256:'+'e'*64,'0009_coordinator_process_supervision')
        else: raise ValueError('Finite test mutation required')
        with closing(sqlite3.connect(path)) as db:
            cursor=db.execute(sql,args)
            if mutation=='supervision-receipt': testcase.assertEqual(1,cursor.rowcount)
            db.commit()
    c=_seal(testcase,c,'all-present-'+(mutation or 'normal'))
    testcase.assertEqual(ROLES,c.present)
    testcase.assertEqual(set(),c.absent)
    return c


def make_prefix19_bundle(testcase):
    c=make_verified_bundle(testcase)
    # NEW synthetic source, actual capped migration producer. Do not delete or
    # downgrade populated current schema, fake migration receipts or run a
    # current LocalOwners factory against this source before backup.
    root=c.fixture.base/'private-prefix19-source';create_private_directory(root)
    c.config=replace(c.config,product_instance_id='upgrade-prefix19-fixture',
        local_data_root=root,database_path=root/'canonical.sqlite3',cloud_root=None)
    with closing(_connect(c.config.database_path)) as db:
        _apply_migrations(db,through_migration='0019_paper_operational_selections.sql')
        testcase.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
    profile=c.fixture.base/'private-prefix19-config';create_private_directory(profile)
    c.config_path=profile/'source-profile.json'
    values={key:str(value) if isinstance(value,Path) else value for key,value in asdict(c.config).items()}
    write_private_new(c.config_path,(json.dumps(values,sort_keys=True)+'\n').encode())
    c=_seal(testcase,c,'prefix19-normal-backup')
    testcase.assertEqual({'canonical'},c.present)
    testcase.assertEqual(ROLES-{'canonical'},c.absent)
    return c
