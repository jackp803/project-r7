"""Build changed source and verify affected native historical PAPER publication.

This does not invoke the new worker or claim ordinary native PAPER composition.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, stat, subprocess, sys

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parent
REPO=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.qualification import revision_fact, _sanitize
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.distribution import verify_distribution
from application.platform.supervision import _local_path
from application.datasets.catalog import read_local

def sha(raw): return 'sha256:'+hashlib.sha256(raw).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def capture_qualification(folder,revision):
    paths=[folder/'qualification.json',folder/'qualification-context.json']
    raw={path:read_local(path.parent,path.name,8*1024**2) for path in paths}
    report,context=(json.loads(raw[path]) for path in paths)
    assert report['passed'] is True and len(report['commands'])==33 and context['inputs_unchanged'] is True
    assert report['source_before']==report['source_after']==dict(revision=revision,worktree='CLEAN')
    return report,context,{path:sha(value) for path,value in raw.items()}

class OwnedProof:
    def __init__(self,path): self.path=Path(path);self.stream=None
    def __enter__(self):
        _local_path(self.path)
        self.stream=self.path.open('x+b')
        return self
    def require_owned(self):
        _local_path(self.path)
        current=self.path.lstat();owned=os.fstat(self.stream.fileno())
        if not stat.S_ISREG(current.st_mode) or current.st_nlink!=1 or not os.path.samestat(current,owned):
            raise ValueError('Original unlinked proof ownership required')
    def persist(self,value):
        self.require_owned()
        raw=(json.dumps(value,indent=2)+'\n').encode('utf-8')
        self.stream.seek(0);self.stream.write(raw);self.stream.truncate()
        self.stream.flush();os.fsync(self.stream.fileno())
        self.require_owned()
        self.stream.seek(0)
        if self.stream.read(8*1024**2+1)!=raw:
            raise ValueError('Published proof differs from owned bytes')
        self.require_owned()
    def __exit__(self,*_):
        if self.stream is not None:self.stream.close()

def main():
    revision='9bf85349a81486297dbfb3e452f84f67421230d5'
    short=revision[:7]
    qualification=BASE/f'r7-productization-S09-owner-worker-qualified-{short}'
    report,context,qualification_hashes=capture_qualification(qualification,revision)
    output=BASE/f'r7-native-windows-S09-owner-worker-{short}'
    package=output/'dist/R7'
    proof=BASE/f'S09-owner-worker-{short}-native-regression.json'
    assert not os.path.lexists(proof) and not os.path.lexists(output)
    paths=[Path(__file__),REPO/'tools/build_product.py',REPO/'tools/verify_native_product.py',
        BASE/'s14_feedback_cli_native_paper.py',BASE/'S14LocalFakeRclone.exe',BASE/'S14LocalFakeRclone.cs',
        qualification/'qualification.json',qualification/'qualification-context.json',
        BASE/'s09_owner_worker_source_qualify.py',BASE/'test_s09_native_wrapper_guards.py']
    def hashes(): return {path.relative_to(PROJECT).as_posix():sha(read_local(path.parent,path.name,64*1024**2)) for path in paths}
    captured={path.relative_to(PROJECT).as_posix():expected for path,expected in qualification_hashes.items()}
    for path in paths:
        if path not in qualification_hashes:
            captured[path.relative_to(PROJECT).as_posix()]=sha(read_local(path.parent,path.name,64*1024**2))
    assert captured[(BASE/'s09_owner_worker_source_qualify.py').relative_to(PROJECT).as_posix()]==context['launcher_sha256']
    identity=None
    value=dict(executable_revision=revision,source_qualification='PASS',input_hashes_before=captured,
        commands=[],passed=False,scope='CHANGED_SOURCE_BUILD_SMOKE_AND_HISTORICAL_PAPER_PUBLICATION_ONLY',
        native_worker_invoked=False,ordinary_native_paper='NOT_RUN',production_qualified_release_profile='PROPOSED_NOT_ACTIVE',
        real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',ubuntu='NOT_RUN')
    stages=[('build',[str(PROJECT/'toolchains/py312-native-build/Scripts/python.exe'),str(REPO/'tools/build_product.py'),
        '--output',str(output),'--expected-revision',revision],1000),
        ('smoke',[sys.executable,str(REPO/'tools/verify_native_product.py'),'--package',str(package),
            '--output',str(BASE/f'r7-native-S09-owner-worker-smoke-{short}')],600),
        ('historical-paper',[sys.executable,str(BASE/'s14_feedback_cli_native_paper.py'),str(package),
            str(BASE/'S14LocalFakeRclone.exe'),str(BASE/f'r7-native-S09-owner-worker-historical-{short}')],600)]
    with OwnedProof(proof) as proof_owner:
        for label,argv,timeout in stages:
            revision_fact(REPO,revision,True);assert hashes()==captured
            if identity is not None: assert verify_distribution(package)==identity
            log=BASE/f'S09-owner-worker-{short}-native-{label}.log'
            assert not os.path.lexists(log)
            start=stamp(); owned=None
            try:
                with log.open('xb') as stream:
                    owned=spawn_owned(argv,cwd=REPO,limits=ResourceLimits(timeout),stdout=stream,stderr=subprocess.STDOUT)
                    code=owned.wait()
                reaped=terminate_owned(owned,deadline_seconds=5).reaped
                text=_sanitize(log.read_text(encoding='utf-8',errors='replace'),REPO).replace('\r\n','\n')
                log.write_text(text,encoding='utf-8',newline='\n')
                result=dict(label=label,started_at_utc=start,finished_at_utc=stamp(),exit_code=code,tree_reaped=reaped,
                    log=log.name,log_sha256=sha(log.read_bytes()),passed=code==0 and reaped)
                value['commands'].append(result);proof_owner.persist(value);print(json.dumps(result),flush=True)
                revision_fact(REPO,revision,True);assert hashes()==captured
                if not result['passed']: return 1
                if label=='build':
                    identity=verify_distribution(package)
                    assert identity['executable_revision']==revision and identity['implementation_hash']==context['implementation_hash']
                    value['native_build_identity']=identity
                assert verify_distribution(package)==identity
            finally:
                if owned is not None: assert terminate_owned(owned,deadline_seconds=5).reaped
        value.update(passed=True,input_hashes_after=hashes());proof_owner.persist(value)
    print(json.dumps(dict(passed=True,stages=3,ordinary_native_paper='NOT_RUN')),flush=True)
    return 0

if __name__=='__main__': raise SystemExit(main())
