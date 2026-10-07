"""Temporarily stage only identified agent evidence, then restore identical bytes."""
from pathlib import Path
import hashlib,json,subprocess,sys
base=Path(__file__).resolve().parent;project=base.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
git=r'C:\Program Files\Git\cmd\git.exe'
revision='fec8af0f70d787deea720b1e7f952c4fca9487b5'
tracked=('coordination/CODEX/PROGRESS.json','coordination/CODEX/HANDOFF.md')
untracked=('status/codex/productization/S14/cli-publisher-fec8af0-py312',
 'status/codex/productization/S14/cli-publisher-artifact-hashes-fec8af0.json',
 'status/codex/productization/S14/HISTORICAL_PAPER_CLI_QUALIFICATION_fec8af0.md')
run=lambda *args:subprocess.check_output([git,'-c','core.quotepath=false','-C',str(repo),*args])
assert run('rev-parse','HEAD').decode().strip()==revision
status=run('status','--porcelain').decode('utf-8').splitlines()
expected={' M '+name for name in tracked}|{'?? '+name+('/' if (repo/name).is_dir() else '') for name in untracked}
assert set(status)==expected,(status,expected)
stage=base/'S14-collection-fec8af0-stage';assert not stage.exists()
pairs=[((repo/name).resolve(),(stage/Path(name).name).resolve()) for name in untracked]
# Validate every absolute recursive-move source/destination BEFORE any move.
for source,destination in pairs:
    assert source.is_relative_to(repo.resolve()) and destination.is_relative_to(stage.resolve())
    assert stage.resolve().is_relative_to(base.resolve()) and base.resolve().is_relative_to(project.resolve())
    assert source.exists() and not destination.exists() and not source.is_symlink()
saved={name:(repo/name).read_bytes() for name in tracked}
original={name:run('show','HEAD:'+name) for name in tracked}
digest=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()
before={name:digest(raw) for name,raw in saved.items()}
for name in untracked:
    path=repo/name
    for file in sorted(path.rglob('*')) if path.is_dir() else [path]:
        if file.is_file():before[file.relative_to(repo).as_posix()]=digest(file.read_bytes())
stage.mkdir();moved=[]
try:
    for source,destination in pairs:source.rename(destination);moved.append((source,destination))
    for name,raw in saved.items():(stage/(Path(name).name+'.qualified.saved')).write_bytes(raw)
    for name,raw in original.items():(repo/name).write_bytes(raw)
    assert run('status','--porcelain').strip()==b''
    subprocess.run([sys.executable,str(base/'run_s15_execution_index_fec8af0_tests.py'),
        'S15-executed-case-index-fec8af0-log-reference-GREEN'],check=True)
    subprocess.run([sys.executable,str(base/'build_s15_execution_index_fec8af0.py'),revision],check=True)
    assert run('status','--porcelain').strip()==b''
finally:
    for name,raw in saved.items():(repo/name).write_bytes(raw)
    for source,destination in reversed(moved):
        assert source.is_relative_to(repo.resolve()) and destination.is_relative_to(stage.resolve())
        assert not source.exists() and destination.exists();destination.rename(source)
after={name:digest((repo/name).read_bytes()) for name in before}
assert before==after and set(run('status','--porcelain').decode('utf-8').splitlines())==expected
receipt=dict(state='RESTORED_IDENTICAL_AGENT_EVIDENCE_BYTES',repository_head=revision,files=len(before),
 before_sha256=before,after_sha256=after,scope='ONLY_EXPLICIT_CURRENT_AGENT_EVIDENCE_AND_TWO_AGENT_METADATA_EDITS',
 recursive_move_boundaries='ALL_ABSOLUTE_TARGETS_CHECKED_BEFORE_MOVES;SAME_PROJECT_ROOT')
target=base/'S15-fec8af0-clean-index-refresh-staging.json';assert not target.exists()
target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(restored_identical_bytes=len(before),clean_index_candidate=revision)))
