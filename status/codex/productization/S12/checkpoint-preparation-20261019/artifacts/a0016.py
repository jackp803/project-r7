"""External helper refusal checks; source tests only, no native credit."""
import json,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import verify_portable_checkpoint as helper
from application.cloud.authoring import emit_package
from application.platform.private_files import create_private_directory,write_private_new
from strategy.v02.capabilities import build_capability_snapshot

class PortableHelperRefusals(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory(dir=helper.BASE,prefix='portable-helper-unit-');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/'scope';create_private_directory(self.root)

    def test_archive_admission_hash_and_final_rechecks_are_closed(self):
        revision='1'*40;facts=dict(implementation_hash='sha256:'+'2'*64,executable_revision=revision)
        name='r7-product-0.2.0-windows-'+revision[:7]+'.zip';raw=b'bounded archive fixture'
        value=dict(archive=name,archive_sha256=helper.sha(raw)[7:],identity=facts,
            source=dict(revision=revision,worktree='CLEAN',implementation_hash=facts['implementation_hash']))
        metadata=self.root/'build-result.json';archive=self.root/name
        write_private_new(archive,raw)
        def save(document):metadata.write_text(json.dumps(document),encoding='utf-8')
        save(value)
        self.assertEqual(helper.archive_subject(self.root,revision,facts)[2],raw)
        for bad in ('../elsewhere.zip',str(archive),name+'/extra'):
            save(dict(value,archive=bad))
            with self.subTest(ref=bad),self.assertRaises(ValueError):helper.archive_subject(self.root,revision,facts)
        save(value);archive.write_bytes(b'changed')
        with self.assertRaises(ValueError):helper.archive_subject(self.root,revision,facts)
        archive.write_bytes(raw);save(dict(value,source=dict(value['source'],worktree='DIRTY')))
        with self.assertRaises(ValueError):helper.archive_subject(self.root,revision,facts)

    def test_author_kit_payload_manifest_snapshot_or_response_tamper_denies(self):
        snapshot=build_capability_snapshot();write_private_new(self.root/'capabilities.json',snapshot.canonical_json.encode())
        definition=(helper.ROOT/'docs/strategy/authoring-v0.2/examples/four-hour/strategy.json').read_bytes()
        authored=emit_package(definition,self.root/'engineering-package',submission_id='engineering-source-check')
        exported=dict(status='CAPABILITIES_EXPORTED',snapshot_hash=snapshot.snapshot_hash,execution_evidence='NOT_RUN')
        self.assertIn('engineering-package/manifest.json',helper.validate_authoring(self.root,exported,authored))
        for relative in ('capabilities.json','engineering-package/strategy.json','engineering-package/manifest.json'):
            path=self.root/relative;original=path.read_bytes();path.write_bytes(original+b' ')
            with self.subTest(path=relative),self.assertRaises(Exception):helper.validate_authoring(self.root,exported,authored)
            path.write_bytes(original)
        with self.assertRaises(ValueError):helper.validate_authoring(self.root,dict(exported,status='OTHER'),authored)
        with self.assertRaises(ValueError):helper.validate_authoring(self.root,exported,dict(authored,financial_authority='APPROVED'))

    def test_version_only_replacement_cannot_claim_another_subject(self):
        expected=b'{"financial_authority":"NONE","revision":"actual"}\n'
        write_private_new(self.root/'version.json',expected);helper.require_version(self.root,expected)
        (self.root/'version.json').write_bytes(b'{"financial_authority":"APPROVED","revision":"other"}\n')
        with self.assertRaises(ValueError):helper.require_version(self.root,expected)

if __name__=='__main__':unittest.main(verbosity=2)
