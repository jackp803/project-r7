from pathlib import Path
import ast,hashlib,json,tempfile
BASE=Path(__file__).resolve().parent
from s09_ui_dependency_inputs import protected_bytes
module=ast.parse((BASE/'publish_s15_negative_checkpoint.py').read_text(encoding='utf-8'))
defs=[n for n in module.body if isinstance(n,ast.FunctionDef)]
ns={'hashlib':hashlib,'json':json,'protected_bytes':protected_bytes,'retained_hashes':{}}
exec(compile(ast.Module(body=defs,type_ignores=[]),'publish_s15_negative_checkpoint.py','exec'),ns)
with tempfile.TemporaryDirectory(prefix='S15-publication-binding-guard-',dir=BASE) as folder:
    root=Path(folder);ns['REPO']=root
    local=root/'source.json';pub=root/'public.json';original=root/'public.json.raw'
    raw=b'{"passed":true}\r\n';normal=raw.replace(b'\r\n',b'\n')
    local.write_bytes(raw);pub.write_bytes(normal);original.write_bytes(raw)
    sha=lambda v:'sha256:'+hashlib.sha256(v).hexdigest()
    row=dict(path='public.json',sha256=sha(normal),bytes=len(normal),original_sha256=sha(raw),raw_subject_path='public.json.raw')
    manifest={'artifacts':[row,dict(path='public.json.raw',sha256=sha(raw),bytes=len(raw))]}
    check=ns['verify_retained'];assert check(local,'public.json',manifest)=={'passed':True}
    assert ns['retained_hashes']['public.json']==sha(normal)
    denied=0
    for path,replacement in [(pub,b'{"passed":false}\n'),(original,b'{"passed":false}\r\n'),(local,b'{"passed":false}\r\n')]:
        prior=path.read_bytes();path.write_bytes(replacement)
        try:check(local,'public.json',manifest)
        except AssertionError:denied+=1
        else:raise AssertionError('Changed retained/external bytes accepted')
        path.write_bytes(prior)
    assert denied==3
print(json.dumps({'publication_binding_guards':'PASS','valid_capture':1,'changed_subjects_rejected':3,'source_qualification_credit':False}))
