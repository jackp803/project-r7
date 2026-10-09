"""Actual continuation caller rejects malformed public proof before reference I/O."""
import copy,io,json,runpy,sys,unittest
from pathlib import Path
from unittest.mock import patch
from s09_owner_worker_native_regression import OwnedProof,BASE,REPO,sha
from application.qualification import _sanitize
REVISION='af01b45f980882e64f3c83784d0a4da0731728ba'
original_path=BASE/'S09-public-research-setup-af01b45-native-regression.json'
original=json.loads(original_path.read_bytes())

class UnexpectedReferenceRead(RuntimeError):pass

class ReferenceGuards(unittest.TestCase):
    def check(self,mutate):
        value=copy.deepcopy(original);mutate(value)
        fn=module['main'];reads=[]
        def read(path,limit):
            reads.append(path)
            if path==original_path:return json.dumps(value).encode()
            raise UnexpectedReferenceRead('Report reference traversed before exact-set validation')
        with patch.dict(fn.__globals__,read_input=read,revision_fact=lambda *_:None),patch.object(sys,'argv',['guard',REVISION]):
            with self.assertRaises(AssertionError):fn()
        self.assertEqual(reads,[original_path])
    def test_escaping_extra_reference_is_rejected_before_read(self):
        self.check(lambda value:value['input_hashes_before'].update({'../outside-public-scope':'sha256:'+'a'*64}))
    def test_partial_input_set_is_rejected_before_read(self):
        self.check(lambda value:value.update(input_hashes_before={}))
    def test_explicit_recorded_drift_is_rejected_before_read(self):
        def mutate(value):
            value['input_hashes_after']=dict(value['input_hashes_before'])
            value['input_hashes_after'][next(iter(value['input_hashes_after']))]='sha256:'+'0'*64
        self.check(mutate)

if __name__=='__main__':
    label=sys.argv[1];assert label in ('RED','GREEN')
    path=BASE/('s09_native_long_backup_continuation.original-before-guard-remediation.py' if label=='RED' else 's09_native_long_backup_continuation.py')
    module=runpy.run_path(str(path));before=sha(path.read_bytes());capture=io.StringIO()
    result=unittest.TextTestRunner(stream=capture,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReferenceGuards))
    text=_sanitize(capture.getvalue(),REPO);assert before==sha(path.read_bytes())
    prefix=BASE/('S09-native-reference-guards-bound-'+label)
    with OwnedProof(prefix.with_suffix('.log')) as proof:
        proof.stream.write(text.encode());proof.stream.flush();proof.require_owned()
    with OwnedProof(prefix.with_suffix('.json')) as proof:proof.persist(dict(label=label,tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),passed=result.wasSuccessful(),
        tested_caller=path.name,tested_caller_sha256=before,test_sha256=sha(Path(__file__).read_bytes()),
        log_sha256=sha(prefix.with_suffix('.log').read_bytes()),scope='EXTERNAL_REFERENCE_BINDING_GUARDS_ONLY;NO_PRODUCT_TEST_CREDIT'))
    print(text,flush=True);raise SystemExit(0 if result.wasSuccessful() else 1)
