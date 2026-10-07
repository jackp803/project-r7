"""Observed pre-fix function reconstruction, controlled Windows directory-entry seam."""
from pathlib import Path
import importlib.util,io,json,sys,unittest
from unittest.mock import patch
project=Path(__file__).resolve().parent.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'));sys.path.insert(0,str(repo))
import tools.build_product as builder
namespace={name:getattr(builder,name) for name in ('ROOT','Path','shutil')}
source='''def observed_pre_fix(package,target):
    if target != 'linux':return
    files={name:ROOT/'packaging/linux'/name for name in ('install-service.sh','uninstall-service.sh')}
    for name in ('NATIVE_UBUNTU_SERVICE_ADMIN.md','NATIVE_UBUNTU_SERVICE_PLAN.md','SSH_CONTROL_ACCESS.md'):
        files[name]=ROOT/'docs/product'/name
    for name,origin in files.items():
        destination=Path(package)/name
        if destination.exists():raise ValueError('Fresh service wrapper destination required')
        shutil.copyfile(origin,destination)
        destination.chmod(0o755 if name.endswith('.sh') else 0o644)
'''
exec(compile(source,'OBSERVED_PRE_FIX_ASSET_FUNCTION_RECONSTRUCTION','exec'),namespace)
spec=importlib.util.spec_from_file_location('controlled_asset_regression',repo/'tests/application/test_service_admin_packaging.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
suite=unittest.TestSuite([module.ServiceAdminPackagingTests('test_existing_dangling_asset_link_is_refused_without_creating_external_target')])
stream=io.StringIO()
with patch.object(builder,'_retain_service_assets',namespace['observed_pre_fix']):
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
from application.qualification import _sanitize
log=project/'artifacts/S13-service-installer-asset-copy-observed-original-RED.log';assert not log.exists()
log.write_text(_sanitize(stream.getvalue(),repo),encoding='utf-8',newline='\n')
import hashlib
facts=dict(scope='OBSERVED_PRE_FIX_FUNCTION_RECONSTRUCTION;CONTROLLED_WINDOWS_LINK_ENTRY_SEAM;NOT_KERNEL_SYMLINK_ACCEPTANCE',
    tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),expected_defect_reproduced=result.testsRun==1 and len(result.failures)==1 and not result.errors,
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),native_ubuntu='NOT_RUN')
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(facts));raise SystemExit(0 if facts['expected_defect_reproduced'] else 1)
