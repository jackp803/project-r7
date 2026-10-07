from pathlib import Path
base=Path(__file__).resolve().parent;target=base/'s14_feedback_source_qualify.py'
broken=target.read_bytes();history=base/'s14_feedback_source_qualify.before-execution-syntax-repair.py'
assert not history.exists()
try:compile(broken,str(target),'exec')
except SyntaxError:pass
else:raise ValueError('Expected pre-execution generator failure missing')
history.write_bytes(broken)
original=(base/'s13_installer_qualify.py').read_text(encoding='utf-8')
assert original.count('S13-recovery')==1
text=original.replace('S13-recovery','S14-feedback');start=text.index("scope='S13 bounded root-only")
end=text.index("\n(output/'qualification-context.json')",start)
text=text[:start]+"scope='S14 actual current-owner PAPER feedback projection, original producer/checkpoint lineage, opt-in privacy, canonical monetary graph, bounded durable publication outbox and exact pre-staging schema/render validation; retained complete LF/FP/source regression. Controlled local fixtures only. Native/browser acceptance separate; S12 normal runtime integration, real cloud/forward/provider and Ubuntu NOT_RUN.')\n"+text[end:]
compile(text,str(target),'exec');target.write_text(text,encoding='utf-8',newline='\n')
print('Pre-execution generator syntax repaired; no qualification ran')
