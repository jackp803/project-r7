"""Fresh next-increment launchers; preserve prior exact qualification bytes."""
from pathlib import Path
base=Path(__file__).resolve().parent
def new(name,source):
    target=base/name;assert not target.exists();compile(source,name,'exec')
    target.write_text(source,encoding='utf-8',newline='\n')
full=(base/'s13_service_qualify.py').read_text(encoding='utf-8')
full=full.replace("scope='S13 exact native", "scope='S13 SSH argv planning/public loopback probe and actual frozen helper CLI without connection or credentials; exact native")
full=full.replace('S12/S13 service/SSH/S14 forward/S15/S16 pending.','S12 continuous composition/S13 installer and native Ubuntu/real SSH commissioning/S14 forward/S15/S16 pending.')
new('s13_ssh_qualify.py',full)
pipeline=(base/'s13_service_candidate_pipeline.py').read_text(encoding='utf-8')
pipeline=pipeline.replace(" ('native-smoke'", " ('native-ssh-access',[str(python),str(base/'s13_native_ssh_probe.py'),str(package),str(base/f'r7-native-S13-ssh-access-{short}')],300),\n ('native-smoke'")
pipeline=pipeline.replace('s13_service_qualify.py','s13_ssh_qualify.py')
pipeline=pipeline.replace("qualification_scope='S13_SERVICE_SUBJECT_AND_RETAINED_WINDOWS_RECOVERY'", "qualification_scope='S13_SSH_PLANNER_PUBLIC_NATIVE_PROBE_AND_RETAINED_SERVICE_RECOVERY'")
# Supplementary orchestration logs also carry recorded execution hashes.
pipeline=pipeline.replace('import json,re,sys','import hashlib,json,re,sys')
pipeline=pipeline.replace("log=log.name)","log=log.name,log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())")
new('s13_ssh_candidate_pipeline.py',pipeline)
print('Prepared serial SSH native and full-source qualification launchers')
