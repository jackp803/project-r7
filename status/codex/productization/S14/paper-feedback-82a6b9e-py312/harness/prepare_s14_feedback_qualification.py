"""Prepare new named qualification launchers without changing accepted tools."""
from pathlib import Path
base=Path(__file__).resolve().parent
def fresh(name,text):
 path=base/name;assert not path.exists();path.write_text(text,encoding='utf-8',newline='\n')
frontend=(base/'s13_service_ui_frontend.py').read_text(encoding='utf-8')
assert frontend.count('S13-recovery')==1
frontend=frontend.replace('S13-recovery','S14-feedback')
frontend=frontend.replace('S13 guarded service and UI link increment; frontend-only qualification','S14 PAPER feedback increment; unchanged frontend-only qualification')
fresh('s14_feedback_ui_frontend.py',frontend)
browser=(base/'s13_service_serial_browser_qualify_v2.py').read_text(encoding='utf-8')
assert browser.count('S13-recovery')==3
fresh('s14_feedback_serial_browser_qualify.py',browser.replace('S13-recovery','S14-feedback'))
qualifier=(base/'s13_installer_qualify.py').read_text(encoding='utf-8')
assert qualifier.count('S13-recovery')==1
qualifier=qualifier.replace('S13-recovery','S14-feedback')
start=qualifier.index("scope='S13 bounded root-only")
qualifier=qualifier[:start]+"scope='S14 actual current-owner PAPER feedback projection, original producer/checkpoint lineage, opt-in privacy, canonical monetary graph, bounded durable publication outbox and exact pre-staging schema/render validation; retained complete LF/FP/source regression. Controlled local fixtures only. Native/browser acceptance separate; S12 normal runtime integration, real cloud/forward/provider and Ubuntu NOT_RUN.')\n"+qualifier[qualifier.index("\n(output/'qualification-context.json')",start):]
fresh('s14_feedback_source_qualify.py',qualifier)
print('Prepared3 fresh launchers; unchanged33 source commands and11 browser assertions')
