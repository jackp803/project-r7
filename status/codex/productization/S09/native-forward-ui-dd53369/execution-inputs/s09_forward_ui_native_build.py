"""Build exact-clean UI candidate; retain inherited Python and current UI scopes."""
from pathlib import Path
import json,os,subprocess,sys
from s09_normal_fixture_source_qualify import BASE,REPO,inputs
from s09_owner_worker_native_regression import PROJECT,OwnedProof,sha,stamp,capture_qualification
from s09_ui_dependency_inputs import protected_bytes,installed_dependencies,cache_inventory
from s09_forward_ui_bound_qualification import capture_dist,NODE,EDGE
from application.qualification import revision_fact,_sanitize
from application.platform.distribution import verify_distribution
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from strategy.v02.capabilities import _revision
from local_windows_qualification_awake import awake_request

REV=sys.argv[1];OLD='d3d849642f278ccd39723355367bf1030d8f0619'
UIREV='9a48e09f877b46d5e6f0971cf6a47df8c0485859'
OUTPUT=BASE/('r7-native-windows-S09-forward-ui-'+REV[:7])
PROOF=BASE/('S09-forward-ui-'+REV[:7]+'-native-build.json')
BUILD_PYTHON=PROJECT/'toolchains/py312-native-build/Scripts/python.exe'
ui_folder=BASE/'S09-forward-ui-serial-9a48e09-literal-bound'
ui_raw=protected_bytes(ui_folder/'ui-qualification.json',8*1024**2);ui=json.loads(ui_raw)
revision_fact(REPO,REV,True)
public=json.loads(protected_bytes(REPO/'status/codex/productization/S09/forward-ui-9a48e09-py312/disposition.json',8*1024**2))
assert sha(ui_raw)==public['raw_result_hashes']['serial_report']
assert ui['passed'] and ui['unit_tests']==18 and ui['browser_tests']==11 and ui['awake_request']['restored']
assert ui['source_before']==ui['source_after']==dict(revision=UIREV,worktree='CLEAN')
captured=inputs();assert captured==ui['source_input_hashes'] and len(captured)==636
dependencies=installed_dependencies();assert dependencies==ui['installed_dependency_hashes']
caches=cache_inventory();assert caches==ui['commands'][-1]['derived_cache_inventory_after']
dist=capture_dist(REPO/'ui/dist');assert dist==ui['ui_dist_inventory']
qualified=BASE/'r7-productization-S09-normal-fixture-qualified-d3d8496'
report,context,old_hashes=capture_qualification(qualified,OLD)
assert report['tests_run']==2101 and _revision()==context['implementation_hash']
baseline_manifest=json.loads(protected_bytes(REPO/'status/codex/productization/S09/normal-fixture-qualified-artifact-hashes-d3d8496.json',8*1024**2))
for path,digest in old_hashes.items():
    records=[item for item in baseline_manifest['files'] if item['source']==path.relative_to(BASE).as_posix()]
    assert len(records)==1 and records[0]['original_sha256']==digest
delta=sorted(name for name,value in captured.items() if context['source_input_hashes'].get(name)!=value)
assert delta==['ui/qa/control-center.spec.ts','ui/src/App.tsx','ui/src/model.test.ts','ui/src/model.ts']
paths=[Path(__file__),BASE/'s09_owner_worker_native_regression.py',BASE/'s09_normal_fixture_source_qualify.py',
 BASE/'s09_ui_dependency_inputs.py',BASE/'s09_forward_ui_bound_qualification.py',BASE/'local_windows_qualification_awake.py',
 REPO/'tools/build_product.py',BUILD_PYTHON,Path(sys.executable),NODE,EDGE,
 ui_folder/'ui-qualification.json',qualified/'qualification.json',qualified/'qualification-context.json']
hashes={str(path):sha(protected_bytes(path)) for path in paths}
assert not os.path.lexists(OUTPUT) and not os.path.lexists(PROOF)
value=dict(passed=False,executable_revision=REV,source_before=revision_fact(REPO,REV,True),
 source_input_hashes=captured,helper_hashes=hashes,installed_node_dependencies=dependencies,
 ui_dist_inventory=dist,python_implementation_hash=context['implementation_hash'],
 inherited_python_full_qualification_revision=OLD,inherited_python_execution_instances=2101,
 current_ui_qualification_revision=UIREV,current_ui_unit_tests=18,current_ui_browser_tests=11,
 source_input_delta_from_python_baseline=delta,commands=[],native_acceptance='NOT_RUN',
 scope='EXACT_CLEAN_NATIVE_BUILD;UNCHANGED_QUALIFIED_PYTHON_PLUS_CURRENT_UI_BYTES;NOT_NEW_FULL_PYTHON_RUN_OR_NATIVE_FLOW_ACCEPTANCE',
 provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
argv=[str(BUILD_PYTHON),str(REPO/'tools/build_product.py'),'--output',str(OUTPUT),'--expected-revision',REV]
owned=None
with OwnedProof(PROOF) as proof:
    proof.persist(value)
    with awake_request() as awake:
        with OwnedProof(BASE/('S09-forward-ui-'+REV[:7]+'-native-build.log')) as log:
            started=stamp()
            try:
                owned=spawn_owned(argv,cwd=REPO,limits=ResourceLimits(1200),stdout=log.stream,stderr=subprocess.STDOUT,
                  env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
                code=owned.wait()
            finally:cleanup=None if owned is None else terminate_owned(owned,deadline_seconds=5)
            assert cleanup is not None and cleanup.reaped
            log.require_owned();log.stream.seek(0);raw=log.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
            out=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
            log.stream.seek(0);log.stream.write(out);log.stream.truncate();log.stream.flush();log.require_owned()
        value['commands'].append(dict(label='build',exit_code=code,tree_reaped=True,started_at_utc=started,
          finished_at_utc=stamp(),log='S09-forward-ui-'+REV[:7]+'-native-build.log',log_sha256=sha(out)))
        proof.persist(value)
        assert code==0
        identity=verify_distribution(OUTPUT/'dist/R7')
        assert identity['executable_revision']==REV and identity['implementation_hash']==context['implementation_hash']
        built=json.loads(protected_bytes(OUTPUT/'build-result.json',8*1024**2))
        archive=OUTPUT/('r7-product-0.2.0-windows-'+REV[:7]+'.zip')
        assert sha(protected_bytes(archive,512*1024**2))=='sha256:'+built['archive_sha256']
    assert awake['restored'] and inputs()==captured and installed_dependencies()==dependencies
    assert cache_inventory()==caches and capture_dist(REPO/'ui/dist')==dist
    for path,digest in hashes.items():assert sha(protected_bytes(Path(path)))==digest
    value.update(passed=True,source_after=revision_fact(REPO,REV,True),native_build_identity=identity,
      archive_sha256='sha256:'+built['archive_sha256'],archive_name=archive.name,awake_request=awake)
    proof.persist(value)
print(json.dumps(dict(passed=True,identity=identity,archive=archive.name,native_acceptance='NOT_RUN')),flush=True)
