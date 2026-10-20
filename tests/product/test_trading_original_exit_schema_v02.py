"""ONE real owner-populated immutable schema case.
Controlled FIXTURE provider responses only. SQL is assertion-only attacks against
owner-created rows, rolled back after every denial. No positive SQL financial rows.
"""
import json
import re
import sqlite3
import unittest

from brokers.okx_demo import stable_okx_cl_ord_id
from execution.close import prepare_close_order
from position.exit_requests import CurrentExitAuthority, interpret_exit_request
from strategy.v02.exits import ExitRequest
from tests.product import h01_original_exit_fixture as fixtures


_TABLES = ('product_exit_anchors','product_exit_decisions','product_exit_publications')


def _snapshot(db):
    # Fixed table names only; capture ALL rows of all three tables, not one field.
    return {name: tuple(tuple(row) for row in db.execute(
        'SELECT * FROM '+name+' ORDER BY run_id,entry_decision_id').fetchall())
        for name in _TABLES}


class TradingOriginalExitSchemaV02Tests(unittest.TestCase):
    def test_actual_exit_anchor_decision_and_publication_reject_update_delete_replace_recursive_off(self):
        with fixtures.H01OriginalExitFixture(self) as c:
            f=c.f; run_id=c.service.run_id; entry=c.entry_decision
            held=c.runner.evaluate_original_exit(f.bundle.boundary,**c.exit_arguments())
            self.assertEqual('HOLD',held.status)
            self.assertIsNone(held.operation_id)
            self.assertIsNone(held.dispatch_outcome)
            anchor=f.dispatch.exit_anchor(run_id,entry.decision_id)
            self.assertIsNotNone(anchor)
            self.assertEqual(held.anchor,anchor.anchor)
            self.assertIsNone(f.dispatch.exit_decision(run_id,entry.decision_id))
            # Derive deadline from actual persisted first-fill anchor, never seed
            # an authorized action/terminal state or reset first-fill clock.
            c.clock[0]=anchor.anchor.hold_deadline
            current=c.refresh_protected()
            arguments=c.exit_arguments()
            request=ExitRequest(json.dumps(entry.exit_request))
            expected=interpret_exit_request(request,CurrentExitAuthority(
                current.current_position_projection.payload,c.plan,anchor.anchor,
                arguments['market_snapshot'],arguments['market_freshness_classification'],
                c.clock[0],arguments['action_expires_at']))
            self.assertEqual('AUTHORIZED',expected.status)
            self.assertEqual(('E5_MAX_HOLD_REACHED',),expected.reason_codes)
            expected_request=prepare_close_order(expected.position_action,c.plan,
                current.current_position_projection.payload,now=c.clock[0])
            native_client=stable_okx_cl_ord_id(expected_request.client_order_id).provider_cl_ord_id
            c.append(dict(code='0',data=[dict(ordId='3456',clOrdId=native_client,sCode='0')]))
            outcome=c.runner.evaluate_original_exit(f.bundle.boundary,**arguments)
            self.assertEqual('DISPATCHED',outcome.status)
            self.assertEqual('ACK_PENDING',outcome.dispatch_outcome.status)
            self.assertEqual(expected_request.order_request_id,outcome.operation_id)
            decision=f.dispatch.exit_decision(run_id,entry.decision_id)
            self.assertEqual(outcome.decision_id,decision.decision_id)
            self.assertEqual([dict(kind='POSITION_ACTION',payload=expected.position_action)],decision.effects)
            self.assertEqual((),f.dispatch.pending_exit_publications(run_id))
            self.assertEqual('EXIT_REQUESTED',c.assert_binding().current_position_projection.payload['lifecycle_state'])
            self.assertEqual(3,len([call for call in c.provider.calls if call['method']=='POST']))
            self.assertFalse(c.provider._responses)
            calls_before=tuple(c.provider.calls)

            # This is the actual owner-created dispatch connection. Changing only
            # connection pragmas and assertion attacks is confined to this fixture.
            db=f.dispatch._db
            self.assertFalse(db.in_transaction)
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA recursive_triggers=OFF')
            self.assertEqual(1,db.execute('PRAGMA foreign_keys').fetchone()[0])
            self.assertEqual(0,db.execute('PRAGMA recursive_triggers').fetchone()[0])
            before=_snapshot(db)
            for table in _TABLES:
                self.assertEqual(1,len(before[table]))
                row=db.execute('SELECT run_id,entry_decision_id FROM '+table).fetchone()
                self.assertEqual((run_id,entry.decision_id),tuple(row))
            self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())

            for table in _TABLES:
                attacks=(
                    ('update','UPDATE '+table+' SET evidence_hash=? WHERE run_id=? AND entry_decision_id=?',
                        ('sha256:'+'f'*64,run_id,entry.decision_id),'Original exit record is immutable'),
                    ('delete','DELETE FROM '+table+' WHERE run_id=? AND entry_decision_id=?',
                        (run_id,entry.decision_id),'Original exit record is immutable'),
                    # Every inserted value is the exact actual existing row. All
                    # original entry/generation/anchor/decision FKs are valid.
                    ('replace','INSERT OR REPLACE INTO '+table+' SELECT * FROM '+table+
                        ' WHERE run_id=? AND entry_decision_id=?',
                        (run_id,entry.decision_id),'Original exit replacement is forbidden'),
                )
                for action,sql,parameters,message in attacks:
                    with self.subTest(table=table,action=action):
                        try:
                            with self.assertRaisesRegex(sqlite3.IntegrityError,'^'+re.escape(message)+'$'):
                                db.execute(sql,parameters)
                        finally:
                            db.rollback()
                        self.assertFalse(db.in_transaction)
                        self.assertEqual(before,_snapshot(db))
                        self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
                        self.assertEqual(1,db.execute('PRAGMA foreign_keys').fetchone()[0])
                        self.assertEqual(0,db.execute('PRAGMA recursive_triggers').fetchone()[0])
            self.assertEqual(anchor,f.dispatch.exit_anchor(run_id,entry.decision_id))
            self.assertEqual(decision,f.dispatch.exit_decision(run_id,entry.decision_id))
            self.assertEqual(calls_before,tuple(c.provider.calls),'SQL attacks must perform no provider I/O')
