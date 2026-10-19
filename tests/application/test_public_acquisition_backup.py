"""Offline public-capture inputs survive private backup without becoming authority."""
import json
from pathlib import Path
import unittest

from application.config import ProductConfig
from application.datasets.catalog import canonical
from application.datasets.okx_public import acquire_okx_public_dataset
from application.local_owners import LocalOwners
from application.platform.product_backup import create_product_backup,restore_product_backup,ProductBackupError
from tests.application import test_okx_public_dataset as public_fixture

class PublicAcquisitionBackupTests(unittest.TestCase):
    def setUp(self):
        helper=public_fixture.PublicDatasetTests();helper.setUp();self.addCleanup(helper.doCleanups)
        self.helper=helper;self.base=helper.root.parent
        data=self.base/'product-data'
        self.config=ProductConfig('r7-product-config-v0.2','public-backup-source',data,None,data/'canonical.sqlite3')
        self.capture=data/'datasets'/'public-capture'
        with LocalOwners(self.config).registry_factory() as registry:registry.lifecycle_counts()

    def acquire(self,opener=None):
        return acquire_okx_public_dataset(self.capture,start=public_fixture.START,end=public_fixture.END,
                                         _opener=opener or self.helper.opener,_minimum_interval=0)

    def backup(self):return create_product_backup(self.config,self.base/'private-backup')

    def test_unselected_successful_public_capture_roundtrips_all_raw_receipts_and_stays_inhibited(self):
        self.assertEqual(self.acquire()['status'],'DATASET_ACQUIRED')
        before={p.relative_to(self.config.local_data_root).as_posix():p.read_bytes() for p in self.capture.rglob('*') if p.is_file()}
        self.backup()
        restored=restore_product_backup(self.config,self.base/'private-backup',self.base/'restored')
        for relative,raw in before.items():self.assertEqual((self.base/'restored'/relative).read_bytes(),raw)
        from application.platform.restoration import require_valid_restoration
        from application.config import load_config
        config=load_config(self.base/'restored/restored-product.json')
        self.assertEqual(require_valid_restoration(config)['status'],'RESTORED_INHIBITED')
        self.assertIsNone(config.cloud_root)

    def test_rejected_gap_remains_backup_evidence_without_dataset_admission(self):
        self.helper.candles.pop(5)
        self.assertEqual(self.acquire()['status'],'ACQUISITION_REJECTED')
        self.backup()

    def test_prepared_only_interrupted_capture_and_unreceipted_body_are_retained(self):
        from application.datasets.okx_public import PublicTransport,HISTORY,millis
        self.capture.mkdir(parents=True)
        # Inject a crash after response bytes were published. No acquisition
        # summary or result can be invented from this interrupted capture.
        def crash(root,name,value):
            if name.endswith('-result.json'):raise KeyboardInterrupt()
            from application.datasets.okx_public import save
            original_save(root,name,value)
        from unittest.mock import patch
        from application.datasets import okx_public
        original_save=okx_public.save
        transport=PublicTransport(self.capture,opener=self.helper.opener,minimum_interval=0)
        with patch.object(okx_public,'save',side_effect=crash),self.assertRaises(KeyboardInterrupt):
            transport.get(HISTORY,dict(instId='BTC-USDT-SWAP',after=millis(public_fixture.END),limit='100',bar='4H'))
        self.assertFalse((self.capture/'acquisition.json').exists())
        self.backup()

    def test_prepared_receipt_alone_does_not_infer_a_successful_request_or_dataset(self):
        from application.datasets.okx_public import PublicTransport,HISTORY,millis
        self.capture.mkdir(parents=True)
        def interrupted(*args,**kwargs):raise KeyboardInterrupt()
        transport=PublicTransport(self.capture,opener=interrupted,minimum_interval=0)
        with self.assertRaises(KeyboardInterrupt):
            transport.get(HISTORY,dict(instId='BTC-USDT-SWAP',after=millis(public_fixture.END),limit='100',bar='4H'))
        self.assertEqual(len(list(self.capture.rglob('*-attempt.json'))),1)
        from application.datasets.public_capture import public_capture_inventory
        refs,hashes,manifest=public_capture_inventory(self.config.local_data_root,'datasets/public-capture',
            {p.relative_to(self.config.local_data_root).as_posix() for p in self.capture.rglob('*') if p.is_file()})
        self.assertIsNone(manifest);self.assertEqual(len(refs),1)
        self.backup()

    def test_partial_http_body_failure_roundtrips_without_becoming_a_dataset(self):
        from http.client import IncompleteRead
        class Partial(public_fixture.Response):
            def read1(self,size):raise IncompleteRead(b'{"code":',100)
        def opener(request,timeout):
            response=Partial(b'');response.url=request.full_url;return response
        self.assertEqual(self.acquire(opener)['status'],'ACQUISITION_REJECTED')
        self.backup()
        restore_product_backup(self.config,self.base/'private-backup',self.base/'restored')
        target=self.base/'restored/datasets/public-capture'
        self.assertEqual((target/'requests/001-partial-response.bin').read_bytes(),b'{"code":')
        self.assertFalse((target/'dataset.json').exists())

    def test_selected_successful_capture_and_explicit_diagnostic_refs_are_covered(self):
        self.acquire()
        selected=dict(selection_mode='DIAGNOSTIC_DEVELOPMENT_ONLY',dataset_ref='datasets/public-capture/dataset.json',
            split_policy_ref='selected-split.json',cost_policy_ref='selected-cost.json',requested_dataset_profile='okx-btc-4h',
            requested_validation_profile='diagnostic',requested_robustness_profile='diagnostic')
        # Backup checks coverage/bytes, not execution validity of policy bodies.
        for name in ('selected-split.json','selected-cost.json'):
            (self.config.local_data_root/name).write_text(canonical(dict(namespace='LOCAL_RESEARCH',status='UNEXECUTED_ARCHIVE_TEST_INPUT')),encoding='utf-8')
        (self.config.local_data_root/'owner-selections.json').write_text(canonical(dict(schema_version='r7-owner-selections-v0.2',
            cloud_root_id=None,research_policies={'diagnostic':selected})),encoding='utf-8')
        self.backup()

    def test_tampered_response_cannot_be_backed_up_as_original_public_capture(self):
        self.acquire();path=self.capture/'requests/001-response.bin';path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaises(ProductBackupError):self.backup()

    def test_unknown_files_and_private_endpoint_or_extra_secret_field_remain_rejected(self):
        self.acquire();path=self.capture/'requests/001-attempt.json';original=path.read_bytes();value=json.loads(original)
        value['url']='https://www.okx.com/api/v5/account/balance'
        path.write_text(canonical(value),encoding='utf-8')
        with self.assertRaises(ProductBackupError):self.backup()
        value=json.loads(original);value['api_key']='forbidden-extra-field'
        path.write_text(canonical(value),encoding='utf-8')
        with self.assertRaises(ProductBackupError):self.backup()
        path.write_bytes(original);(self.capture/'unexpected.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ProductBackupError):self.backup()

    def test_orphan_result_and_reported_count_conflict_are_rejected(self):
        self.acquire();summary=self.capture/'acquisition.json';original=summary.read_bytes();value=json.loads(original)
        value['provider_requests']=1;summary.write_text(canonical(value),encoding='utf-8')
        with self.assertRaises(ProductBackupError):self.backup()
        summary.write_bytes(original)
        (self.capture/'requests/001-attempt.json').unlink()
        with self.assertRaises(ProductBackupError):self.backup()
