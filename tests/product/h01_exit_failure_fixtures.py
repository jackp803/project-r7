"""Non-TestCase helpers for original EXIT fault cases.

Only real owner composition and assertion-only reads; no financial SQL writes.
"""
from tests.product import h01_entry_recovery_fixture as recovery_fixtures


def held_anchor(c):
    result=c.runner.evaluate_original_exit(c.f.bundle.boundary,**c.exit_arguments())
    c.test.assertEqual('HOLD',result.status)
    c.test.assertIsNone(result.operation_id)
    record=c.f.dispatch.exit_anchor(c.service.run_id,c.entry_decision.decision_id)
    c.test.assertEqual(result.anchor,record.anchor)
    c.test.assertEqual(c.first_projection.payload,record.evidence['source_position'])
    c.test.assertEqual(c.first_binding.payload,record.evidence['source_binding'])
    c.test.assertIsNone(c.f.dispatch.exit_decision(c.service.run_id,c.entry_decision.decision_id))
    return record


def at_original_deadline(c):
    anchor=held_anchor(c)
    c.clock[0]=anchor.anchor.hold_deadline
    c.refresh_protected()
    return anchor,c.exit_arguments()


def exit_rows(dispatch,run_id,entry_decision_id):
    # Fixed allowlisted E6 tables, test-owned temporary DB, SELECT only.
    return {table:tuple(dict(row) for row in dispatch._db.execute(
        'SELECT * FROM '+table+' WHERE run_id=? AND entry_decision_id=?',
        (run_id,entry_decision_id)).fetchall()) for table in
        ('product_exit_anchors','product_exit_decisions','product_exit_publications')}


def canonical_action(journal,action_id):
    row=journal._store._object_row('POSITION_ACTION',action_id)
    return None if row is None else dict(row)


def successor(c,stack):
    # Deliberately do NOT call H01RecoveryFixture.__enter__: that would create
    # another H01 setup. The tested successor recipe needs only these fields.
    bridge=recovery_fixtures.H01RecoveryFixture()
    bridge.fixture=c.f
    bridge.stack=stack
    return bridge.successor()
