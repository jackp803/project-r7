"""Actual public scan reconstruction, preserving the product eight MiB limit."""
import hashlib,json,unittest
from unittest.mock import patch
import prepare_current_supplement_archive as helper

class ScanChunkTests(unittest.TestCase):
    def test_known_public_scan_exceeds_default_but_bounded_chunks_reconstruct(self):
        path=helper.BASE/'l01-l05-audit-3ae6460-first.json'
        with self.assertRaises(ValueError):helper.CapturedEvidence(helper.PROJECT).capture(path)
        raw,document=helper.large_scan_document()
        self.assertEqual('3ae6460c69a8a8f90588c396b819af7079e7546d',document['requested_head'])
        chunks,metadata=helper.public_scan_chunks(raw)
        self.assertGreater(len(chunks),1)
        text=b''.join(bytes.fromhex(json.loads(chunk)['text_hex']) for chunk in chunks).decode()
        self.assertEqual(helper.sanitize_public(raw),text)
        self.assertEqual(helper.sha(text.encode()),metadata['sanitized_complete_hash'])
        self.assertEqual(helper.sha(raw),metadata['original_hash'])
        self.assertTrue(all(len(chunk)<8*1024*1024 for chunk in chunks))
        self.assertEqual(list(range(1,len(chunks)+1)),[json.loads(chunk)['part'] for chunk in chunks])
        self.assertTrue(all(helper.sanitize_public(chunk).encode()==chunk for chunk in chunks))

    def test_larger_read_is_only_for_fixed_public_scan_and_exact_commitment(self):
        with patch('prepare_current_supplement_archive.artifact_bytes',return_value=b'{}') as reader:
            with self.assertRaisesRegex(ValueError,'Known public scan commitment'):
                helper.large_scan_document()
        self.assertEqual((helper.BASE,'l01-l05-audit-3ae6460-first.json',16*1024*1024),reader.call_args.args)

if __name__=='__main__':unittest.main(verbosity=2)
