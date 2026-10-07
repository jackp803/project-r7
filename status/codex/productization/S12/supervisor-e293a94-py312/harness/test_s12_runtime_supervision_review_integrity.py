import ast,hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock
import s12_runtime_supervision_review_integrity as integrity
from s12_runtime_supervision_review_integrity import validate_review_inventory,validate_primary_proof


class ReviewRetentionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='R7 retention guard ')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.input=self.root/'source.py';self.input.write_text('OWNED = 1\n',encoding='utf-8')
        self.sha='sha256:'+hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.review=dict(kind='EXPECTED',reviewer='/root/qualification_review',reviewer_execution='NONE',
            remaining_critical=0,remaining_important=0,reviewed_files={'source':self.sha})

    def review_validate(self,review):
        validate_review_inventory(review,kind='EXPECTED',files={'source':self.input},bound={},project=self.root)

    def test_exact_nonempty_current_review_inventory_is_accepted(self):
        self.review_validate(self.review)

    def test_empty_partial_or_unknown_review_inventory_is_denied(self):
        for inventory in ({},{'other':self.sha},{'source':self.sha,'other':self.sha}):
            with self.subTest(inventory=inventory),self.assertRaises(ValueError):
                self.review_validate(dict(self.review,reviewed_files=inventory))

    def test_changed_current_reviewed_file_is_denied(self):
        self.input.write_text('UNREVIEWED = 2\n',encoding='utf-8')
        with self.assertRaises(ValueError):self.review_validate(self.review)

    def proof(self,log='Ran 2 tests in 0.001s\n\nOK\n'):
        (self.root/'proof.log').write_text(log,encoding='utf-8')
        sha='sha256:'+hashlib.sha256((self.root/'proof.log').read_bytes()).hexdigest()
        proof=dict(passed=True,tree_reaped=True,harness_binding='BEFORE_AND_AFTER_EXECUTION',
            exit_code=0,tests_run=2,failures=0,errors=0,skipped=0,log_sha256=sha,
            before={'source':self.sha},after={'source':self.sha})
        (self.root/'proof.json').write_text(json.dumps(proof),encoding='utf-8')
        return proof

    def proof_validate(self):
        return validate_primary_proof(self.root,'proof',2,inputs={'source':self.input},
            input_fields=('before','after'),bound={},project=self.root)

    def test_primary_log_bytes_counts_and_input_binding_are_required(self):
        self.proof();self.proof_validate()
        (self.root/'proof.log').write_text('Ran 2 tests in 0.001s\n\nFAILED (failures=1)\n',encoding='utf-8')
        with self.assertRaises(ValueError):self.proof_validate()

    def test_unexecuted_or_different_count_log_cannot_support_pass_sidecar(self):
        for text in ('NO_EXECUTION\n','Ran 1 test in 0.001s\n\nOK\n','Ran 2 tests in 0.001s\n\nFAILED (errors=1)\n'):
            with self.subTest(text=text):
                self.proof(text)
                with self.assertRaises(ValueError):self.proof_validate()

    def test_missing_changed_or_extra_primary_input_binding_is_denied(self):
        for mapping in ({},{'source':'sha256:'+'0'*64},{'source':self.sha,'other':self.sha}):
            with self.subTest(mapping=mapping):
                proof=self.proof();proof.update(before=mapping,after=mapping)
                (self.root/'proof.json').write_text(json.dumps(proof),encoding='utf-8')
                with self.assertRaises(ValueError):self.proof_validate()

    def test_failed_log_replaced_after_verification_cannot_support_pass(self):
        self.proof('Ran 2 tests in 0.001s\n\nFAILED (errors=1)\n')
        log=self.root/'proof.log';original=log.read_bytes();real_bind=integrity._bind
        def replace_after_verification(path,*args):
            real_bind(path,*args)
            if Path(path)==log:
                log.write_text('Ran 2 tests in 0.001s\n\nOK\n',encoding='utf-8')
        try:
            with mock.patch.object(integrity,'_bind',side_effect=replace_after_verification):
                with self.assertRaises(ValueError):self.proof_validate()
        finally:
            log.write_bytes(original)

    def test_retention_runner_binds_complete_external_import_closure(self):
        base=Path(__file__).parent
        runner=base/'run_s12_runtime_supervision_review_integrity.py'
        tree=ast.parse(runner.read_bytes())
        node=next(node.value for node in tree.body if isinstance(node,ast.Assign)
            and any(isinstance(target,ast.Name) and target.id=='names' for target in node.targets))
        names={value.value for value in node.elts if isinstance(value,ast.Constant) and isinstance(value.value,str)}
        names.add(runner.name)
        required=set()
        for name in names:
            for imported in ast.walk(ast.parse((base/name).read_bytes())):
                if isinstance(imported,ast.ImportFrom) and imported.module and imported.module.startswith(('s12_','s13_','s14_')):
                    required.add(imported.module+'.py')
        self.assertFalse(required-names,required-names)
