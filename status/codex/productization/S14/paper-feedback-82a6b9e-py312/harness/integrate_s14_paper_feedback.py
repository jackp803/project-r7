"""Copy reviewed additive source into the existing branch, refusing overwrite."""
from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent
development=base/'S14-paper-feedback-development'
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
pairs={
 'cloud/paper_feedback.py':'src/application/cloud/paper_feedback.py',
 'cloud/public_feedback.py':'src/application/cloud/public_feedback.py',
 'storage/paper_feedback.py':'src/storage/paper_feedback.py',
 'migrations/0017_paper_feedback_outbox.sql':'src/storage/migrations/0017_paper_feedback_outbox.sql',
 'contracts/paper_feedback_v0_2.schema.json':'contracts/paper_feedback_v0_2.schema.json',
 **{name:'tests/product/'+name for name in ('test_paper_feedback_projection.py','test_paper_feedback_outbox.py',
 'test_paper_feedback_schema.py','test_public_feedback_dispatch.py','test_paper_feedback_bridge.py')},
}
for target in pairs.values():assert not (repo/target).exists(),target
proof=[]
for original,target in pairs.items():
 raw=(development/original).read_bytes()
 if original in ('test_paper_feedback_outbox.py','test_paper_feedback_bridge.py'):
  needle=b",Path(__file__).parent/'migrations'"
  assert raw.count(needle)==1
  raw=raw.replace(needle,b'')
 with (repo/target).open('xb') as stream:stream.write(raw)
 proof.append(dict(original=original,target=target,sha256=hashlib.sha256(raw).hexdigest(),
   adjustment='CANONICAL_DEFAULT_MIGRATION_DIRECTORY' if original in ('test_paper_feedback_outbox.py','test_paper_feedback_bridge.py') else 'BYTE_IDENTICAL'))
path=base/'S14-paper-feedback-integration-files.json';assert not path.exists()
path.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(files=len(proof),scope='DEVELOPMENT_SOURCE_NOT_QUALIFIED')))
