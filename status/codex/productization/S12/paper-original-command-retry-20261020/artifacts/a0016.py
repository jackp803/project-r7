"""No-read source probe of the exact historical artifact capture loop."""
import ast,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(ROOT/'src'))
from application.cloud.manifest import safe_relative
from application.cloud.protocol import CloudError
history=ROOT/'status/codex/productization/S12/current-windows-1e99e09-native07-depth'
bindings=json.loads((history/'disposition.json').read_bytes())['artifacts']
original=next(row for row in bindings if row['original_ref'].endswith('/retain_native07_depth_history.py'))
before=(history/original['retained_ref']).read_text(encoding='utf-8')
after=(BASE/'retain_native07_depth_history.py').read_text(encoding='utf-8')
def probe(source):
    tree=ast.parse(source)
    loop=next(node for node in tree.body if isinstance(node,ast.For)
        and isinstance(node.iter,ast.Subscript) and isinstance(node.iter.value,ast.Name)
        and node.iter.value.id=='result' and isinstance(node.iter.slice,ast.Constant)
        and node.iter.slice.value=='artifacts')
    compiled=compile(ast.Module(body=[loop],type_ignores=[]),'<capture-loop-probe>','exec')
    calls=[];rejections=0
    for ref in ('C:/Approved/project/other-private.log','../other-private.log','/absolute.log','nested/../../escape.log'):
        scope=dict(result={'artifacts':[dict(ref=ref,hash='sentinel')]},output=Path('C:/Approved/project/native-output'),
            capture=lambda *args:calls.append(args),safe_relative=safe_relative)
        try:exec(compiled,scope)
        except CloudError:rejections+=1
    return dict(rejected_before_read=rejections,capture_calls=len(calls))
value=dict(before=probe(before),after=probe(after),scope='SOURCE_CAPTURE_LOOP_SENTINEL;NO_PRIVATE_FILES_READ;NO_NATIVE_CREDIT')
assert value['before']==dict(rejected_before_read=0,capture_calls=4)
assert value['after']==dict(rejected_before_read=4,capture_calls=0)
(BASE/'native07-history-scope-probe.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value))
