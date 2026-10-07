"""Named execution evidence only; no requirement is accepted by this index."""
import hashlib,re
from application.qualification import parse_result

CASE_START=re.compile(r'^(test_[A-Za-z0-9_]+) \(([A-Za-z_][A-Za-z0-9_.]*)\) \.\.\. (.*)$')

def validate_execution_row(row):
    if row.get('passed') is not True or row.get('tree_reaped') is not True or type(row.get('returncode')) is not int or row['returncode']!=0:
        raise ValueError('Successful owned execution required')
    counts=('tests_run','tests_passed','failures','errors','skipped','expected_failures','unexpected_successes')
    if any(type(row.get(key)) is not int for key in counts):
        raise ValueError('Actual integer test counts required')
    if row['tests_run']<1 or row['tests_passed']!=row['tests_run'] or any(row[key]!=0 for key in counts[2:]):
        raise ValueError('Complete passing test execution required')

def parse_command_cases(raw,expected_count,returncode):
    text=raw.decode('utf-8').replace('\r\n','\n')
    result=parse_result(text,returncode=returncode)
    if type(expected_count) is not int or expected_count<1 or not result.passed or result.tests_run!=expected_count:
        raise ValueError('Complete passing unittest summary required')
    cases=[];pending=None
    for number,line in enumerate(text.splitlines(),1):
        match=CASE_START.fullmatch(line)
        if match:
            if pending is not None:raise ValueError('Previous named case has no completion')
            method,identity,tail=match.groups()
            if identity.rsplit('.',1)[-1]!=method:raise ValueError('Reported method identity mismatch')
            case=dict(reported_test_id=identity,method=method,status='ok',log_start_line=number)
            if tail.strip()=='ok':case['log_completion_line']=number;cases.append(case)
            elif tail.strip() in ('FAIL','ERROR','expected failure','unexpected success') or tail.startswith('skipped'):
                raise ValueError('Nonpassing individual test status')
            else:pending=case
        elif pending is not None:
            if line.strip()=='ok':
                pending['log_completion_line']=number;cases.append(pending);pending=None
            elif re.match(r'^Ran \d+ tests? in ',line):raise ValueError('Summary cannot complete a pending named test')
    if pending is not None or len(cases)!=expected_count:
        raise ValueError('Named executed case count differs from the actual summary')
    return cases

def read_command_cases(folder,row,command_index):
    from application.datasets.catalog import read_local
    validate_execution_row(row)
    expected=f"{command_index:03d}-{row['phase']}-{row['suite']}.log"
    if row.get('log')!=expected or row['phase'] not in ('phase_1','phase_2') or not re.fullmatch('[a-z][a-z0-9_]+',row['suite']):
        raise ValueError('Canonical owned qualification log required')
    raw=read_local(folder,expected,4*1024*1024)
    if hashlib.sha256(raw).hexdigest()!=row['log_sha256']:
        raise ValueError('Execution log bytes differ from their commitment')
    return parse_command_cases(raw,row['tests_run'],row['returncode'])
