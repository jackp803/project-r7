"""Disposable schema constraints and SQLite topology, no financial authority."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import os
import sqlite3
import unittest

import tests.storage.test_stop_cleanup_constraints as cleanup_constraints
from storage.product_finalization import require_distinct_journals
from storage.runtime import open_paper_runtime_journal


class TradeFinalizationConstraintTests(unittest.TestCase):
    def test_outbox_and_receipt_immutable_with_valid_foreign_keys_and_recursive_triggers_off(self):
        helper=cleanup_constraints.StopCleanupConstraintTests(methodName='runTest')
        self.addCleanup(helper.doCleanups)
        db,cleanup=helper.claim_fixture()
        at=cleanup[-2];generation=cleanup[-1]
        outbox=('run','close','stop','{}','schema-source','[]','schema-effects',at,generation)
        receipt=('run','close','schema-source','schema-effects',at,generation)
        for table,row,changed,message in (
            ('product_dispatch_finalization_outbox',outbox,'source_hash','Finalization source and effects are immutable'),
            ('product_dispatch_finalization_publications',receipt,'source_hash','Finalization receipt is immutable')):
            db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in row)+')',row);db.commit()
            self.assertEqual([],list(db.execute('PRAGMA foreign_key_check')))
            for sql,params,expected in (
                ('UPDATE '+table+' SET '+changed+'=?',('changed',),message),
                ('DELETE FROM '+table,(),message),
                ('INSERT OR REPLACE INTO '+table+' VALUES('+','.join('?' for _ in row)+')',row,
                 'Finalization replacement is forbidden' if table.endswith('outbox') else 'Finalization receipt replacement is forbidden')):
                with self.subTest(table=table,statement=sql.split()[0]):
                    with self.assertRaises(sqlite3.IntegrityError) as caught:db.execute(sql,params)
                    self.assertIn(expected,str(caught.exception));db.rollback()
                    self.assertEqual([row],[tuple(value) for value in db.execute('SELECT * FROM '+table)])
            self.assertEqual(0,db.execute('PRAGMA recursive_triggers').fetchone()[0])
            self.assertEqual([],list(db.execute('PRAGMA foreign_key_check')))

    def test_shared_connection_same_file_and_hardlink_are_refused_before_writes(self):
        with TemporaryDirectory() as temporary:
            path=Path(temporary)/'canonical.sqlite'
            first=open_paper_runtime_journal(path)
            try:
                first_connection=first._store._connection
                with self.assertRaisesRegex(ValueError,'DISTINCT_IDLE_JOURNALS'):
                    require_distinct_journals(SimpleNamespace(_db=first_connection),first)
                alias=Path(temporary)/'hardlink.sqlite';os.link(path,alias)
                for target in (path,alias):
                    second=open_paper_runtime_journal(target)
                    try:
                        with self.assertRaisesRegex(ValueError,'DISTINCT_LOCAL_DATABASE_FILES'):
                            require_distinct_journals(SimpleNamespace(_db=first_connection),second)
                        self.assertFalse(first_connection.in_transaction)
                        self.assertFalse(second._store._connection.in_transaction)
                    finally:second.close()
            finally:first.close()

    def test_distinct_files_require_both_owners_idle(self):
        with TemporaryDirectory() as temporary:
            first=open_paper_runtime_journal(Path(temporary)/'one.sqlite')
            second=open_paper_runtime_journal(Path(temporary)/'two.sqlite')
            try:
                dispatch=SimpleNamespace(_db=first._store._connection)
                require_distinct_journals(dispatch,second)
                for connection in (dispatch._db,second._store._connection):
                    connection.execute('BEGIN')
                    with self.assertRaisesRegex(ValueError,'DISTINCT_IDLE_JOURNALS'):
                        require_distinct_journals(dispatch,second)
                    connection.rollback()
                require_distinct_journals(dispatch,second)
            finally:second.close();first.close()
