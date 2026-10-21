"""One-off committed-blob audit v4 DRAFT; requires established outer owned child."""
from __future__ import annotations
import argparse
from array import array
import bisect
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

PROJECT = Path(r"<USER_HOME>/Desktop/交易機器人主體")
REPO = PROJECT / "workspaces/project-r7-productization-master-20261002"
ART = PROJECT / "artifacts/current-windows-20261019"
RULE_FILE = ART / "l01-l05-local-audit-rules-bffc558.json"
RULE_SHA = "f3c5f660d728298a0fca97104163db096485b439428f53497c71898edd11d5c7"
BLOB_MAX = 16*1024**2
READ_MAX = 512*1024**2
BATCH_MAX = 32*1024**2
META_MAX = 32*1024**2
PATH_MAX = 50000
FINDING_MAX = 10000
HEX = re.compile(r"[0-9a-f]{40}\Z")
FACTS = []
END = 0.0

class AuditError(RuntimeError):
    def __init__(self, code): self.code=code; super().__init__(code)

def fail(code): raise AuditError(code)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def remaining():
    left=END-time.monotonic()
    if left<=0: fail('AUDIT_DEADLINE')
    return min(120.0,left)

def ordinary(path, *, directory=False, trusted_git_binary=False):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts: fail('UNSAFE_LOCAL_PATH')
    for item in reversed((path,*path.parents)):
        info=item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
            fail('LINK_OR_REPARSE_PATH')
    info=path.lstat()
    if directory:
        if not stat.S_ISDIR(info.st_mode): fail('ORDINARY_DIRECTORY_REQUIRED')
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink<1 or (not trusted_git_binary and info.st_nlink!=1):
        fail('ORDINARY_SINGLE_LINK_REQUIRED')
    return info

def local_bytes(path, cap, *, trusted_git_binary=False):
    before=ordinary(path,trusted_git_binary=trusted_git_binary)
    if before.st_size>cap: fail('LOCAL_INPUT_SIZE_LIMIT')
    with open(path,'rb',buffering=0) as handle:
        opened=os.fstat(handle.fileno())
        if (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino): fail('LOCAL_INPUT_REPLACED')
        raw=handle.read(cap+1)
        after=os.fstat(handle.fileno())
    current=ordinary(path,trusted_git_binary=trusted_git_binary)
    if len(raw)!=before.st_size or len(raw)>cap or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or (current.st_dev,current.st_ino,current.st_size,current.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
        fail('LOCAL_INPUT_CHANGED')
    return raw

# REQUIRED external contract: this scanner runs as ONE child of the existing
# application.platform.processes.spawn_owned ResourceLimits owner. Its Windows
# job/process group covers Git descendants. This script does not reimplement it.
def git(git_exe, label, args, *, payload=b'', cap=META_MAX):
    timeout=remaining();started=time.monotonic()
    env={key:os.environ[key] for key in ('SystemRoot','WINDIR','TEMP','TMP','PATH','PATHEXT') if key in os.environ}
    env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never',GIT_OPTIONAL_LOCKS='0',LC_ALL='C')
    command=[str(git_exe),'--no-pager','--no-optional-locks','--no-replace-objects','-c','core.fsmonitor=false','-c','core.hooksPath='+str(ART/'nonexistent-audit-hooks'),'-c','gc.auto=0','-C',str(REPO),*args]
    fact=dict(label=label,exit_code=None,operation_complete=False,direct_child_reaped=False,containment='REQUIRED_EXTERNAL_ESTABLISHED_OWNER_NOT_ATTESTED_HERE')
    try:
        result=subprocess.run(command,input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            timeout=timeout,check=False,env=env,cwd=str(REPO))
        fact.update(exit_code=result.returncode,direct_child_reaped=True,stdout_bytes=len(result.stdout),stderr_bytes=len(result.stderr),stderr_sha256=sha(result.stderr))
        # Post-capture checks only: expected batches/read budget are finite,
        # but subprocess.run and Git may allocate more. Outer ResourceLimits
        # is SOFT_LIMIT_ONLY: timeout/tree containment, no hard memory/RSS cap.
        # Raw captures never hit disk.
        if len(result.stdout)>cap or len(result.stderr)>65536:fail('GIT_OUTPUT_LIMIT')
        if result.returncode!=0:fail('GIT_COMMAND_FAILED')
        fact['operation_complete']=True
        return result.stdout
    except subprocess.TimeoutExpired:
        # subprocess.run kills and waits its direct process on timeout; root owns
        # descendant teardown and must retain that actual closure independently.
        fact.update(direct_child_reaped=True,timed_out=True)
        fail('GIT_CALL_TIMEOUT')
    finally:
        fact['elapsed_seconds']=round(time.monotonic()-started,3)
        FACTS.append(fact)

def oid(raw):
    value=raw.decode('ascii').strip()
    if not HEX.fullmatch(value):fail('GIT_OBJECT_ID_INVALID')
    return value

def text_path(raw):
    if not 1<=len(raw)<=4096:fail('GIT_PATH_LIMIT')
    try:value=raw.decode('utf-8')
    except UnicodeError:fail('GIT_PATH_NOT_UTF8')
    if value.startswith('/') or any(part in ('','..','.') for part in value.split('/')):fail('GIT_PATH_INVALID')
    return value

def tree_rows(raw):
    rows=[];seen=set()
    for record in raw.split(b'\0'):
        if not record:continue
        head,sep,path=record.partition(b'\t')
        fields=head.split()
        if not sep or len(fields)!=3:fail('TREE_FORMAT')
        mode,kind,obj=(part.decode('ascii') for part in fields)
        path=text_path(path)
        if path in seen or not HEX.fullmatch(obj):fail('TREE_FORMAT')
        if (mode,kind) not in (('100644','blob'),('100755','blob'),('120000','blob'),('160000','commit')):fail('TREE_MODE_UNSUPPORTED')
        seen.add(path);rows.append(dict(path=path,mode=mode,kind=kind,git_oid=obj))
        if len(rows)>PATH_MAX:fail('TREE_PATH_LIMIT')
    return rows

def diff_rows(raw,tree):
    parts=raw.split(b'\0');rows=[];i=0
    while i<len(parts) and parts[i]:
        fields=parts[i].decode('ascii').split();i+=1
        if len(fields)!=5 or not fields[0].startswith(':') or fields[4] not in ('A','M','D','T') or i>=len(parts):fail('DIFF_FORMAT')
        path=text_path(parts[i]);i+=1
        oldmode,newmode,oldoid,newoid,status=fields;oldmode=oldmode[1:]
        if not HEX.fullmatch(oldoid) or not HEX.fullmatch(newoid):fail('DIFF_OBJECT_FORMAT')
        if status!='D' and (path not in tree or (tree[path]['mode'],tree[path]['git_oid'])!=(newmode,newoid)):fail('DIFF_TREE_MISMATCH')
        rows.append(dict(path=path,status=status,old_mode=oldmode,new_mode=newmode,old_oid=oldoid,new_oid=newoid))
        if len(rows)>PATH_MAX:fail('DIFF_PATH_LIMIT')
    if any(parts[i:]):fail('DIFF_TRAILING_DATA')
    return rows

TOKEN_RULES=(
 ('GITHUB_TOKEN_STYLE',re.compile(r'(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{30,255}|github_pat_[A-Za-z0-9_]{40,255})(?![A-Za-z0-9_])')),
 ('OPENAI_KEY_STYLE',re.compile(r'(?<![A-Za-z0-9_])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,255}(?![A-Za-z0-9_])')),
 ('GOOGLE_API_KEY_STYLE',re.compile(r'(?<![A-Za-z0-9_])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9_])')),
 ('AWS_ACCESS_KEY_ID_STYLE',re.compile(r'(?<![A-Za-z0-9_])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Za-z0-9_])')),
)
PEM=re.compile(r'-----BEGIN (?P<label>(?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY)-----')
KEY=r'(?:api[_-]?key|api[_-]?secret|secret|client[_-]?secret|secret[_-]?access[_-]?key|access[_-]?token|refresh[_-]?token|private[_-]?key|password|passphrase|credentials|authorization|(?:openai|google|gemini|okx|aws|github|provider)[_-]?(?:api[_-]?)?(?:key|secret|token))'
ASSIGN=re.compile(r'(?<![A-Za-z0-9_])(?:["\']?'+KEY+r'["\']?)(?:\])?\s*(?::|=)\s*(?:"(?P<double>(?:\\.|[^"\\\r\n]){0,4096})"|\'(?P<single>(?:\\.|[^\'\\\r\n]){0,4096})\')',re.I)
NONCREDENTIAL={sha(value.encode()) for value in ('','NONE','NOT_USED','NOT_CONFIGURED','DISABLED','OPT_OUT','REDACTED','<redacted>','<secret>','<token>','YOUR_API_KEY','YOUR_SECRET','PLACEHOLDER')}
AWS_EXAMPLE_SHA='1a5d44a2dca19669d72edf4c4f1c27c4c1ca4b4408fbb17f6ce4ad452d78ddb3'
RUNNER=re.compile(r'^\s*runs-on\s*:\s*(.+)$',re.M|re.I)
USES=re.compile(r'^\s*(?:-\s*)?uses\s*:\s*(.+)$',re.M|re.I)
TRIGGER=re.compile(r'\b(?:gh\s+(?:workflow\s+run|run\s+rerun)|gcloud\s+builds\s+submit|az\s+pipelines\s+run|buildkite-agent\s+pipeline|gitlab-runner\s+exec)\b|https://api\.github\.com/[^\s"\']{1,1024}/actions/[^\s"\']{0,256}',re.I)
ASSERTION=re.compile(r'\b(?:github_compute|github_actions|GITHUB_ACTIONS|hosted_compute|hosted_runner)\b')

def context(path,value):
    if path.startswith(('tests/','ui/qa/')):return 'TEST_OR_QA_CONTEXT_ONLY'
    if path.startswith(('docs/','packaging/')):return 'DOCUMENTATION_OR_PACKAGING_CONTEXT_ONLY'
    if re.search(r'fixture|synthetic|placeholder|example|test[-_]',value,re.I):return 'SYNTHETIC_LITERAL_HINT_ONLY'
    return 'NO_SYNTHETIC_CLASSIFICATION'

def hosted_path(path):
    lower=path.lower()
    return lower.startswith('.github/workflows/') and lower.endswith(('.yml','.yaml')) or lower in ('.gitlab-ci.yml','.circleci/config.yml','.drone.yml','appveyor.yml','bitbucket-pipelines.yml','jenkinsfile','cloudbuild.yaml','cloudbuild.yml','azure-pipelines.yml') or lower.startswith('.buildkite/') and lower.endswith(('.yml','.yaml'))

def scan(path,text,branch,findings):
    newline=array('I',(m.start() for m in re.finditer('\n',text)));dedupe=set()
    def emit(start,rule,value,classification,review=True):
        digest=sha(value.encode('utf-8'));line=bisect.bisect_left(newline,start)+1
        key=(line,rule,digest)
        if key in dedupe:return
        dedupe.add(key)
        if len(findings)>=FINDING_MAX:fail('FINDING_LIMIT')
        findings.append(dict(path=path,line=line,rule=rule,value_sha256=digest,classification=classification,synthetic_category=context(path,value),root_review_required=review,scopes=['HEAD_TREE']+(['BRANCH_INTRODUCED_OR_MODIFIED'] if branch else [])))
    for match in PEM.finditer(text):
        endmarker='-----END '+match.group('label')+'-----';end=text.find(endmarker,match.end(),match.end()+65536)
        value=text[match.start():end+len(endmarker)] if end>=0 else match.group()
        emit(match.start(),'PRIVATE_KEY_PEM',value,'POTENTIAL_SECRET_UNRESOLVED')
    for rule,pattern in TOKEN_RULES:
        for match in pattern.finditer(text):
            value=match.group();documented=rule=='AWS_ACCESS_KEY_ID_STYLE' and sha(value.encode())==AWS_EXAMPLE_SHA
            emit(match.start(),rule,value,'DOCUMENTED_PROVIDER_EXAMPLE' if documented else 'POTENTIAL_SECRET_UNRESOLVED',not documented)
    for match in ASSIGN.finditer(text):
        value=match.group('double') if match.group('double') is not None else match.group('single')
        safe=sha(value.encode()) in NONCREDENTIAL
        emit(match.start(),'QUOTED_SECRET_ASSIGNMENT',value,'EXACT_NONCREDENTIAL_MARKER' if safe else 'POTENTIAL_SECRET_UNRESOLVED',not safe)
    if hosted_path(path):emit(0,'HOSTED_CONFIG_PATH',text,'DECLARED_HOSTED_OR_CI_CONFIG_REQUIRES_REVIEW')
    for match in RUNNER.finditer(text):
        value=match.group(1);category='SELF_HOSTED_DECLARATION_NOT_EXECUTION' if 'self-hosted' in value.lower() else 'GITHUB_HOSTED_LABEL_DECLARATION' if re.search(r'ubuntu|windows|macos',value,re.I) else 'DYNAMIC_OR_UNKNOWN_RUNNER_DECLARATION'
        emit(match.start(),'GITHUB_RUNNER_DECLARATION',value,category)
    for match in USES.finditer(text):emit(match.start(),'ACTION_USES_DECLARATION',match.group(1),'ACTION_REFERENCE_NOT_EXECUTION')
    for match in TRIGGER.finditer(text):emit(match.start(),'HOSTED_RUN_TRIGGER',match.group(),'POTENTIAL_TRIGGER_REFERENCE_NOT_EXECUTION')
    return sum(1 for _ in ASSERTION.finditer(text))

def audit(git_exe,expected,report):
    helper=Path(__file__).absolute();helper_raw=local_bytes(helper,1024**2);git_raw=local_bytes(git_exe,32*1024**2,trusted_git_binary=True)
    rules=local_bytes(RULE_FILE,1024**2)
    if sha(rules)!=RULE_SHA:fail('RULE_MANIFEST_CHANGED')
    report.update(helper_sha256=sha(helper_raw),rules_sha256=sha(rules),git_executable_sha256=sha(git_raw))
    def subject():
        head=oid(git(git_exe,'head',['rev-parse','--verify','HEAD'],cap=256))
        base=oid(git(git_exe,'origin-main',['rev-parse','--verify','refs/remotes/origin/main'],cap=256))
        if head!=expected:fail('HEAD_SUBJECT_MISMATCH')
        return head,base
    before=subject();merge=oid(git(git_exe,'merge-base',['merge-base','--all',before[1],expected],cap=256))
    tree_raw=git(git_exe,'head-tree',['ls-tree','-r','-z','--full-tree',expected]);rows=tree_rows(tree_raw);index={r['path']:r for r in rows}
    diff_raw=git(git_exe,'branch-diff',['diff','--raw','-z','--abbrev=40','--no-renames','--no-ext-diff','--no-textconv',merge,expected,'--'])
    changes=diff_rows(diff_raw,index);branch={r['path'] for r in changes if r['status']!='D'}
    report.update(subject=dict(head=expected,origin_main=before[1],merge_base=merge),head_tree_metadata_sha256=sha(tree_raw),branch_diff_metadata_sha256=sha(diff_raw),branch_changes=changes,inventory=rows,findings=[],hosted_compute_assertion_reference_counts=[])
    objects=list(dict.fromkeys(row['git_oid'] for row in rows if row['kind']=='blob'))
    check=git(git_exe,'blob-sizes',['cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],payload=('\n'.join(objects)+'\n').encode('ascii')) if objects else b''
    sizes={}
    lines=check.splitlines()
    if len(lines)!=len(objects):fail('BLOB_METADATA_COUNT')
    for obj,line in zip(objects,lines):
        fields=line.split()
        if len(fields)!=3 or fields[0].decode('ascii')!=obj or fields[1]!=b'blob' or not fields[2].isdigit():fail('BLOB_METADATA_INVALID')
        sizes[obj]=int(fields[2])
    paths={}
    for row in rows:
        if row['kind']!='blob':row['status']='EXCLUDED_SUBMODULE_CONTENT';continue
        row['bytes']=sizes[row['git_oid']]
        if row['mode']=='120000':row['status']='EXCLUDED_SYMLINK_TARGET';continue
        paths.setdefault(row['git_oid'],[]).append(row)
    budget=0;selected=[]
    for obj,items in paths.items():
        size=sizes[obj]
        reason='EXCLUDED_PER_BLOB_SIZE' if size>BLOB_MAX else 'EXCLUDED_TOTAL_BUDGET' if budget+size>READ_MAX else None
        if reason:
            for row in items:row['status']=reason
        else:budget+=size;selected.append(obj)
    batches=[];batch=[];amount=0
    for obj in selected:
        if batch and (amount+sizes[obj]>BATCH_MAX or len(batch)>=4096):batches.append(batch);batch=[];amount=0
        batch.append(obj);amount+=sizes[obj]
    if batch:batches.append(batch)
    for number,batch in enumerate(batches,1):
        remaining();maximum=sum(sizes[obj]+len(obj)+64 for obj in batch)
        data=git(git_exe,'blob-batch-'+str(number),['cat-file','--batch'],payload=('\n'.join(batch)+'\n').encode('ascii'),cap=maximum)
        offset=0
        for obj in batch:
            nl=data.find(b'\n',offset)
            if nl<0:fail('BLOB_BATCH_FORMAT')
            header=data[offset:nl].split();offset=nl+1;size=sizes[obj]
            if header!=[obj.encode(),b'blob',str(size).encode()]:fail('BLOB_BATCH_SUBJECT')
            raw=data[offset:offset+size];offset+=size
            if len(raw)!=size or data[offset:offset+1]!=b'\n':fail('BLOB_BATCH_TRUNCATED')
            offset+=1
            if hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()!=obj:fail('BLOB_OBJECT_HASH_MISMATCH')
            digest=sha(raw);text=None;reason='EXCLUDED_BINARY_NUL'
            if b'\0' not in raw:
                try:text=raw.decode('utf-8-sig')
                except UnicodeError:reason='EXCLUDED_NON_UTF8'
            for row in paths[obj]:
                row['sha256']=digest;row['status']='SCANNED_UTF8_TEXT' if text is not None else reason
                if text is not None:
                    if text.startswith('version https://git-lfs.github.com/spec/v1\n'):row['external_lfs_content']='NOT_SCANNED'
                    references=scan(row['path'],text,row['path'] in branch,report['findings'])
                    if references:
                        report['hosted_compute_assertion_reference_counts'].append(dict(
                            path=row['path'],reference_count=references,
                            classification='NON_PROOF_REFERENCE_COUNT_ONLY',
                            scopes=['HEAD_TREE']+(['BRANCH_INTRODUCED_OR_MODIFIED'] if row['path'] in branch else [])))
            remaining()
        if offset!=len(data):fail('BLOB_BATCH_TRAILING_DATA')
    if subject()!=before:fail('FINAL_SUBJECT_CHANGED')
    if local_bytes(helper,1024**2)!=helper_raw or local_bytes(RULE_FILE,1024**2)!=rules or local_bytes(git_exe,32*1024**2,trusted_git_binary=True)!=git_raw:fail('FINAL_TOOL_CHANGED')
    report['hosted_compute_assertion_reference_total']=sum(row['reference_count'] for row in report['hosted_compute_assertion_reference_counts'])
    unresolved=sum(row['root_review_required'] for row in report['findings'])
    incomplete=any(row['status'] in ('EXCLUDED_PER_BLOB_SIZE','EXCLUDED_TOTAL_BUDGET') for row in rows)
    report.update(status='STOP_ROOT_REVIEW' if unresolved or incomplete else 'SCOPED_SCAN_COMPLETE_NO_UNRESOLVED_PATTERN_MATCH',unresolved_findings=unresolved,raw_blob_bytes_read=budget,scope_complete_with_declared_binary_limits=not incomplete,tree_inventory_sha256=sha(canonical(rows)),final_subject_unchanged=True,final_tools_unchanged=True)

class SafeParser(argparse.ArgumentParser):
    def error(self,message):fail('INVALID_ARGUMENTS')

def publish(path,report):
    ordinary(ART,directory=True)
    if path.parent!=ART or not re.fullmatch(r'l01-l05-audit-bffc558-[a-z0-9-]{1,40}\.json',path.name):fail('OUTPUT_NAME_NOT_APPROVED')
    parent=ART.stat();raw=json.dumps(report,indent=2,ensure_ascii=True,allow_nan=False).encode()+b'\n'
    if len(raw)>32*1024**2:fail('REPORT_SIZE_LIMIT')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb',buffering=0) as stream:
        stream.write(raw);os.fsync(stream.fileno());opened=os.fstat(stream.fileno())
    current=ordinary(path)
    if (opened.st_dev,opened.st_ino)!=(current.st_dev,current.st_ino) or (parent.st_dev,parent.st_ino)!=(ART.stat().st_dev,ART.stat().st_ino) or local_bytes(path,len(raw))!=raw:fail('OUTPUT_READBACK_MISMATCH')

def main():
    global END
    if not __debug__:fail('OPTIMIZED_MODE_REFUSED')
    parser=SafeParser(description='DRAFT scoped committed-blob audit; never prints matches')
    parser.add_argument('--expected-head',required=True);parser.add_argument('--git',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();END=time.monotonic()+180
    if not HEX.fullmatch(args.expected_head) or not args.expected_head.startswith('bffc558'):fail('EXPECTED_FIXED_HEAD_REQUIRED')
    ordinary(REPO,directory=True);ordinary(ART,directory=True)
    if not args.git.is_absolute() or args.git.name.lower() not in ('git','git.exe'):fail('ACTUAL_GIT_EXECUTABLE_REQUIRED')
    if args.output.parent!=ART or not re.fullmatch(r'l01-l05-audit-bffc558-[a-z0-9-]{1,40}\.json',args.output.name) or os.path.lexists(args.output):fail('FRESH_APPROVED_OUTPUT_REQUIRED')
    report=dict(schema='r7-l01-l05-committed-audit-v1',draft_tool=True,required_outer_owner='application.platform.processes.spawn_owned ResourceLimits180/300',outer_containment_verified_by_scanner=False,memory_enforcement='NONE_SOFT_LIMIT_ONLY_NO_HARD_MEMORY_GUARANTEE',expected_batch_bytes=BATCH_MAX,selected_blob_read_budget_bytes=READ_MAX,requested_head=args.expected_head,status='INCOMPLETE',scope='HEAD_TREE_AND_LOCAL_ORIGIN_MAIN_MERGE_BASE_DIFF_ONLY',execution_credit='LOCAL_STATIC_PATTERN_SCAN_ONLY_NO_REQUIREMENT_PASS',limits=['No full ancestral history, working-tree, ignored/untracked, binary/image, submodule or symlink-target secret audit','UTF-8 text pattern scan cannot prove absence of encoded, split, dynamic or unfamiliar credential forms','Hosted wiring/claims are source observations, not invocation/spend evidence'],git_processes=FACTS)
    try:audit(args.git,args.expected_head,report)
    except BaseException as exc:
        report.update(status='STOP_AUDIT_FAILED',error_code=exc.code if isinstance(exc,AuditError) else 'AUDIT_UNEXPECTED_ERROR',error_type=type(exc).__name__)
    report['all_direct_git_children_reaped']=all(row['direct_child_reaped'] for row in FACTS)
    if not report['all_direct_git_children_reaped']:report['status']='STOP_CLEANUP_UNCONFIRMED'
    publish(args.output,report)
    print(json.dumps(dict(status=report['status'],report_name=args.output.name,findings=len(report.get('findings',[])),unresolved=report.get('unresolved_findings'),report_sha256=sha(local_bytes(args.output,32*1024**2)))))
    return 0 if report['status']=='SCOPED_SCAN_COMPLETE_NO_UNRESOLVED_PATTERN_MATCH' else 2

if __name__=='__main__':
    try:raise SystemExit(main())
    except AuditError as exc:
        print(json.dumps(dict(status='STOP_AUDIT_FAILED',error_code=exc.code)),file=sys.stderr);raise SystemExit(2)
    except Exception:
        print('{"status":"STOP_AUDIT_FAILED","error_code":"UNEXPECTED_OUTER_FAILURE"}',file=sys.stderr);raise SystemExit(2)
