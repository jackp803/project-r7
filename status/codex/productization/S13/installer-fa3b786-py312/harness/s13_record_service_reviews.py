from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002';base=project/'artifacts'
digest=lambda path:'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
source=dict(reviewed_at_utc=stamp,reviewer='/root/qualification_review',kind='INDEPENDENT_BOUNDED_READ_ONLY_SOURCE_ASSERTION_REVIEW',
    remaining_critical=0,remaining_important=0,
    important_findings_resolved=['shared writable scope/provisioning root','Unicode pinned config reader','research child config binding','private root owner rwx','creation-only tmpfiles scope inode facts'],
    reviewed_source_hashes={name:digest(repo/name) for name in ['src/application/platform/service_plan.py','src/application/platform/service_guard.py',
        'src/application/control_api/assets.py','src/application/research/worker.py','tests/application/test_service_plan.py','tests/application/test_control_asset_links.py']},
    actual_test_execution='SEPARATE_LOCAL_CODEX_RUNS',reviewer_execution='NONE',ubuntu='NOT_RUN',systemd='NOT_RUN',whole_branch='NOT_REVIEWED',
    withdrawn_candidate='5f42a84e8e3b246bc569d093b8a8b1b4e4c8ac90_NOT_ACCEPTED')
launchers=['s13_service_ui_frontend.py','s13_service_candidate_pipeline.py','s13_service_serial_browser_qualify.py','s13_native_service_denial.py']
harness=dict(reviewed_at_utc=stamp,reviewer='/root/qualification_review',kind='INDEPENDENT_BOUNDED_READ_ONLY_LAUNCHER_DELTA_REVIEW',
    remaining_critical=0,remaining_important=0,harness_hashes={name:digest(base/name) for name in launchers},
    browser_assertions='UNCHANGED_11_CASES_7_ACTUAL_SERIAL_PROFILES;NATIVE_ASSET_INVENTORY_BOUND',
    frontend='5_COMMANDS_ONLY;BROWSER_PENDING_LABEL',pipeline='SERIAL_OWNED_COMMANDS;NO_UBUNTU_ACCEPTANCE',reviewer_execution='NONE')
for name,data in [('S13-service-independent-review-v2.json',source),('S13-service-launcher-review.json',harness)]:
    path=base/name;assert not path.exists();path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
print('Recorded bounded independent source and launcher reviews; qualification remains pending')
