from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
base=Path(__file__).resolve().parent
names=['s13_ssh_candidate_pipeline.py','s13_ssh_qualify.py','s13_native_ssh_probe.py','s13_native_access_integrity.py',
    's13_native_access_integrity_tests.py','s13_ssh_acceptance_integrity.py','s13_ssh_acceptance_integrity_tests.py','s13_ssh_accept.py']
data=dict(reviewed_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),reviewer='/root/qualification_review',
    kind='INDEPENDENT_BOUNDED_READ_ONLY_SSH_NATIVE_HARNESS_AND_ACCEPTANCE_GUARD_REVIEW',remaining_critical=0,remaining_important=0,
    resolved_important_findings=['readiness redirects denied','owned native control generation and actual Job Object membership before/after probes',
        'single-argument report loader preserved by narrow template change'],
    harness_hashes={name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names},
    reviewer_execution='NONE',actual_tests='SEPARATE_CODEX_LOCAL_RUNS:4_HARNESS_AND9_SSH_RETENTION_GUARD',
    real_ssh='NOT_RUN',native_ubuntu='NOT_RUN',whole_branch='NOT_REVIEWED')
target=base/'S13-ssh-independent-harness-review.json';assert not target.exists()
target.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Recorded bounded SSH harness and retention guard review')
