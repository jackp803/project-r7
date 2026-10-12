"""Build exact-clean intake repair with fresh full source and unchanged UI proof."""
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

REV=sys.argv[1]
OUTPUT=BASE/('r7-native-windows-S15-negative-intake-'+REV[:7])
PROOF=BASE/('S15-negative-intake-'+REV[:7]+'-native-build.json')
BUILD_PYTHON=PROJECT/'toolchains/py312-native-build/Scripts/python.exe'
qualified=BASE/('r7-productization-S09-normal-fixture-qualified-'+REV[:7])
report,context,qual_hashes=capture_qualification(qualified,REV)
captured=inputs();assert len(captured)==637 and captured==context['source_input_hashes']
assert _revision()==context['implementation_hash']
ui_folder=BASE/'S09-forward-ui-serial-9a48e09-literal-bound'
ui_raw=protected_bytes(ui_folder/'ui-qualification.json',8*1024**2);ui=json.loads(ui_raw)
public=json.loads(protected_bytes(REPO/'status/codex/productization/S09/forward-ui-9a48e09-py312/disposition.json',8*1024**2))
assert sha(ui_raw)==public['raw_result_hashes']['serial_report'] and ui['passed']
delta=sorted(name for name,value in captured.items() if ui['source_input_hashes'].get(name)!=value)
assert delta==['src/application/control_api/owner_services.py','src/application/intake/ledger.py',
    'src/application/intake/service.py','src/application/platform/supervision.py',
    'tests/application/test_process_supervision.py','tests/application/test_submission_validity_intake.py']
dependencies=installed_dependencies();assert dependencies==ui['installed_dependency_hashes']
caches=cache_inventory();assert caches==ui['commands'][-1]['derived_cache_inventory_after']
dist=capture_dist(REPO/'ui/dist');assert dist==ui['ui_dist_inventory']
paths=[Path(__file__),BASE/'s09_owner_worker_native_regression.py',BASE/'s09_normal_fixture_source_qualify.py',
    BASE/'s09_ui_dependency_inputs.py',BASE/'s09_forward_ui_bound_qualification.py',BASE/'local_windows_qualification_awake.py',
    REPO/'tools/build_product.py',BUILD_PYTHON,Path(sys.executable),NODE,EDGE,ui_folder/'ui-qualification.json',*qual_hashes]
hashes={str(path):sha(protected_bytes(path)) for path in paths}
assert not os.path.lexists(OUTPUT) and not os.path.lexists(PROOF)
value=dict(passed=False,executable_revision=REV,source_before=revision_fact(REPO,REV,True),source_input_hashes=captured,
    helper_hashes=hashes,full_source_qualification_revision=REV,full_source_execution_instances=report['tests_run'],
    source_qualification_hashes={str(path):value for path,value in qual_hashes.items()},
    current_ui_qualification_revision='9a48e09f877b46d5e6f0971cf6a47df8c0485859',current_ui_unit_tests=18,current_ui_browser_tests=11,
    source_input_delta_from_ui_baseline=delta,installed_node_dependencies=dependencies,ui_dist_inventory=dist,
    python_implementation_hash=context['implementation_hash'],commands=[],native_acceptance='NOT_RUN',
    scope='EXACT_CLEAN_NATIVE_BUILD_WITH_FRESH_FULL_SOURCE;UNCHANGED_UI_PROOF;NO_NATIVE_FLOW_OR_WHOLE_MASTER_CREDIT',
    provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
owned=None
with OwnedProof(PROOF) as proof:
    proof.persist(value)
    with awake_request() as awake:
        with OwnedProof(BASE/('S15-negative-intake-'+REV[:7]+'-native-build.log')) as log:
            started=stamp()
            try:
                owned=spawn_owned([str(BUILD_PYTHON),str(REPO/'tools/build_product.py'),'--output',str(OUTPUT),'--expected-revision',REV],
                    cwd=REPO,limits=ResourceLimits(1200),stdout=log.stream,stderr=subprocess.STDOUT,
                    env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
                code=owned.wait()
            finally:cleanup=None if owned is None else terminate_owned(owned,deadline_seconds=5)
            assert cleanup is not None and cleanup.reaped
            log.require_owned();log.stream.seek(0);raw=log.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
            out=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
            log.stream.seek(0);log.stream.write(out);log.stream.truncate();log.stream.flush();log.require_owned()
        value['commands'].append(dict(label='build',exit_code=code,tree_reaped=True,started_at_utc=started,
            finished_at_utc=stamp(),log='S15-negative-intake-'+REV[:7]+'-native-build.log',log_sha256=sha(out)))
        proof.persist(value);assert code==0
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
