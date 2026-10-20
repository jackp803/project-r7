"""Root classification of one pinned scan; no matched values in artifacts."""
from pathlib import Path
from collections import Counter,defaultdict
import ast,hashlib,importlib.util,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]/'workspaces/project-r7-productization-master-20261002'
BASE=Path(__file__).resolve().parent
scan_path=BASE/'l01-l05-audit-3ae6460-first.json';raw_scan=scan_path.read_bytes()
assert hashlib.sha256(raw_scan).hexdigest()=='273eea3d4ea52482bed90bc4951f3988d3051a33d83fa93a9712940d272368b0'
scan=json.loads(raw_scan)
assert scan['final_subject_unchanged'] and scan['final_tools_unchanged'] and scan['all_direct_git_children_reaped']
assert scan['scope_complete_with_declared_binary_limits'] and scan['unresolved_findings']==95
assert all(row['rule']=='QUOTED_SECRET_ASSIGNMENT' for row in scan['findings'])
helper=BASE/'audit_l01_l05_committed_tree_owned_v4_20261021.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='fae54906ac495d42a19df84c3b66a07b131fce7d790835f0df23c191f1d5872c'
spec=importlib.util.spec_from_file_location('audit_rules',helper);rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
groups=defaultdict(list)
for row in scan['findings']:
    if row['root_review_required']:groups[row['value_sha256']].append(row)
assert len(groups)==42
manual={
    '7a01d1996d8edfc5041415975bb3620d23bad1c348cf44e18955ccb98ccf11ee':('NONCREDENTIAL_SSH_PLAN_STATUS','plan_ssh_tunnel result status NOT_READ, no credential input/read'),
    '715dc8493c36579a5b116995100f635e3572fdf8703e708ef1a08d943b36774e':('REJECTION_TEST_TAINT_LITERAL','test_bundle_mutation_private_payload_and_old_process_receipt_are_rejected constructs rejected payload'),
    '35e0d0360a0af6d115f9df30e1b00b5b544ebf4bb93272aa02cd5d64b064a64b':('REJECTION_TEST_MANIFEST_FIELD','test_manifest_traversal_unknown_schema_and_duplicate_subjects_are_rejected mutates synthetic manifest and expects BackupError'),
    'b98df9051510f52dc6acb9d7a4658ce158aa925995ac1f1220249cb1d74d5c9e':('UNSENT_TEST_DRIVER_INPUT','test_setup_uses_positive_fixture_without_temporal_expiry_or_early_login assigns only fake driver object input'),
    'e6d72ea8d2cbce581418e39bbbcd3d6e0d299bb683858dc6fa33cb44e6ead2f2':('REJECTION_TEST_EXTRA_PRIVATE_FIELD','test_unknown_files_and_private_endpoint_or_extra_secret_field_remain_rejected adds invalid synthetic capture field'),
    '83aaae26be52087d57a7fdf0b6b7fdc5eadc9d4b92a556cc85188ff45cb5963c':('NONCREDENTIAL_NEGATIVE_STATUS','test_identity_types_software_commitments_and_authority_are_validated passes invalid credentials PRESENT status'),
    '43ed5c457b799abe72e15e5ce574960937404f72402c5c15837044c1fc1a3a4a':('REJECTED_PROVIDER_PARAMETER_LITERAL','Controlled public transport tests add an explicitly forbidden parameter and require ValueError before network attempts; related test uses share same rejection literal'),
    'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb':('UNPERSISTED_GENERATOR_FRAGMENT','PublicFixture password starts with one repeated character then runtime secrets.token_hex; artifact contains generator fragment only'),
    '636646ce0490d0cbf958ebfa35139da0b1748819e05b14e86f275d7e7b9876c9':('FETCH_PROTOCOL_ENUM','ControlAPI uses browser credentials same-origin mode, not an account credential'),
}
decisions=[];cache={}
for digest,rows in groups.items():
    row=sorted(rows,key=lambda r:(not r['path'].startswith('tests/'),not r['path'].startswith('src/'),r['path']))[0]
    path=row['path']
    if path not in cache:
        blob=subprocess.run(['git','show',scan['subject']['head']+':'+path],cwd=ROOT,check=True,capture_output=True,timeout=5).stdout
        cache[path]=(blob,blob.decode('utf-8-sig'))
    blob,text=cache[path];matches=[]
    for m in rules.ASSIGN.finditer(text):
        value=m.group('double') if m.group('double') is not None else m.group('single')
        if hashlib.sha256(value.encode()).hexdigest()==digest and text.count('\n',0,m.start())+1==row['line']:matches.append(value)
    assert matches and len(set(matches))==1
    value=matches[0];symbols=[]
    if path.endswith('.py'):
        try:
            for node in ast.walk(ast.parse(text)):
                if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and node.lineno<=row['line']<=node.end_lineno:symbols.append(node.name)
        except SyntaxError:pass
    if digest in manual:category,basis=manual[digest]
    else:
        assert re.search(r'fixture|synthetic|test|fake|demo|example|redact|placeholder',value,re.I)
        assert path.startswith(('tests/','status/codex/','ui/qa/'))
        category='SYNTHETIC_TEST_INPUT_OR_ARCHIVED_HARNESS_NARRATIVE'
        basis='Root-reviewed test/harness/review context and explicit synthetic/fake/test/redaction literal; no external credential validation performed'
    decisions.append(dict(value_sha256=digest,category=category,basis=basis,occurrences=len(rows),
        reviewed_primary_ref=path,reviewed_line=row['line'],reviewed_source_sha256=hashlib.sha256(blob).hexdigest(),
        owner_symbols=symbols,all_refs=[dict(path=r['path'],line=r['line']) for r in rows]))
assert sum(row['occurrences'] for row in decisions)==95
inventory=scan['inventory']
hosted_paths=[row['path'] for row in inventory if rules.hosted_path(row['path'])]
assert not hosted_paths
report=dict(status='ROOT_RESOLVED_SCOPED_COMMITTED_TREE_PATTERN_AUDIT',review='ROOT_SELF_REVIEW',subject=scan['subject'],
    scan_sha256=hashlib.sha256(raw_scan).hexdigest(),scanner_tree_owned='committed-tree-owned-first/checkpoint.json',
    scanned_tree_paths=len(inventory),inventory_status_counts=dict(Counter(row['status'] for row in inventory)),
    raw_blob_bytes_read=scan['raw_blob_bytes_read'],source_snapshot='COMMITTED_HEAD_ONLY',
    secret_format_matches=dict(PRIVATE_KEY_PEM=0,GITHUB_TOKEN_STYLE=0,OPENAI_KEY_STYLE=0,GOOGLE_API_KEY_STYLE=0,AWS_ACCESS_KEY_ID_STYLE=0),
    quoted_assignment_matches=len(scan['findings']),noncredential_marker_occurrences=len(scan['findings'])-95,
    manual_review_occurrences=95,manual_review_distinct_literals=42,unresolved_after_root_review=0,confirmed_real_secrets=0,
    hosted_configuration_paths=hosted_paths,hosted_runner_or_trigger_findings=0,
    l05_scope='Current committed tree and origin/main merge-base branch diff; declarations/absence only, not historical spend proof',
    decisions=decisions,limits=scan['limits'],
    no_whole_ancestral_history_or_binary_secret_absence_claim=True,provider_requests=0,credentials_access='NONE',github_compute='NOT_USED')
path=BASE/'l01-l05-root-triage-3ae6460-20261021.json'
with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:report[key] for key in ('status','scanned_tree_paths','raw_blob_bytes_read','manual_review_occurrences','manual_review_distinct_literals','unresolved_after_root_review','confirmed_real_secrets','hosted_configuration_paths')}))
