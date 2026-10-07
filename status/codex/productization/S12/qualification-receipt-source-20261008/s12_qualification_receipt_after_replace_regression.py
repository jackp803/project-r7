"""Bounded actual source regressions; not native or qualified release issuance."""
from pathlib import Path
import json,subprocess,sys
from s09_owner_worker_native_regression import OwnedProof,BASE,REPO,sha,stamp
from application.datasets.catalog import read_local
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.qualification import parse_result,revision_fact,_sanitize
from strategy.v02.capabilities import _revision

FILES=['src/storage/qualification.py','src/storage/migrations/0018_product_qualification_receipts.sql',
    'tests/storage/test_qualification_receipts.py']

def main():
    paths=[REPO/name for name in FILES]+[Path(__file__)]
    def capture():return {str(path.relative_to(BASE.parent).as_posix()):sha(read_local(path.parent,path.name,1024**2)) for path in paths}
    captured=capture();implementation=_revision();source=revision_fact(REPO)
    value=dict(passed=False,input_hashes_before=captured,implementation_hash=implementation,source_before=source,commands=[],
        scope='STORAGE_ONLY_SOURCE_REGRESSIONS;NO_NATIVE_PRODUCT_QUALIFICATION_OR_PRODUCER_ISSUANCE',
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        ordinary_native_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE')
    stages=[('storage-all',['discover','-s','tests/storage','-p','test_*.py','-v'],180),
        ('owner-backup',['-v','tests.application.test_local_paper_control_composition','tests.application.test_local_owner_composition',
            'tests.product.test_paper_control_ipc','tests.product.test_api_owner_services','tests.application.test_native_entrypoints',
            'tests.application.test_native_http_contract','tests.application.test_control_process_supervision',
            'tests.application.test_paper_owner_worker','tests.application.test_paper_effect_recovery',
            'tests.application.test_database_backup','tests.application.test_database_restore','tests.application.test_product_data_backup'],300)]
    with OwnedProof(BASE/'S12-qualification-receipts-source-regression-20261008-after-replace.json') as proof:
        for label,arguments,timeout in stages:
            assert capture()==captured and _revision()==implementation and revision_fact(REPO)==source
            owned=None;started=stamp();name=f'S12-qualification-receipts-{label}-20261008-after-replace.log'
            try:
                with OwnedProof(BASE/name) as log:
                    owned=spawn_owned([sys.executable,'-m','unittest',*arguments],cwd=REPO,limits=ResourceLimits(timeout),
                        stdout=log.stream,stderr=subprocess.STDOUT)
                    code=owned.wait();cleanup=terminate_owned(owned,deadline_seconds=5)
                    log.require_owned();log.stream.seek(0);raw=log.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
                    sanitized=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace('\r\n','\n').encode('utf-8')
                    log.stream.seek(0);log.stream.write(sanitized);log.stream.truncate();log.stream.flush();log.require_owned()
                    result=parse_result(sanitized.decode('utf-8'),returncode=code)
                    item=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),argv=[sys.executable,'-m','unittest',*arguments],
                        returncode=code,tests_run=result.tests_run,failures=result.failures,errors=result.errors,skipped=result.skipped,
                        tree_reaped=cleanup.reaped,passed=result.passed and cleanup.reaped,log=name,log_sha256=sha(sanitized))
                value['commands'].append(item);proof.persist(value);print(json.dumps(item),flush=True)
                if not item['passed']:return 1
            finally:
                if owned is not None:assert terminate_owned(owned,deadline_seconds=5).reaped
        value.update(passed=True,input_hashes_after=capture(),source_after=revision_fact(REPO))
        assert value['input_hashes_after']==captured and value['source_after']==source and _revision()==implementation
        proof.persist(value)
    return 0

if __name__=='__main__':raise SystemExit(main())
