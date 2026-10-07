"""Derive a fresh serial policy; add native historical publication only."""
from pathlib import Path
import ast
base=Path(__file__).resolve().parent
for name in ('candidate_pipeline','ui_frontend','bound_installer','source_qualify','serial_browser_qualify'):
    source=base/('s12_runtime_supervision_'+name+'.py')
    target=base/('s14_feedback_cli_'+name+'.py');assert not target.exists()
    code=source.read_text(encoding='utf-8').replace('s12_runtime_supervision_','s14_feedback_cli_').replace('S12-runtime-supervision','S14-feedback-cli')
    code=code.replace('S12_RUNTIME_CLOUD_SUPERVISION_WITH_UNCHANGED_WINDOWS_NATIVE_AND_BROWSER_REGRESSION',
        'S14_HISTORICAL_PAPER_PUBLICATION_COMPOSITION_WITH_WINDOWS_NATIVE_AND_BROWSER_REGRESSION')
    if name=='candidate_pipeline':
        old=" ('native-restore',[python,str(base/'s13_native_recovery_probe.py'),str(package),str(outputs['restore'])],600),"
        assert old in code
        code=code.replace(old,old+"\n ('native-paper-feedback',[python,str(base/'s14_feedback_cli_native_paper.py'),str(package),str(base/'S14LocalFakeRclone.exe'),str(base/f'r7-native-S14-feedback-cli-paper-{short}')],600),")
        code=code.replace("'s14_native_probe.py','s13_native_recovery_probe.py','S14LocalFakeRclone.exe')",
            "'s14_native_probe.py','s13_native_recovery_probe.py','s14_feedback_cli_native_paper.py','S14LocalFakeRclone.exe','S14LocalFakeRclone.cs')")
    if name=='source_qualify':
        start=code.index("scope='S12 actual")
        end=code.index(".')",start)+2
        code=code[:start]+"scope='S14 configured existing E6 historical PAPER feedback publication through the actual cloud CLI, one shared intake/research/PAPER batch limit, original cloud host scope, no runtime attachment or lease renewal; retained complete LF/FP/source regression. Local accelerated owners and fake transport only. Normal runtime composition and production qualified release issuance pending; real cloud/forward/provider and native Ubuntu NOT_RUN.'"+code[end:]
    ast.parse(code)
    target.write_text(code,encoding='utf-8',newline='\n')
print('Prepared five fresh launchers with unchanged source/timeouts and added native historical PAPER proof')
