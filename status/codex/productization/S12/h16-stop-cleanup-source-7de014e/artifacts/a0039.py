"""Retain actual failed joined source run; never transfer PASS credit."""
from pathlib import Path
import ast,hashlib,json,re,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
REV=sys.argv[1]
revision_fact(ROOT,REV,True)
if REV!='7de014eeedf2791c8e186a9608c589454c792f4c':raise ValueError('Exact failed subject required')
prefix='h16-stop-cleanup-source-'+REV[:7]
# Extract only literal planned reference declarations, never execute planned PASS retainer.
tree=ast.parse((BASE/'retain_h16_stop_cleanup_source.py').read_text(encoding='utf-8'))
refs=[]
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='refs' for t in node.targets):
        refs=[prefix+'/checkpoint.json',prefix+'/source.log']+ast.literal_eval(ast.List(elts=node.value.elts[2:],ctx=ast.Load()))
    elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call):
        c=node.value
        if isinstance(c.func,ast.Attribute) and isinstance(c.func.value,ast.Name) and c.func.value.id=='refs':
            if c.func.attr=='extend':refs.extend(ast.literal_eval(c.args[0]))
            elif c.func.attr=='append':refs.append(ast.literal_eval(c.args[0]))
refs.extend(['h16-stop-cleanup-memory-failure-audit-20261020.json',
 'partition_h16_cleanup_tests.py.reviewed-pass-only.unapplied',
 'h16-cleanup-partition-script-review-initial-20261020.json',
 'h16-cleanup-partition-script-review-final-20261020.json',
 'h16-cleanup-partition-script-memory-review-initial-20261020.json',
 'h16-cleanup-partition-script-memory-review-final-20261020.json',
 'retain_h16_stop_cleanup_failure.py'])
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    value=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in value.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run_raw=prepared[0][1];log=prepared[1][1]
if digest(run_raw)!='sha256:342763ac9b99bb94124bb72bb40eac7a1e49ed5c3189ad278ae43a23a2a09b1c':raise ValueError('Exact checkpoint required')
if digest(log)!='sha256:c6be7807600527ca1a2db41fbc67422c18532d3211783c8c85b69cc3d0145737':raise ValueError('Exact failed log required')
run=json.loads(run_raw)
if not (run['executable_revision']==REV and run['passed'] is False and run['tests_run']==158 and len(run['modules'])==16 and run['source_unchanged'] and run['tree_reaped'] and run['exit_code']==1):raise ValueError('Wrong completed failed subject')
review_bytes=(BASE/'h16-stop-cleanup-owner-review-final-retry01.json').read_bytes()
if digest(review_bytes)!='sha256:c00e4267598d2d9a9a0284d39116d5af7379c0a0d255cc973799b3bc2fcb9ba7':raise ValueError('Exact review required')
for ref,wanted in json.loads(review_bytes)['subject_hashes'].items():
    if hashlib.sha256((ROOT/ref).read_bytes()).hexdigest()!=wanted:raise ValueError('Source changed')
out=ROOT/'status/codex/productization/S12'/prefix
create_private_directory(out);art=out/'artifacts';create_private_directory(art);items=[]
for number,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{number:04d}'+Path(ref).suffix);write_private_new(target,safe)
    items.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),retained_hash=digest(safe)))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
 implementation_hash=run['implementation_hash'],scope=run['scope'],status='FAILED_RESOURCE_ADMISSION_NOT_QUALIFIED',
 tests_run=158,passed_cases=66,errors=92,failures=0,skips=0,cleanup_cases_passed=11,
 source_unchanged=True,tree_reaped=True,started_at=run['started_at'],finished_at=run['finished_at'],
 error='All92 actual error blocks are RESEARCH_MEMORY_PRESSURE. Memory below existing5060439859byte floor; no threshold change or user process closure.',
 cleanup='Genuine FILLED entry/protection/close/partial/same-native-position zero followed by one exact owned-stop cleanup claim. ACK/lost ACK do not prove terminality. Original reconcile observes terminal stop. Successor E6lease2 preserves E7release1; no repeat cancel. All11 passed in this failed joined run.',
 freshness='Prior actual expiry RED exposed4.9to5.1second final guard gap. Minimal final issuer/window/proof check preserves5seconds and leaves unresolved durable claim with zero cancel. Focused2 passed before this run; static0C0I executionNONE.',
 coverage_gap='AlternatePK REPLACE fixture has nonexistent-FK mask. SQL native-unique guard has no observed defect; strengthen to real originalENTRY claim and isolated mutation oracle. No independent native-unique test credit.',
 timing_gap='Observed9cases1864.525s exceeds existing900s perfile qualification limit. Partition same11 into6bounded files/non-TestCase mixin without gate increase or lost cases; future timing pending. No actual PQR failure claimed.',
 H01='Bounded static265file review0C1I: formal E2-driven TradingService runner absent. Existing Paper separate. Original MasterM9/TRADE01 already require integration; continue local Fake work.',
 next='Partition all11 and validFK oracle, genuine E5 funded TradeResult/CLOSED with durable replay and K05positive, F04/I04/J03/H01/portable/audits/clause binding. Final inventory/examples/full/native remain required.',
 preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',native_full='NOT_RUN_FOR_THIS_SOURCE',
 H16='INCOMPLETE_FINALIZATION_PENDING',K05='INCOMPLETE_GENUINE_CLOSED_DISPATCH_PENDING',master='IN_PROGRESS',
 actual_production_cleanup='UNSUPPORTED_NOT_CALLED',actual_production_funding='UNSUPPORTED_NOT_CALLED',
 public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,
 credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained mismatch')
evidence=(out/'disposition.json').relative_to(ROOT).as_posix()
p=ROOT/'coordination/CODEX/PROGRESS.json';v=json.loads(p.read_bytes())
v.update(executable_revision=REV,candidate_executable_revision=REV,active_step='H16_CLEANUP11_PASS_JOINED158_RESOURCE_FAILED_CONTINUE_LOCAL',next_step=doc['next'])
v['h16_owned_stop_cleanup_checkpoint']=dict(executable_revision=REV,status=doc['status'],tests_run=158,passed_cases=66,errors=92,cleanup_cases_passed=11,evidence_ref=evidence)
v['h01_formal_trading_runner_gap']=dict(status='IMPORTANT_UNFINISHED_LOCAL_INTEGRATION',reviewed_revision=REV,evidence_ref=evidence,live='NOT_STARTED')
p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=f'''# H16 cleanup checkpoint — 2026-10-20

Exact `{REV}` source158/16modules FAILED:66pass,92errors,0failures/skip;
all92errors are actual RESEARCH_MEMORY_PRESSURE; source unchanged/tree reaped.
All11cleanup scenarios passed. No joined-regression/PQR/native PASS credit.
Evidence: `{evidence}`.

Actual original entry/protection/close/flat and exact owned-stop cleanup,
durable claim, lostACK/successor no-repeat and current-read fences passed.
Prior expiry RED/focused2PASS retained; existing5second window unchanged.
Later static finding: alternatePK native-unique fixture has missing-FK mask;
strengthen with real claimedENTRY and isolated mutation oracle. No SQL defect
observed. Original9cases1864.525s exceed existing900s perfile limit; partition
all11 into6files/non-TestCase helper without raising deadline or losing cases.
H16/K05 funded CLOSED/TradeResult/replay positive remain unfinished.
H01 static0C1I: formal E2-driven TradingService runner absent; originalM9/
TRADE01 require it. Normal Paper separate and supported. Continue local work
during memory pressure. No repeat full run until actual resources adequate.
Preserve qualified Windows7d821f2; final inventory/examples/full/native still
required for settled source. F04/I04/J03/portable/audits/clause binding pending.
OldPC/Ubuntu/cloud/policies/realforward external or unselected; no wait for
independent local work. Master IN_PROGRESS; original task/branch preserved.
Public8/responses8/additional0/private0; credentialsNONE/capitalNONE/LIVE
notstarted/GitHub compute notused.

'''
for relative in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    p=ROOT/relative;p.write_text(note+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=evidence,status=doc['status'])))
