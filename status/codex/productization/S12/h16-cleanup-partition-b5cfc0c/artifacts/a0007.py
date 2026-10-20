"""One real migrated disposable DB, normal then isolated trigger mutation."""
from pathlib import Path
import hashlib,json,sys,unittest
from unittest.mock import patch
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from strategy.v02.capabilities import _revision
from application.qualification import _sanitize
from tests.storage.test_stop_cleanup_constraints import StopCleanupConstraintTests
before=_revision()
results={};original=StopCleanupConstraintTests.claim_fixture
def mutated(self):
    db,row=original(self)
    sql=db.execute("SELECT sql FROM sqlite_master WHERE type='trigger' AND name='product_dispatch_stop_cleanup_claims_no_replace'").fetchone()[0]
    line=' OR EXISTS(SELECT 1 FROM product_dispatch_stop_cleanup_claims WHERE provider_ref=NEW.provider_ref AND account_ref=NEW.account_ref AND native_algo_id=NEW.native_algo_id)'
    if sql.count(line)!=1:raise ValueError('Exact isolated native-unique trigger branch required')
    db.execute('DROP TRIGGER product_dispatch_stop_cleanup_claims_no_replace')
    db.execute(sql.replace(line,''));db.commit()
    return db,row
for name,mutation in [('normal',False),('missing-native-trigger-branch',True)]:
    path=BASE/('h16-cleanup-constraint-'+name+'.log')
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(StopCleanupConstraintTests)
        if mutation:
            with patch.object(StopCleanupConstraintTests,'claim_fixture',mutated):
                result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        else:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    raw=path.read_text(encoding='utf-8');safe=_sanitize(raw,ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    path.write_text(safe,encoding='utf-8',newline='\n')
    results[name]=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        log_hash='sha256:'+hashlib.sha256(path.read_bytes()).hexdigest())
    if mutation and not (result.testsRun==1 and len(result.failures)==1 and not result.errors and
            'IntegrityError not raised' in raw):raise ValueError('Mutation must expose exact independent native guard oracle')
    if not mutation and not (result.testsRun==1 and result.wasSuccessful() and not result.skipped):raise ValueError('Normal guard failed')
if _revision()!=before:raise ValueError('Source changed')
report=dict(status='SCHEMA_ONLY_NORMAL_PASS_MUTANT_FAILS_EXPECTED',implementation_hash=before,source_unchanged=True,
    mutation='Only native-unique OR branch removed from trigger in disposable migrated testDB, PK branch/UNIQUE/FKs/recursiveOFF preserved. No production source or product DB mutation.',
    owner_flow_credit='NONE_THIS_SCHEMA_PROOF',private_requests=0,public_requests=0,results=results)
(BASE/'h16-cleanup-constraint-oracle.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(report))
