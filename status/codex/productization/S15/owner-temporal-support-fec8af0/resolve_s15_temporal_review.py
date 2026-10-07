"""Preserve reviewed wording history and regenerate the narrowed draft."""
from pathlib import Path
import ast,json
base=Path(__file__).resolve().parent;project=base.parent.resolve()
generator=(base/'prepare_s15_temporal_support_draft.py').read_text(encoding='utf-8')
tree=ast.parse(generator)
behaviors={node.value.args[0].value:node.value.args[1].value for node in tree.body
    if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)
    and isinstance(node.value.func,ast.Name) and node.value.func.id=='add'}
for stem in ('selection','draft'):
    target=base/f'S15-temporal-support-{stem}-fec8af0.json'
    previous=base/f'S15-temporal-support-{stem}-fec8af0.before-semantic-review.json'
    assert target.resolve().is_relative_to(project) and previous.resolve().is_relative_to(project)
    assert not previous.exists()
    previous.write_bytes(target.read_bytes())
    if stem=='selection':
        body=json.loads(target.read_bytes())
        for row in body['requirements']:row['supported_behavior']=behaviors[int(row['id'].split('-')[1])]
        target.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    else:target.unlink()
print('Three semantic wording findings narrowed; both original artifacts preserved.')
