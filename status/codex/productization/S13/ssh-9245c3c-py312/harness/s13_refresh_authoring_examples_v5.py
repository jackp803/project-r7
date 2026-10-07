from pathlib import Path
import shutil,sys,json
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(repo),str(repo/'src')]
from application.cloud.authoring import emit_package
from tests.strategy.v02_fixtures import definition_v02,field,operator
from tests.strategy.test_slice1_runtime import make_definition
fresh=project/'artifacts/S13-service-current-authoring-examples-v5'
assert not fresh.exists()
source=(project/'artifacts/s14_schema_examples.py').read_text(encoding='utf-8')
source=source[source.index("examples=repo/"):]
source=source.replace("dict(schemas=2,actual_json_packages=4","dict(schemas='NOT_GENERATED',actual_json_packages=4")
source=source.replace("examples=repo/'docs/strategy/authoring-v0.2/examples'","examples=fresh")
exec(compile(source,'s13-current-synthetic-authoring','exec'))
for item in fresh.rglob('*.json'):
    destination=repo/'docs/strategy/authoring-v0.2/examples'/item.relative_to(fresh)
    assert destination.is_file()
    shutil.copyfile(item,destination)
print('Refreshed actual E2/capability synthetic examples; no cloud/provider')
