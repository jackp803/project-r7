"""Two EOF-only normalizations; retain discovery and update exact byte bindings."""
import ast,hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from strategy.v02.capabilities import _revision,build_capability_snapshot
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
out=BASE/'k03-whitespace-final-bindings';create_private_directory(out)
changes=[]
for number,ref in enumerate(('src/application/cloud/candidate_index.py','tests/application/test_candidate_index_roundtrip_v02.py')):
    p=ROOT/ref;before=p.read_bytes();text=before.decode('utf-8').replace('\r\n','\n')
    after=(text.rstrip()+'\n').encode()
    assert ast.dump(ast.parse(before))==ast.dump(ast.parse(after))
    assert text.rstrip()==after.decode().rstrip()
    write_private_new(out/(str(number)+'.before.py'),before);p.write_bytes(after)
    changes.append(dict(path=ref,before_hash=sha(before),after_hash=sha(after),change='EOF_WHITESPACE_ONLY;AST_IDENTICAL'))
inventory=ROOT/'src/application/paper/_fixed_inventory.py';old_raw=inventory.read_bytes()
tree=ast.parse(old_raw);value=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)))
write_private_new(out/'inventory-before.py.unapplied',old_raw)
test='tests/application/test_candidate_index_roundtrip_v02.py'
previous=value['source_files'][test];value['source_files'][test]=sha((ROOT/test).read_bytes())
inventory.write_text('"""Generated fixed PQR data; regenerate and commit before qualification."""\nFROZEN = '+repr(value)+'\n',encoding='utf-8',newline='\n')
final=ast.literal_eval(next(n.value for n in ast.parse(inventory.read_bytes()).body if isinstance(n,ast.Assign)))
assert final==value
assert all(sha((ROOT/ref).read_bytes())==expected for ref,expected in value['source_files'].items())
old=ast.literal_eval(next(n.value for n in ast.parse(old_raw).body if isinstance(n,ast.Assign)))
old['source_files'][test]=value['source_files'][test];assert old==final
implementation=_revision();capability=build_capability_snapshot().snapshot_hash
manifests=[]
for name in ('four-hour','legacy','multitimeframe','tactical'):
    p=ROOT/'docs/strategy/authoring-v0.2/examples'/name/'manifest.json';raw=p.read_bytes();doc=json.loads(raw)
    prior=doc['capability_snapshot_hash'];doc['capability_snapshot_hash']=capability
    p.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifests.append(dict(path=p.relative_to(ROOT).as_posix(),old_hash=sha(raw),new_hash=sha(p.read_bytes()),previous_capability=prior,current_capability=capability))
assert _revision()==implementation
report=dict(scope='EOF_ONLY_AST_IDENTICAL_NORMALIZATION_AND_BINDING_REFRESH',test_execution='NONE',
    changes=changes,inventory_previous_hash=sha(old_raw),inventory_current_hash=sha(inventory.read_bytes()),
    inventory_changed_field='source_files.'+test,previous_test_hash=previous,current_test_hash=value['source_files'][test],
    groups_cases_commands_native_deadlines_toolchains_unchanged=True,all_source_file_hashes_valid=True,
    implementation_hash=implementation,capability_hash=capability,manifests=manifests,
    original_discovery_ref='k03-inventory-freeze-first/checkpoint.json',provider_requests=0,credentials='NONE',capital='NONE')
write_private_new(out/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(dict(implementation_hash=implementation,capability_hash=capability,normalizations=2,discovery_reexecuted=False)))
