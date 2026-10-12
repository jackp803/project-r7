"""Replay the unchanged eleven source browser cases, one owned fixture at a time."""
from pathlib import Path
import json,os,re,subprocess,sys
from s09_normal_fixture_source_qualify import BASE,REPO,inputs
from s09_owner_worker_native_regression import OwnedProof,sha,stamp
from s09_ui_dependency_inputs import protected_bytes,installed_dependencies,cache_inventory,fresh_caches
from s09_forward_ui_bound_qualification import capture_dist,NODE,EDGE
from application.qualification import revision_fact,_sanitize
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from local_windows_qualification_awake import awake_request

def require_prefix_inventory(prefix,expected_helpers):
    if set(prefix['helper_hashes'])!=set(expected_helpers):
        raise ValueError('Exact known prefix helper inventory required')
    expected=[(label,label+'.log') for label in ['contract','typecheck','unit','build','browser']]
    if [(c['label'],c['log']) for c in prefix['commands']]!=expected:
        raise ValueError('Exact known prefix command/log inventory required')

REV=sys.argv[1]
OUTPUT=BASE/('S09-forward-ui-serial-'+REV[:7]+'-literal-bound')
PREFIX=BASE/('S09-forward-ui-bound-'+REV[:7]+'-fresh-cache')
revision_fact(REPO,REV,True)
prefix_raw=protected_bytes(PREFIX/'ui-qualification.json',8*1024**2)
prefix=json.loads(prefix_raw)
prefix_helper_paths=[BASE/'s09_forward_ui_bound_qualification.py',BASE/'s09_ui_dependency_inputs.py',
 BASE/'s09_owner_worker_native_regression.py',BASE/'s09_normal_fixture_source_qualify.py',
 BASE/'local_windows_qualification_awake.py',NODE,EDGE,Path(sys.executable)]
require_prefix_inventory(prefix,{str(path) for path in prefix_helper_paths})
assert not prefix['passed'] and len(prefix['commands'])==5
assert [c['label'] for c in prefix['commands'][:4]]==['contract','typecheck','unit','build']
assert all(c['passed'] and c['tree_reaped'] for c in prefix['commands'][:4])
captured=inputs();assert captured==prefix['source_input_hashes']
dependencies=installed_dependencies();assert dependencies==prefix['installed_dependency_hashes']
for path,digest in prefix['helper_hashes'].items():assert sha(protected_bytes(Path(path)))==digest
for command in prefix['commands'][:4]:assert sha(protected_bytes(PREFIX/command['log'],8*1024**2))==command['log_sha256']
unit_raw=protected_bytes(PREFIX/'unit-results.json',8*1024**2);unit=json.loads(unit_raw)
assert unit['success'] and unit['numTotalTests']==unit['numPassedTests']==18 and unit['numFailedTests']==unit['numPendingTests']==0
dist=capture_dist(REPO/'ui/dist');assert dist==prefix['ui_dist_inventory']
assert not os.path.lexists(OUTPUT);OUTPUT.mkdir()
cache_preparation=fresh_caches(OUTPUT);observed_caches={}
source=protected_bytes(REPO/'ui/qa/control-center.spec.ts',1024**2).decode()
cases=re.findall(r"test\('([^']+)',async\(\{page\}\)=>\{(.*?)(?=\ntest\(|\Z)",source,re.S)
assert len(cases)==11 and len({title for title,body in cases})==11
profiles=['empty','research','paper','protected','temporal','approval','deployment']
groups={profile:[] for profile in profiles}
for title,body in cases:
    found=re.findall(r"await login\(page,'([^']+)'\)",body)
    assert len(found)==1 and found[0] in groups
    groups[found[0]].append(title)
assert all(groups.values())
helper_paths=[Path(__file__),BASE/'s09_ui_dependency_inputs.py',
 BASE/'s09_forward_ui_bound_qualification.py',BASE/'s09_normal_fixture_source_qualify.py',
 BASE/'s09_owner_worker_native_regression.py',BASE/'local_windows_qualification_awake.py',NODE,EDGE,Path(sys.executable)]
helpers={str(path):sha(protected_bytes(path)) for path in helper_paths}
report=dict(passed=False,source_before=revision_fact(REPO,REV,True),source_input_hashes=captured,
 installed_dependency_hashes=dependencies,helper_hashes=helpers,cache_preparation=cache_preparation,
 frontend_prefix_report_sha256=sha(prefix_raw),frontend_prefix_unit_results_sha256=sha(unit_raw),
 frontend_prefix_scope='FOUR_COMPLETED_BOUND_STAGES_ONLY;FAILED_PARALLEL_BROWSER_NOT_CREDITED',
 frontend_commands=prefix['commands'][:4],commands=[],unchanged_cases=groups,ui_dist_inventory=dist,
 scope='SOURCE_UI_ONLY;SERIAL_UNCHANGED_ASSERTIONS;NO_NATIVE_OR_NORMAL_PRODUCT_OR_REAL_FORWARD_CREDIT',
 real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
merged=dict(suites=[],errors=[],stats=dict(expected=0,unexpected=0,skipped=0,flaky=0))
observed_titles=[]
with OwnedProof(OUTPUT/'ui-qualification.json') as proof:
    proof.persist(report)
    with awake_request() as awake:
        for index,profile in enumerate(profiles):
            revision_fact(REPO,REV,True);assert inputs()==captured and capture_dist(REPO/'ui/dist')==dist
            assert cache_inventory()==observed_caches
            group=OUTPUT/profile;group.mkdir()
            module=(REPO/'ui/node_modules/@playwright/test/index.mjs').as_uri()
            settings=dict(testDir=str(REPO/'ui/qa'),testMatch='*.spec.ts',fullyParallel=False,workers=1,
              timeout=25000,expect=dict(timeout=4000),retries=0,outputDir=str(group/'results'),
              reporter=[['line'],['json',dict(outputFile=str(group/'results.json'))]],
              use=dict(browserName='chromium',headless=True,launchOptions=dict(executablePath=str(EDGE)),
                viewport=dict(width=1440,height=960),actionTimeout=8000,trace='off',video='off',screenshot='off'),
              webServer=dict(command=f'"{sys.executable}" -X utf8 qa/serve_fixture.py --profile {profile} --port {8766+index}',
                cwd=str(REPO/'ui'),url=f'http://127.0.0.1:{8766+index}/api/v1/auth/status',
                reuseExistingServer=False,timeout=90000,stdout='ignore',stderr='pipe'))
            config=OUTPUT/(profile+'.config.mjs')
            raw_config=('import {defineConfig} from '+json.dumps(module)+';\nexport default defineConfig('+json.dumps(settings)+');\n').encode()
            with OwnedProof(config) as owner:owner.stream.write(raw_config);owner.stream.flush();owner.require_owned()
            pattern='(?:'+'|'.join(re.escape(title) for title in groups[profile])+')$'
            argv=[str(NODE),str(REPO/'ui/node_modules/@playwright/test/cli.js'),'test','--config',str(config),'--grep',pattern]
            environment=os.environ.copy();environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',
              NO_COLOR='1',R7_BROWSER_ARTIFACT_ROOT=str(group))
            owned=None;started=stamp()
            with OwnedProof(OUTPUT/(profile+'.log')) as log:
                try:
                    owned=spawn_owned(argv,cwd=REPO/'ui',limits=ResourceLimits(300),stdout=log.stream,
                      stderr=subprocess.STDOUT,env=environment);code=owned.wait()
                finally:cleanup=None if owned is None else terminate_owned(owned,deadline_seconds=5)
                assert cleanup is not None and cleanup.reaped
                log.require_owned();log.stream.seek(0);raw_log=log.stream.read(8*1024**2+1);assert len(raw_log)<=8*1024**2
                published=_sanitize(raw_log.decode('utf-8',errors='replace'),REPO).replace('\r\n','\n').encode()
                log.stream.seek(0);log.stream.write(published);log.stream.truncate();log.stream.flush();log.require_owned()
            observed_caches=cache_inventory()
            result=dict(profile=profile,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,
              tree_reaped=True,log=profile+'.log',log_sha256=sha(published),
              config_sha256=sha(raw_config),derived_cache_inventory_after=observed_caches)
            report['commands'].append(result);proof.persist(report);print(json.dumps(result),flush=True)
            assert code==0 and protected_bytes(config)==raw_config
            raw_results=protected_bytes(group/'results.json',8*1024**2);actual=json.loads(raw_results)
            stats=actual['stats'];assert stats['expected']==len(groups[profile]) and stats['unexpected']==stats['skipped']==stats['flaky']==0 and not actual.get('errors')
            def titles(suites):
                for suite in suites:
                    for spec in suite.get('specs',[]):yield spec['title']
                    yield from titles(suite.get('suites',[]))
            names=list(titles(actual['suites']));assert sorted(names)==sorted(groups[profile]);observed_titles.extend(names)
            result.update(tests=stats['expected'],results_sha256=sha(raw_results))
            merged['suites'].extend(actual['suites'])
            for key in merged['stats']:merged['stats'][key]+=stats[key]
            for path in group.glob('*.png'):
                pixels=protected_bytes(path,8*1024**2)
                with OwnedProof(OUTPUT/path.name) as owner:owner.stream.write(pixels);owner.stream.flush();owner.require_owned()
            assert inputs()==captured and capture_dist(REPO/'ui/dist')==dist
            proof.persist(report)
    assert awake['restored'] and sorted(observed_titles)==sorted(title for title,body in cases)
    assert installed_dependencies()==dependencies and cache_inventory()==observed_caches
    for path,digest in helpers.items():assert sha(protected_bytes(Path(path)))==digest
    merged_raw=(json.dumps(merged,indent=2)+'\n').encode()
    with OwnedProof(OUTPUT/'browser-results.json') as owner:owner.stream.write(merged_raw);owner.stream.flush();owner.require_owned()
    assert inputs()==captured and capture_dist(REPO/'ui/dist')==dist
    report.update(passed=True,source_after=revision_fact(REPO,REV,True),inputs_unchanged=True,
      unit_tests=18,browser_tests=11,unit_failures=0,unit_skipped=0,browser_failures=0,browser_skipped=0,browser_flaky=0,
      browser_results_sha256=sha(merged_raw),awake_request=awake)
    proof.persist(report)
print(json.dumps(dict(passed=True,frontend_commands=4,serial_browser_commands=7,unit_tests=18,browser_tests=11)))
