"""Schema-only regression: valid FKs must not mask native cleanup uniqueness.

Rows below are disposable constraint fixtures, never canonical lifecycle facts
or cleanup authority. The owner-flow test separately creates a genuine claim.
"""
import sqlite3
import unittest

import tests.storage.test_product_dispatch_v02 as dispatch_fixtures


class StopCleanupConstraintTests(unittest.TestCase):
    def claim_fixture(self):
        helper=dispatch_fixtures.ProductDispatchV02Tests(methodName='runTest')
        helper.setUp();self.addCleanup(helper.doCleanups)
        journal,lease=helper.initialized()
        for operation in ('stop','close','entry'):
            journal.prepare('run',operation,helper.request('constraint'+operation),lease=lease,now=helper.now)
            journal.claim_dispatch('run',operation,lease=lease,now=helper.now)
            self.assertEqual('READBACK_REQUIRED',journal.operation('run',operation).recovery_disposition)
        db=journal._db
        db.execute('PRAGMA recursive_triggers=OFF')
        self.assertEqual(1,db.execute('PRAGMA foreign_keys').fetchone()[0])
        self.assertEqual(0,db.execute('PRAGMA recursive_triggers').fetchone()[0])
        row=('run','stop','close','2345','OKX_FIXTURE','sanitized-account',
             '{}','schema-fixture-only','{}','schema-fixture-only',
             helper.now.isoformat().replace('+00:00','Z'),lease.generation)
        db.execute('INSERT INTO product_dispatch_stop_cleanup_claims VALUES('+','.join('?' for _ in row)+')',row)
        db.commit()
        self.assertEqual([],list(db.execute('PRAGMA foreign_key_check')))
        return db,row

    def test_native_unique_replace_denies_alternate_valid_claim_key_with_recursive_triggers_off(self):
        db,original=self.claim_fixture()
        alternative=list(original);alternative[1]='entry'
        self.assertIsNotNone(db.execute('SELECT 1 FROM product_dispatch_claims WHERE run_id=? AND operation_id=?',
            (alternative[0],alternative[1])).fetchone())
        self.assertIsNone(db.execute('SELECT 1 FROM product_dispatch_stop_cleanup_claims WHERE run_id=? AND stop_operation_id=?',
            (alternative[0],alternative[1])).fetchone())
        with self.assertRaises(sqlite3.IntegrityError) as caught:
            db.execute('INSERT OR REPLACE INTO product_dispatch_stop_cleanup_claims VALUES('+','.join('?' for _ in alternative)+')',alternative)
        self.assertIn('Stop cleanup claim replacement is forbidden',str(caught.exception))
        db.rollback()
        rows=db.execute('SELECT * FROM product_dispatch_stop_cleanup_claims').fetchall()
        self.assertEqual([original],[tuple(row) for row in rows])
        self.assertEqual([],list(db.execute('PRAGMA foreign_key_check')))
