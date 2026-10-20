from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
recipe=json.loads((BASE/'h01-original-exit-storage-draft-assumptions-20261020.json').read_bytes())
for row in recipe['source_hashes']:assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
for row in recipe['draft_hashes']:assert hashlib.sha256((BASE/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
paths={'product_exit_decision.py.unapplied':'src/storage/product_exit_decision.py','0024_product_original_exit.sql.unapplied':'src/storage/migrations/0024_product_original_exit.sql'}
for target in paths.values():assert not (ROOT/target).exists()
target=ROOT/'src/storage/product_dispatch.py';content=target.read_text(encoding='utf-8');marker='    def recover(self, run_id):'
assert content.count(marker)==1
snippet=(BASE/'product_dispatch_exit_facade.py.unapplied').read_text(encoding='utf-8').split('\n',1)[1]
for ref,path in paths.items():
    data=(BASE/ref).read_text(encoding='utf-8').replace('UNAPPLIED / NOT_EXECUTED: ','').replace('-- UNAPPLIED / NOT_EXECUTED; proposed migration filename only, root reserves number.\n','')
    (ROOT/path).write_text(data.rstrip()+'\n',encoding='utf-8',newline='\n')
target.write_text(content.replace(marker,snippet.rstrip()+'\n\n'+marker),encoding='utf-8',newline='\n')
print(json.dumps(dict(status='APPLIED_NOT_EXECUTED',files=3)))
