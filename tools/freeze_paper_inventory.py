"""Development-only fixed PQR inventory generation; commit before execution.

Discovery imports tests in an isolated owned child per directory. This tool
does not execute tests or issue a software receipt. No caller command inventory.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.qualification import source_commands
from application.platform.processes import spawn_owned,ResourceLimits
from application.paper.inventory import NATIVE_ASSERTIONS
from application.paper.inventory import current_target
from tools.paper_toolchain import measure


def cases(directory,pattern):
    suite=unittest.TestLoader().discover(str(ROOT/directory),pattern=pattern)
    def flatten(value):
        if isinstance(value,unittest.TestSuite):
            for child in value:yield from flatten(child)
        else:
            if isinstance(value,unittest.loader._FailedTest):raise ValueError('Test discovery import failed')
            yield value.id()
    names=list(flatten(suite))
    if not names or len(names)!=len(set(names)):raise ValueError('Unique nonempty actual test identities required')
    return names


def generate():
    selected=source_commands(ROOT)
    members=[]
    for index,(directory,pattern) in enumerate(selected,1):
        with tempfile.TemporaryFile() as stream:
            owned=spawn_owned([sys.executable,str(Path(__file__)),'--discover',directory,pattern],
                cwd=ROOT,limits=ResourceLimits(60),stdout=stream,stderr=subprocess.STDOUT)
            code=owned.wait();stream.seek(0);raw=stream.read(4*1024*1024)
        if code!=0 or not owned.termination_report.reaped:raise ValueError('Owned test inventory discovery failed')
        members.append(dict(member_id=f'PQR-01-{index:03d}',kind='UNITTEST',command_ref=f'source-tests-{index:03d}',
            tool_ref='tools/run_credential_free_tests.py',directory=directory,pattern=pattern,
            test_cases=json.loads(raw),assertions=[],timeout_seconds=900,target_predicate='ALL_SOURCE_ON_NAMED_NATIVE_HOST'))
    groups=[dict(check_id='PQR-01',members=members)]
    for group,assertions in NATIVE_ASSERTIONS.items():
        tool='tools/verify_native_product.py' if group=='PQR-02' else 'tools/verify_paper_product.py'
        groups.append(dict(check_id=group,members=[dict(member_id=group+'-native',kind='NATIVE_ASSERTIONS',
            command_ref=group.lower()+'-native',tool_ref=tool,test_cases=[],assertions=list(assertions),
            # Expanded nine-fault plus isolation sequence actually takes >20m.
            # This is only the aggregate harness cap; all child/health/E5/stop
            # deadlines and mandatory observations remain unchanged.
            timeout_seconds=1800 if group=='PQR-05' else 1200,target_predicate='NAMED_NATIVE_TARGET')]))
    paths=sorted(list((ROOT/'tests').rglob('*.py'))+list((ROOT/'tools').glob('*.py'))+
                 list((ROOT/'tools').glob('*.mjs'))+[ROOT/'status/PM_PAPER_RELEASE_MAPPING_DECISION_20261013.md',
                 ROOT/'packaging/windows/requirements-build-py312.lock',
                 ROOT/'packaging/linux/requirements-build-py312.lock',ROOT/'ui/package-lock.json'])
    files={path.relative_to(ROOT).as_posix():'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    for group in groups:
        for member in group['members']:member['tool_hash']=files[member['tool_ref']]
    value=dict(schema_version='r7-qualified-paper-inventory-v0.2',profile_id='r7-qualified-paper-release-v0.2',
        decision_ref='PM_PAPER_RELEASE_MAPPING_DECISION_20261013',
        decision_hash=files['status/PM_PAPER_RELEASE_MAPPING_DECISION_20261013.md'],
        source_files=files,groups=groups,execution_toolchains={current_target():measure(ROOT)})
    path=ROOT/'src/application/paper/_fixed_inventory.py'
    path.write_text('"""Generated fixed PQR data; regenerate and commit before qualification."""\nFROZEN = '+repr(value)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(groups=len(groups),commands=sum(len(g['members']) for g in groups),
        test_cases=sum(len(m['test_cases']) for g in groups for m in g['members']),source_files=len(files))))


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--discover':
        print(json.dumps(cases(sys.argv[2],sys.argv[3])))
    elif len(sys.argv)==1:generate()
    else:raise SystemExit('Only fixed development inventory generation is supported')
