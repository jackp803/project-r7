"""K05 readonly boundary source tests; no native/LIVE/qualification credit.

Proposed APIs are listed in K05-test-design.json. Missing APIs should produce an
honest initial RED after root chooses names and applies the draft. Do not skip,
mock provenance CLEAN, or interpret a signature mismatch as a product defect.
Only existing real owner factories create financial state in this draft.
"""
from contextlib import ExitStack, closing,contextmanager
from dataclasses import FrozenInstanceError
from datetime import timedelta
import importlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from tests.product import test_trading_dispatch_v02 as dispatch_fixtures
from tests.risk.test_approved_plan_consumer_v02 import approved
from storage.runtime import open_paper_runtime_journal
from storage.product_dispatch import open_product_dispatch_journal


def logical_store(path):
    # Test-owned stores only. Opening this helper never creates a missing DB.
    with closing(sqlite3.connect(Path(path).absolute().as_uri()+'?mode=ro', uri=True)) as db:
        return tuple(db.iterdump())


class K05ReadBoundaryTests(unittest.TestCase):
    def api(self):
        return importlib.import_module('storage.trading_feedback')  # PROPOSED

    def test_missing_store_does_not_create_replacement_or_migration(self):
        api=self.api()
        with TemporaryDirectory() as directory:
            root=Path(directory)
            for absent in ('canonical.sqlite', 'dispatch.sqlite'):
                with self.subTest(absent=absent):
                    other=root/'other.sqlite'
                    with closing(sqlite3.connect(other)) as db:
                        db.execute('CREATE TABLE harmless_marker(value TEXT)');db.commit()
                    before=logical_store(other);missing=root/absent
                    canonical,dispatch=(missing,other) if absent.startswith('canonical') else (other,missing)
                    with self.assertRaises(api.TradingFeedbackReadError):
                        with api.open_trading_feedback_reader(canonical,dispatch,namespace='FIXTURE'):
                            self.fail('Missing store unexpectedly opened')
                    self.assertFalse(missing.exists());self.assertEqual(before,logical_store(other))
                    other.unlink()

    def test_unknown_or_incomplete_schema_is_refused_without_migration(self):
        api=self.api()
        with TemporaryDirectory() as directory:
            path=Path(directory)/'old.sqlite'
            with closing(sqlite3.connect(path)) as db:
                db.executescript('CREATE TABLE schema_migrations(migration_name TEXT PRIMARY KEY);'
                                 'CREATE TABLE harmless_marker(value TEXT);'
                                 "INSERT INTO harmless_marker VALUES('UNCHANGED');")
                db.commit()
            before=logical_store(path)
            with self.assertRaises(api.TradingFeedbackReadError):
                with api.open_trading_feedback_reader(path,path,namespace='FIXTURE'):
                    self.fail('Unrecognized schema unexpectedly opened')
            self.assertEqual(before,logical_store(path))


class K05ActualOpenOwnerHistoryTests(unittest.TestCase):
    """Real fake-provider ACK history; deliberately NOT a closed/H16 fixture."""
    def setUp(self):
        self.api=importlib.import_module('storage.trading_feedback')  # PROPOSED
        self.h=dispatch_fixtures.TradingDispatchV02Tests(methodName='runTest')
        self.addCleanup(lambda:self.assertTrue(self.h.doCleanups(),'Actual owner fixture cleanup failed'))
        self.h.setUp()
        # Use the actual E6-owner-created namespace store, not a SQL namespace
        # insert. Rebind the helper's real writer ports before any dispatch.
        self.path=self.h.fixture.root/'admission.sqlite'
        self.assertTrue(self.path.is_file())
        self.h.canonical.close();self.h.dispatch.close()
        self.h.canonical=open_paper_runtime_journal(self.path,require_existing=True)
        self.h.dispatch=open_product_dispatch_journal(self.path)
        self.addCleanup(self.h.canonical.close);self.addCleanup(self.h.dispatch.close)
        self.h.canonical.persist_risk_decision(self.h.risk)
        self.h.canonical.persist_approved_trade_plan(self.h.plan)
        self.service,self.provider=self.h.service([self.h.ack()])
        self.assertEqual('ACK_PENDING',self.service.execute(
            self.h.prepared,expected_revision=self.h.fixture.revision).status)
        self.run_id='fixture-run';self.plan_id=self.h.plan['trade_plan_id']

    def read(self,*,namespace='FIXTURE',run_id=None,trade_plan_id=None):
        with self.api.open_trading_feedback_reader(self.path,self.path,namespace=namespace) as reader:
            return reader.snapshot(self.run_id if run_id is None else run_id,
                                   self.plan_id if trade_plan_id is None else trade_plan_id)

    def baseline(self):
        return (self.h.dispatch.recover(self.run_id),
                self.h.canonical.recover(trade_plan_id=self.plan_id),
                tuple(dict(row) for row in self.provider.calls),logical_store(self.path))

    @contextmanager
    def corrupt_text(self,table,column,value,trigger):
        # Isolated genuine owner rows only; restore both bytes and exact schema.
        with closing(sqlite3.connect(self.path)) as writer:
            originals=writer.execute('SELECT rowid,'+column+' FROM '+table).fetchall()
            statement=writer.execute('SELECT sql FROM sqlite_master WHERE name=?',(trigger,)).fetchone()[0]
            writer.execute('DROP TRIGGER '+trigger)
            writer.executemany('UPDATE '+table+' SET '+column+'=? WHERE rowid=?',
                [(value(original) if callable(value) else value,row_id) for row_id,original in originals])
            writer.execute(statement);writer.commit()
            try:yield
            finally:
                writer.execute('DROP TRIGGER '+trigger)
                writer.executemany('UPDATE '+table+' SET '+column+'=? WHERE rowid=?',[(original,row_id) for row_id,original in originals])
                writer.execute(statement);writer.commit()

    def test_actual_ack_and_pending_order_are_not_closed_performance(self):
        before=self.baseline();snapshot=self.read()
        self.assertEqual('FIXTURE',snapshot.namespace)
        self.assertEqual('SIMULATED_MECHANICS',snapshot.execution)
        self.assertFalse(snapshot.available)
        self.assertIsNone(snapshot.canonical.trade_result)
        self.assertEqual((),snapshot.canonical.fills)
        self.assertEqual(before,self.baseline())

    def test_namespace_mismatch_refused_without_owner_effect(self):
        before=self.baseline()
        with self.assertRaises(self.api.TradingFeedbackReadError):self.read(namespace='LOCAL_RESEARCH')
        self.assertEqual(before,self.baseline())

    def test_unknown_run_or_unassociated_plan_is_not_selected_by_latest_row(self):
        now=self.h.fixture.clock[0]+timedelta(seconds=1)
        risk,other_plan,_=approved(self.h.fixture.identity,now)
        self.h.canonical.persist_risk_decision(risk)
        self.h.canonical.persist_approved_trade_plan(other_plan)
        self.assertNotEqual(self.plan_id,other_plan['trade_plan_id'])
        before=self.baseline()
        for run_id,plan_id in (('unknown-owned-run',self.plan_id),
                               (self.run_id,other_plan['trade_plan_id'])):
            with self.subTest(run_id=run_id,plan_id=plan_id),self.assertRaises(self.api.TradingFeedbackReadError):
                self.read(run_id=run_id,trade_plan_id=plan_id)
        self.assertEqual(before,self.baseline())

    def test_reader_uses_real_readonly_query_only_connections_and_no_writer_factory(self):
        before=self.baseline();opened=[];write_attempts=[]
        real_connect=sqlite3.connect
        from storage._sqlite_registry import _apply_migrations as model_migrations
        denied={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,
                sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_ALTER_TABLE,
                sqlite3.SQLITE_CREATE_TRIGGER,sqlite3.SQLITE_DROP_TRIGGER,sqlite3.SQLITE_ATTACH}
        def connect(*args,**kwargs):
            if args[0]==':memory:':return real_connect(*args,**kwargs)
            self.assertIs(kwargs.get('uri'),True)
            query=parse_qs(urlsplit(str(args[0])).query)
            self.assertEqual(['ro'],query.get('mode'))
            self.assertNotIn('immutable',query)  # actual live existing store, not a sealed copy
            db=real_connect(*args,**kwargs)
            def authorizer(action,one,two,database,trigger):
                if action in denied:
                    write_attempts.append((action,one));return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorizer);opened.append(db);return db
        def memory_only_migrations(db,*args,**kwargs):
            self.assertEqual('',db.execute('PRAGMA database_list').fetchone()['file'])
            return model_migrations(db,*args,**kwargs)
        with ExitStack() as traps:
            traps.enter_context(patch.object(self.api.sqlite3,'connect',side_effect=connect))
            traps.enter_context(patch('storage._sqlite_registry._apply_migrations',side_effect=memory_only_migrations))
            traps.enter_context(patch('storage.runtime.open_paper_runtime_journal',side_effect=AssertionError('Writer factory called')))
            traps.enter_context(patch('storage.product_dispatch.open_product_dispatch_journal',side_effect=AssertionError('Writer factory called')))
            with self.api.open_trading_feedback_reader(self.path,self.path,namespace='FIXTURE') as reader:
                reader.snapshot(self.run_id,self.plan_id)
                self.assertTrue(opened)
                for db in opened:self.assertEqual(1,db.execute('PRAGMA query_only').fetchone()[0])
        self.assertEqual([],write_attempts)
        self.assertEqual(before,self.baseline())

    def test_repeated_snapshots_do_not_allocate_generation_or_mutate_canonical_history(self):
        before=self.baseline();first=self.read();second=self.read()
        self.assertEqual(first.observed_process_generation,second.observed_process_generation)
        self.assertEqual(first.original_binding_json,second.original_binding_json)
        self.assertEqual(first.canonical,second.canonical)
        with self.assertRaises((FrozenInstanceError,AttributeError)):
            first.observed_process_generation=999
        # StoredCanonicalObject.payload must be a decoded copy; edit no DB.
        copy=first.canonical.approved_trade_plan.payload;copy['trade_plan_id']='CONSUMER_MUTATION_ONLY'
        self.assertEqual(self.plan_id,self.read().canonical.approved_trade_plan.payload['trade_plan_id'])
        self.assertEqual(before,self.baseline())

    def test_new_real_owner_generation_does_not_turn_the_old_snapshot_into_current_authority(self):
        old=self.read();graph=self.h.canonical.recover(trade_plan_id=self.plan_id)
        current=self.h.dispatch.recover(self.run_id)
        self.h.fixture.clock[0]+=timedelta(seconds=1)
        self.h.dispatch.begin_process(self.run_id,'k05-actual-successor',
            expected_generation=current.process_generation,now=self.h.fixture.clock[0])
        before=self.baseline();new=self.read()
        self.assertEqual(current.process_generation,old.observed_process_generation)
        self.assertEqual(current.process_generation+1,new.observed_process_generation)
        self.assertEqual(old.original_binding_json,new.original_binding_json)
        self.assertEqual(graph,new.canonical)
        self.assertFalse(new.available)  # no closed TradeResult was produced
        # These observed generations are read fences. Neither may be called an
        # original financial-result producer without its own immutable link.
        self.assertEqual(before,self.baseline())

    def test_each_snapshot_rechecks_owned_schema_after_open(self):
        with self.api.open_trading_feedback_reader(self.path,self.path,namespace='FIXTURE') as reader:
            with closing(sqlite3.connect(self.path)) as writer:
                trigger=writer.execute("SELECT sql FROM sqlite_master WHERE name='product_dispatch_claims_no_delete'").fetchone()[0]
                writer.execute('DROP TRIGGER product_dispatch_claims_no_delete');writer.commit()
                try:
                    for unused in range(2):
                        with self.assertRaises(self.api.TradingFeedbackReadError):reader.snapshot(self.run_id,self.plan_id)
                finally:
                    writer.execute(trigger);writer.commit()
            self.assertFalse(reader.snapshot(self.run_id,self.plan_id).available)

    def test_blob_binding_and_claim_are_typed_denials_with_owned_schema_restored(self):
        for table,column,trigger in (('product_dispatch_runs','binding_json','product_dispatch_runs_no_update'),
                ('product_dispatch_intents','request_json','product_dispatch_intents_no_update')):
            with self.subTest(table=table),self.corrupt_text(table,column,lambda raw:sqlite3.Binary(raw.encode('utf-8')),trigger):
                with self.assertRaises(self.api.TradingFeedbackReadError):self.read()

    def test_exact_schema_canonical_payload_hash_corruption_is_refused(self):
        # Deliberately corrupt all immutable hashes in this isolated fixture;
        # no financial outcome or CLOSED row is manufactured.
        with self.corrupt_text('paper_runtime_objects','payload_hash','sha256:'+'f'*64,'paper_runtime_objects_immutable_update'):
            with self.assertRaises(self.api.TradingFeedbackReadError):self.read()

    def test_actual_split_store_append_during_read_is_fenced(self):
        from storage.runtime import PaperRuntimeJournal
        destinations=(self.h.fixture.root/'history-canonical-copy.sqlite',self.h.fixture.root/'history-dispatch-copy.sqlite')
        for path in destinations:
            with closing(sqlite3.connect(path)) as copy:
                self.h.dispatch._db.backup(copy);copy.execute('PRAGMA journal_mode=WAL')
        original=PaperRuntimeJournal.recover
        def actual_append(journal,**kwargs):
            result=original(journal,**kwargs)
            with open_product_dispatch_journal(destinations[1]) as successor:
                successor.begin_process(self.run_id,'actual-split-history-successor',expected_generation=1,now=self.h.fixture.clock[0]+timedelta(seconds=1))
            return result
        before=self.baseline()
        with self.api.open_trading_feedback_reader(*destinations,namespace='FIXTURE') as reader:
            with patch.object(PaperRuntimeJournal,'recover',actual_append):
                with self.assertRaises(self.api.TradingFeedbackReadError) as caught:reader.snapshot(self.run_id,self.plan_id)
                self.assertEqual(caught.exception.code,'TRADING_HISTORY_SNAPSHOT_CHANGED')
        self.assertEqual(before,self.baseline())

    def test_actual_revocation_does_not_refresh_permission_or_relabel_history(self):
        from registry import EvidenceGateError
        original=self.read()
        self.h.fixture.e6.revoke_approval(self.h.fixture.identity,
            authenticated_human=self.h.fixture.auth.authenticate('FIXTURE_AUTH_PROOF'),reason='history-fixture-revocation',command_id='history-revoke')
        with self.assertRaises(EvidenceGateError):self.h.fixture.permission()
        before=self.baseline()
        with patch.object(self.h.admission,'evaluate',side_effect=AssertionError('History refreshed trading admission')):
            after=self.read()
        self.assertEqual(original,after);self.assertEqual(before,self.baseline())

    def test_original_strategy_definition_requires_an_object_not_json_scalar(self):
        for malformed in ('[]','null'):
            with self.subTest(shape=malformed),self.corrupt_text('strategy_versions','definition_json',malformed,'strategy_versions_immutable_content'):
                with self.assertRaises(self.api.TradingFeedbackReadError):self.read()

    def test_public_constructor_uses_actual_read_port_and_keeps_ack_performance_unavailable(self):
        from application.cloud.trading_feedback import build_trading_feedback,validate_trading_feedback
        before=self.baseline()
        with self.api.open_trading_feedback_reader(self.path,self.path,namespace='FIXTURE') as reader:
            value=build_trading_feedback(reader,self.run_id,self.plan_id,performance_opt_in=True)
        validate_trading_feedback(value)
        self.assertEqual(value['provenance']['kind'],'FAKE_PROVIDER_VERIFICATION')
        self.assertEqual(value['availability'],'UNAVAILABLE');self.assertIsNone(value['performance'])
        self.assertEqual(value['actual_live'],{'status':'NOT_RUN','performance':None})
        self.assertIsNone(value['closed_at']);self.assertNotIn('observed_process_generation',json.dumps(value))
        self.assertEqual(before,self.baseline())


# H16-dependent tests are specified in the design, not implemented as skipped
# tests or fabricated CLOSED rows here. Apply only after an actual owner-complete
# fake-provider exit/funding/TradeResult fixture exists.
