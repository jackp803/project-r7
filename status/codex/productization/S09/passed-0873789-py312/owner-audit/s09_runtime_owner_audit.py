from pathlib import Path
from dataclasses import asdict
import hashlib,json,subprocess,sys
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(root/'src'),str(root)]
from tests.product.test_paper_runtime_v02 import PaperRuntimeV02Tests
from application.paper.assessment import assess_forward
from strategy.v02.capabilities import _revision
revision=sys.argv[1]
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==revision
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()
output=project/('artifacts/r7-productization-S09-owner-audit-'+revision[:7]); output.mkdir()
fixture=PaperRuntimeV02Tests(); fixture.setUp()
try:
    runtime=fixture.start(); operations=[]
    for seconds,price,bars in ((0,'60000',True),(1,'60000',False),(2,'60020',False),(3,'60020',False)):
        result=runtime.on_market_event(fixture.event(seconds,price,bars=bars))
        recovered=fixture.process.recover(runtime.run_id)
        operations.append(dict(receipt=asdict(result),runtime=recovered.state['runtime']))
    state=fixture.process.recover(runtime.run_id)
    graph=fixture.canonical.recover(position_id=state.state['runtime']['position']['position_id'])
    assert graph.status=='READY' and graph.current_position_projection.payload['lifecycle_state']=='CLOSED'
    assert len(graph.fills)==2 and len(state.state['runtime']['closed_trades'])==1
    assessment=assess_forward(runtime,fixture.service.promotion).as_dict()
    assert assessment['status']=='BLOCKED' and assessment['actual_elapsed_seconds']==0
    audit=dict(namespace='FIXTURE',mode='ACCELERATED_FIXTURE',executable_revision=revision,implementation_hash=_revision(),
        binding=state.binding,operations=operations,broker=state.state['broker'],canonical_graph=asdict(graph),
        forward=assessment,provider_requests=0,credentials='NONE',capital='NONE',real_forward='NOT_RUN')
    raw=json.dumps(audit,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    (output/'full-cycle.json').write_text(raw,encoding='utf-8',newline='\n')
    print(json.dumps(dict(status='PASS',graph_status=graph.status,actual_fills=len(graph.fills),
        closed_trades=1,real_forward='NOT_RUN',audit_sha256=hashlib.sha256(raw.encode()).hexdigest())))
finally: fixture.doCleanups()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()
