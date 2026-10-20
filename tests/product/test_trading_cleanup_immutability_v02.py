"""Bounded genuine cleanup regressions: TradingCleanupImmutabilityV02Tests."""
from dataclasses import replace
from datetime import timedelta
import json
import unittest
from unittest.mock import patch

import tests.product.test_trading_protected_close_v02 as fixtures
import tests.product.test_trading_inventory_v02 as inventory_fixtures

from tests.product.trading_stop_cleanup_fixtures import StopCleanupFixture


class TradingCleanupImmutabilityV02Tests(StopCleanupFixture,unittest.TestCase):
    def test_cleanup_claim_is_immutable_even_when_recursive_delete_triggers_are_disabled(self):
        import sqlite3
        self.flat();prepared=self.prepare(self.reads());self.flow.append('LOST_ACK');self.execute(prepared)
        connection=self.service.dispatch._db;connection.execute('PRAGMA recursive_triggers=OFF')
        original=connection.execute('SELECT * FROM product_dispatch_stop_cleanup_claims').fetchone()
        operations=[('UPDATE product_dispatch_stop_cleanup_claims SET source_hash=?',('changed',)),
            ('DELETE FROM product_dispatch_stop_cleanup_claims',()),
            ('INSERT OR REPLACE INTO product_dispatch_stop_cleanup_claims VALUES('+','.join('?' for _ in original)+')',tuple(original))]
        replacement=dict(original);replacement['stop_operation_id']=self.flow.entry_operation
        entry=self.service.dispatch.operation(self.service.run_id,self.flow.entry_operation)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.recovery_disposition,'READBACK_REQUIRED')
        self.assertIsNone(self.service.dispatch.stop_cleanup_claim(self.service.run_id,self.flow.entry_operation))
        operations.append((operations[-1][0],tuple(replacement.values())))
        for sql,args in operations:
            with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):connection.execute(sql,args)
            connection.rollback()
            self.assertEqual(tuple(connection.execute('SELECT * FROM product_dispatch_stop_cleanup_claims').fetchone()),tuple(original))
