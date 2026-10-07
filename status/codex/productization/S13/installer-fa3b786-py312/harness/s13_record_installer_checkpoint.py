from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
names=['src/application/platform/service_admin.py','src/application/platform/service_admin_files.py','src/application/platform/service_admin_removal.py',
    'src/application/cli.py','tools/build_product.py','packaging/linux/install-service.sh','packaging/linux/uninstall-service.sh',
    'packaging/linux/FIRST_RUN.md','docs/product/NATIVE_UBUNTU_SERVICE_ADMIN.md','docs/product/NATIVE_UBUNTU_SERVICE_PLAN.md',
    *['tests/application/'+name for name in ('test_service_admin.py','test_service_admin_backend.py','test_service_admin_removal.py','test_service_admin_cli.py','test_service_admin_packaging.py')]]
test=json.loads((base/'S13-service-installer-review-fixed-GREEN.json').read_bytes());assert test['passed'] and test['tests_run']==40
review=dict(reviewed_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),reviewer='/root/qualification_review',
    kind='INDEPENDENT_BOUNDED_READ_ONLY_INSTALLER_CORE_CLI_PACKAGE_AND_LINK_REMEDIATION_REVIEW',remaining_critical=0,remaining_important=0,
    reviewed_source_hashes={name:'sha256:'+hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in names},
    resolved_important_findings=['explicit missing receipt-parent prerequisite','transferred leaf verification/no-replace preservation protocol',
        'exclusive package-asset leaf creation rejects dangling entries before write'],
    reviewer_execution='NONE',actual_tests='SEPARATE_CODEX_LOCAL_RUNS:40_SOURCE_TESTS_PLUS4_WINDOWS_GIT_SH_FAKE_EXECUTABLE_COMMANDS',
    windows_file_symlink='NOT_RUN;ACTUAL_WINERROR1314;CONTROLLED_DIRECTORY_ENTRY_SEAM_TESTED',native_ubuntu='NOT_RUN',
    actual_systemctl='NOT_RUN',actual_root_administration='NOT_RUN',whole_branch='NOT_REVIEWED')
dest=base/'S13-service-installer-independent-source-review.json';assert not dest.exists()
dest.write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8',newline='\n')
path=repo/'coordination/CODEX/PROGRESS.json';progress=json.loads(path.read_bytes())
assert progress['qualified_executable_revision']=='9245c3c9cd6aa369f04ed6d7aa909225dbc15cd7'
progress['service_admin_increment']=dict(status='IMPLEMENTED_SOURCE_PASS;EXACT_CLEAN_QUALIFICATION_PENDING',source_tests=40,
    controlled_protocol_backend_tests=30,cli_tests=6,package_tests=4,actual_windows_git_sh_fake_commands=4,
    independent_bounded_review='NO_REMAINING_CRITICAL_OR_IMPORTANT',native_ubuntu='NOT_RUN',actual_systemctl='NOT_RUN',
    actual_root_administration='NOT_RUN',service_start='NOT_PERFORMED',service_enable='NOT_PERFORMED',financial_authority='NONE')
progress['next_step']='Freeze and qualify bounded installer code/CLI and actual Windows native denial, then continue S12 continuous runtime/restoration and S14-S16; actual Ubuntu/cloud/SSH/real forward/provider commissioning remains NOT_RUN.'
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
path=repo/'coordination/CODEX/HANDOFF.md'
note='S13 bounded installer source integrated:40 source tests (30 controlled backend/protocol,6 typed CLI,4 sealed asset regressions) and4 actual Windows Git-sh wrapper commands with fake executable PASS; native Ubuntu/root/systemctl/renameat2 NOT_RUN. Independent bounded review0 remaining Critical/Important after receipt-directory prerequisite, verified private quarantine removal and exclusive package-asset creation. Actual Windows file symlink lacked privilege (WinError1314); controlled entry-seam regression and explicitly reconstructed observed pre-fix defect evidence retained, no kernel claim. New exact-clean qualification PENDING; accepted executable remains9245c3c9cd6aa369f04ed6d7aa909225dbc15cd7. Continue automatically with same bounded branch.\n\n'
path.write_text(note+path.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print('Recorded reviewed installer SOURCE checkpoint; native Ubuntu remainsNOT_RUN')
