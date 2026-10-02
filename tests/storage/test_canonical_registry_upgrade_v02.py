from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil,sqlite3
import unittest
from registry import StrategyPlatformService
from storage._sqlite_registry import _connect,_apply_migrations,_internal_store_for_tests
from tests.registry.test_validation_lifecycle import strategy_payload,LocalPassE2Boundary,backtest_payload,validation_decision_payload

class CanonicalRegistryUpgradeTests(unittest.TestCase):
    def test_failed_factory_migration_closes_the_owned_connection(self):
        from unittest.mock import patch
        from storage.platform import open_sqlite_platform
        with TemporaryDirectory() as temporary:
            db=_connect(Path(temporary)/'registry.sqlite')
            try:
                with patch('storage._sqlite_registry._connect',return_value=db),patch('storage._sqlite_registry._apply_migrations',side_effect=sqlite3.DatabaseError('fixture migration failure')):
                    with self.assertRaises(sqlite3.DatabaseError): open_sqlite_platform(Path(temporary)/'registry.sqlite')
                with self.assertRaises(sqlite3.ProgrammingError): db.execute('SELECT 1')
            finally: db.close()

    def test_interrupted_product_migrations_rollback_all_schema_objects_and_receipts(self):
        migrations=Path(__file__).resolve().parents[2]/'src/storage/migrations'
        for name in ('0009_product_assessment_evidence.sql','0010_product_lifecycle_authority.sql'):
            with self.subTest(migration=name),TemporaryDirectory() as temporary:
                previous=Path(temporary)/'previous'; broken=Path(temporary)/'broken'
                previous.mkdir(); broken.mkdir()
                for source in migrations.glob('*.sql'):
                    if source.name<name: shutil.copyfile(source,previous/source.name)
                (broken/name).write_text((migrations/name).read_text()+'\nINSERT INTO nonexistent_fault_fixture VALUES(1);\n',encoding='utf-8')
                with closing(_connect(Path(temporary)/'registry.sqlite')) as db:
                    _apply_migrations(db,previous)
                    before=[tuple(row) for row in db.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name')]
                    receipts=[tuple(row) for row in db.execute('SELECT * FROM schema_migrations')]
                    with self.assertRaises(sqlite3.DatabaseError): _apply_migrations(db,broken)
                    self.assertEqual(before,[tuple(row) for row in db.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name')])
                    self.assertEqual(receipts,[tuple(row) for row in db.execute('SELECT * FROM schema_migrations')])
                    self.assertFalse(db.in_transaction); self.assertEqual(1,db.execute('PRAGMA foreign_keys').fetchone()[0])
                    _apply_migrations(db); self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())

    def test_populated_legacy_registry_upgrade_retains_all_identity_and_evidence_rows(self):
        root=Path(__file__).resolve().parents[2]
        self.assertTrue((root/'src/storage/migrations/0008_canonical_strategy_lifecycle.sql').is_file(),'Missing canonical lifecycle upgrade')
        with TemporaryDirectory() as temporary:
            old=Path(temporary)/'legacy-migrations'; old.mkdir()
            for source in (root/'src/storage/migrations').glob('*.sql'):
                if source.name[:4]<'0008': shutil.copyfile(source,old/source.name)
            with closing(_connect(Path(temporary)/'registry.sqlite')) as db:
                _apply_migrations(db,old); service=StrategyPlatformService(_internal_store_for_tests(db),LocalPassE2Boundary())
                registered=service.intake(strategy_payload(),source_actor='fixture',operation_id='fixture-import').strategy
                # Materialize an accepted historical eleven-column transition;
                # the new owner writer requires the already-upgraded schema.
                db.execute('INSERT INTO lifecycle_transitions VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    ('legacy-backtesting',registered.identity.strategy_id,registered.identity.strategy_version,
                     'DRAFT','BACKTESTING','2026-08-20T00:02:00Z','fixture','["COMPATIBILITY_PASS"]',None,0,1))
                db.execute("UPDATE strategy_versions SET current_lifecycle_state='BACKTESTING',registry_revision=1")
                db.commit()
                backtest=service.record_backtest_result(backtest_payload())
                service.record_validation_decision(validation_decision_payload('bt-1'),backtest_evidence_id=backtest.evidence_id)
                tables=('strategy_versions','compatibility_evidence','validation_evidence','strategy_intake_receipts','lifecycle_transitions','strategy_intake_operations')
                columns={name:[row[1] for row in db.execute('PRAGMA table_info('+name+')')] for name in tables}
                def preserved_rows():
                    return {name:[tuple(row) for row in db.execute('SELECT '+','.join(columns[name])+' FROM '+name)] for name in tables}
                before=preserved_rows()
                _apply_migrations(db)
                after=preserved_rows()
                self.assertEqual(before,after); self.assertEqual(1,db.execute('PRAGMA foreign_keys').fetchone()[0])
                self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
                # Reopening migration is idempotent, not a second destructive upgrade.
                _apply_migrations(db); self.assertEqual(after,preserved_rows())
                self.assertEqual([None],[row[0] for row in db.execute('SELECT owner_evidence_id FROM lifecycle_transitions')])
                with self.assertRaises(sqlite3.IntegrityError): db.execute("UPDATE strategy_versions SET content_hash='changed'")
                db.rollback()
                with self.assertRaises(sqlite3.IntegrityError): db.execute("UPDATE strategy_versions SET current_lifecycle_state='LIVE',registry_revision=registry_revision+1")
                db.rollback()
    def test_rebuild_fault_rolls_back_schema_data_and_migration_receipt_then_restores_fk(self):
        root=Path(__file__).resolve().parents[2]
        with TemporaryDirectory() as temporary:
            old=Path(temporary)/'old'; old.mkdir(); broken=Path(temporary)/'broken'; broken.mkdir()
            for source in (root/'src/storage/migrations').glob('*.sql'):
                if source.name[:4]<'0008': shutil.copyfile(source,old/source.name)
            source=root/'src/storage/migrations/0008_canonical_strategy_lifecycle.sql'
            (broken/source.name).write_text(source.read_text()+'\nINSERT INTO nonexistent_fixture_table VALUES(1);\n',encoding='utf-8')
            with closing(_connect(Path(temporary)/'registry.sqlite')) as db:
                _apply_migrations(db,old)
                service=StrategyPlatformService(_internal_store_for_tests(db)); service.intake(strategy_payload(),source_actor='fixture')
                before=[tuple(row) for row in db.execute('SELECT * FROM strategy_versions')]
                schema=db.execute("SELECT sql FROM sqlite_schema WHERE name='strategy_versions'").fetchone()[0]
                versions=[tuple(row) for row in db.execute('SELECT * FROM schema_migrations')]
                with self.assertRaises(sqlite3.DatabaseError): _apply_migrations(db,broken)
                self.assertEqual(before,[tuple(row) for row in db.execute('SELECT * FROM strategy_versions')])
                self.assertEqual(schema,db.execute("SELECT sql FROM sqlite_schema WHERE name='strategy_versions'").fetchone()[0])
                self.assertEqual(versions,[tuple(row) for row in db.execute('SELECT * FROM schema_migrations')])
                self.assertEqual(1,db.execute('PRAGMA foreign_keys').fetchone()[0]); self.assertFalse(db.in_transaction)
                _apply_migrations(db)
                self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
