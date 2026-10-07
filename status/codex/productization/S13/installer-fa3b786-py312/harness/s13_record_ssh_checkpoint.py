from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002';base=project/'artifacts'
names=['src/application/platform/ssh_access.py','src/application/platform/_loopback_probe.py','src/application/cli.py',
    'tests/application/test_ssh_access.py','tests/application/test_ssh_access_cli.py','docs/product/SSH_CONTROL_ACCESS.md']
review=dict(reviewed_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),reviewer='/root/qualification_review',
    kind='INDEPENDENT_BOUNDED_READ_ONLY_SSH_SOURCE_AND_CLI_INTEGRATION_REVIEW',remaining_critical=0,remaining_important=0,
    reviewed_source_hashes={name:'sha256:'+hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in names},
    actual_execution='SEPARATE_CODEX_LOCAL_TESTS',reviewer_execution='NONE',real_ssh='NOT_RUN',native_ubuntu='NOT_RUN',
    development_tests=22,native_qualification='PENDING')
destination=base/'S13-ssh-independent-source-review.json';assert not destination.exists()
destination.write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8',newline='\n')
path=repo/'coordination/CODEX/PROGRESS.json';progress=json.loads(path.read_bytes())
assert progress['qualified_executable_revision']=='14aeb991aef9d92705cdf0a1151a2df2893e02bb'
progress['ssh_access_increment']=dict(status='IMPLEMENTED_SOURCE_PASS;EXACT_NATIVE_QUALIFICATION_PENDING',
    source_tests=22,entrypoint_regressions=10,platform_regressions=9,independent_bounded_review='NO_REMAINING_CRITICAL_OR_IMPORTANT',
    ssh_connection='NOT_STARTED',credentials='NONE',actual_provider_requests=0,real_tunnel='NOT_RUN',native_ubuntu='NOT_RUN',
    exposure='NONE',scope='OPERATOR_ARGV_PLAN_AND_PUBLIC_LOOPBACK_ENDPOINT_ONLY')
progress['next_step']='Freeze and qualify SSH planner/public-loopback native helper increment; continue actual native service install/uninstall, S12 continuous composition/restoration, S14 forward feedback, S15-S16. Ubuntu and actual SSH/cloud/forward/provider commissioning remain NOT_RUN.'
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=repo/'coordination/CODEX/HANDOFF.md'
note='S13 SSH access source increment integrated:22 actual local SSH/CLI tests,10 entrypoint and9 platform regressions PASS; bounded independent source review0 remaining Critical/Important. Planner displays literal loopback SSH argv without connecting; health probe checks only strict public local auth/status using bounded owned source/frozen helper, no proxy/redirect/credentials. Actual frozen Windows/new exact-clean full/browser qualification PENDING; accepted executable remains14aeb991aef9d92705cdf0a1151a2df2893e02bb. Real SSH/Ubuntu services NOT_RUN;installer/uninstaller and S12/S14-S16 independent work remains. Continue automatically.\n\n'
handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print('Recorded SSH source checkpoint; native acceptance remains pending')
