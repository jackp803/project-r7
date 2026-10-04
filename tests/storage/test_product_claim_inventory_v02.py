"""Real migrated journal reads; bulk rows are fixture history, never authority."""
import unittest
from dataclasses import replace

import tests.storage.test_product_dispatch_v02 as dispatch_fixtures
from storage.product_dispatch import ProductDispatchError, _json, _stamp
from registry.product_assessment import digest


def seed_claim_history(journal, owner, lease, now, *, count, role='ENTRY', prefix='history', corrupt_last=False):
    """Build a large immutable SQLite fixture in one transaction, without I/O."""
    body=dict(instId='BTC-USDT-SWAP',tdMode='isolated',posSide='net',side='buy',ordType='market',sz='10')
    key='clOrdId'
    if role=='PROTECTION_STOP':
        body.update(side='sell',ordType='conditional',slTriggerPx='55000',slOrdPx='-1',slTriggerPxType='last',reduceOnly=True)
        key='algoClOrdId'
    intents=[];claims=[]
    for index in range(count):
        client=f'{prefix}{index:06d}'; operation=f'{prefix}-{index:06d}'
        request=dict(role=role,path='/api/v5/trade/order-algo' if role=='PROTECTION_STOP' else '/api/v5/trade/order',
            native_client_id=client,body=dict(body,**{key:client}),
            canonical_request_hash='sha256:'+'2'*64,authority_hash='sha256:'+'3'*64)
        raw=_json(request);hashed=digest(raw)
        if corrupt_last and index==count-1:hashed='sha256:'+'0'*64
        intents.append((lease.run_id,operation,raw,hashed,owner.release.provider_ref,owner.release.account_ref,client,_stamp(now)))
        claims.append((lease.run_id,operation,lease.generation,_stamp(now)))
    with journal._write():
        journal._db.executemany('INSERT INTO product_dispatch_intents VALUES(?,?,?,?,?,?,?,?)',intents)
        journal._db.executemany('INSERT INTO product_dispatch_claims VALUES(?,?,?,?)',claims)


class ProductClaimInventoryV02Tests(unittest.TestCase):
    def setUp(self):
        self.fixture=dispatch_fixtures.ProductDispatchV02Tests(methodName='runTest');self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.journal,self.lease=self.fixture.initialized()

    def seed(self,**kwargs):
        seed_claim_history(self.journal,self.fixture.owner,self.lease,self.fixture.now,**kwargs)

    def test_account_entry_and_stop_history_after_1000_is_retained(self):
        self.seed(count=1101)
        entries=self.journal.claimed_entries_for_account('run')
        self.assertEqual(1101,len(entries));self.assertEqual('history-001100',entries[-1].operation_id)
        self.seed(count=1101,role='PROTECTION_STOP',prefix='stop')
        stops=self.journal.claimed_protections_for_account('run')
        self.assertEqual(1101,len(stops))
        self.assertEqual(1101,len(self.journal.claimed_initial_protections_for_position('run','position')))

    def test_stream_keeps_ties_across_runs_and_exact_account_scope(self):
        self.seed(count=103)
        self.journal.ensure_run('run2',self.fixture.owner,now=self.fixture.now)
        lease=self.journal.begin_process('run2','pid:2',expected_generation=0,now=self.fixture.now)
        seed_claim_history(self.journal,self.fixture.owner,lease,self.fixture.now,count=102,prefix='other')
        different=replace(self.fixture.owner,release=replace(self.fixture.owner.release,account_ref='other-account'))
        self.journal.ensure_run('different',different,now=self.fixture.now)
        other=self.journal.begin_process('different','pid:3',expected_generation=0,now=self.fixture.now)
        seed_claim_history(self.journal,different,other,self.fixture.now,count=3,prefix='excluded')
        rows=list(self.journal.iter_claimed_entries_for_account('run'))
        self.assertEqual(205,len(rows));self.assertEqual(205,len({(r.run_id,r.operation_id) for r in rows}))
        self.assertEqual({'run','run2'},{r.run_id for r in rows})

    def test_new_claim_during_scan_cannot_be_silently_omitted(self):
        self.seed(count=201)
        stream=self.journal.iter_claimed_entries_for_account('run');next(stream)
        with self.fixture.open(self.fixture.path) as writer:
            seed_claim_history(writer,self.fixture.owner,self.lease,self.fixture.now,count=1,prefix='aaa')
        with self.assertRaisesRegex(ProductDispatchError,'DISPATCH_CLAIM_INVENTORY_CHANGED'):
            list(stream)

    def test_same_connection_observation_drift_during_scan_is_rejected(self):
        self.seed(count=201)
        stream=self.journal.iter_claimed_entries_for_account('run');next(stream)
        self.journal.observe('run','history-000200',dict(status='ACK_PENDING',provider_id='123',reason_code='PROVIDER_ACK_PENDING'),
            lease=self.lease,now=self.fixture.now)
        with self.assertRaisesRegex(ProductDispatchError,'DISPATCH_CLAIM_INVENTORY_CHANGED'):
            list(stream)

    def test_corrupt_request_in_last_page_is_not_dropped(self):
        self.seed(count=1001,corrupt_last=True)
        with self.assertRaisesRegex(ProductDispatchError,'DISPATCH_STORED_HASH_MISMATCH'):
            list(self.journal.iter_claimed_entries_for_account('run'))

    def test_initial_stop_scan_still_requires_exact_nonempty_position_identity(self):
        for value in (None,'',[], ' position '):
            with self.subTest(value=value),self.assertRaisesRegex(ProductDispatchError,'DISPATCH_BOUNDED_IDENTITY_REQUIRED'):
                list(self.journal.iter_claimed_initial_protections_for_position('run',value))


if __name__=='__main__':unittest.main()
