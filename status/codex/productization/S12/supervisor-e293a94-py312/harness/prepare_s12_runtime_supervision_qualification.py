"""Preserve the accepted serial qualification policy for a new scoped candidate."""
from pathlib import Path
import py_compile

base=Path(__file__).resolve().parent
names=('candidate_pipeline','ui_frontend','bound_installer','source_qualify','serial_browser_qualify')
for name in names:
    source=base/('s14_feedback_'+name+'.py')
    target=base/('s12_runtime_supervision_'+name+'.py')
    assert not target.exists()
    code=source.read_text(encoding='utf-8').replace('s14_feedback_', 's12_runtime_supervision_').replace('S14-feedback','S12-runtime-supervision')
    code=code.replace('S14_PAPER_FEEDBACK_SOURCE_WITH_UNCHANGED_WINDOWS_NATIVE_AND_BROWSER_REGRESSION',
        'S12_RUNTIME_CLOUD_SUPERVISION_WITH_UNCHANGED_WINDOWS_NATIVE_AND_BROWSER_REGRESSION')
    code=code.replace('S14 PAPER feedback increment;', 'S12 runtime/cloud supervision increment;')
    if name=='source_qualify':
        old='S14 actual current-owner PAPER feedback projection, original producer/checkpoint lineage, opt-in privacy, canonical monetary graph, bounded durable publication outbox and exact pre-staging schema/render validation; retained complete LF/FP/source regression. Controlled local fixtures only. Native/browser acceptance separate; S12 normal runtime integration, real cloud/forward/provider and Ubuntu NOT_RUN.'
        new='S12 actual runtime/cloud supervisor roles, complete-lifetime host locks, independent process generations/heartbeats, atomic additive SQLite migration with exact known constraints and commitment-bound migration receipt, active legacy-owner compatibility and preserved configuration/restart inhibition; retained complete LF/FP/source regression including S14 feedback. Controlled local fixtures only. Native/browser acceptance separate; normal PAPER/feedback worker composition, qualified-release issuance and restoration integration pending; real cloud/forward/provider and Ubuntu NOT_RUN.'
        assert old in code
        code=code.replace(old,new)
    target.write_text(code,encoding='utf-8',newline='\n')
    py_compile.compile(str(target),doraise=True)
print('Prepared five new source/native/browser launchers; unchanged execution policy and timeouts')
