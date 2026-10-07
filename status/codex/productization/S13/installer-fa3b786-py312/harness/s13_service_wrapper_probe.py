"""Actual local Git-sh wrapper execution against a fake native executable only."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile
project=Path(__file__).resolve().parent.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize
shell=Path('C:/Program Files/Git/bin/sh.exe');assert shell.is_file()
output=project/'artifacts/S13-service-wrapper-windows-git-sh';assert not output.exists();output.mkdir()
report=dict(scope='ACTUAL_WINDOWS_GIT_SH_WITH_SYNTHETIC_EXECUTABLE_ONLY',native_ubuntu='NOT_RUN',actual_systemctl='NOT_RUN',commands=[],passed=False)
def msys(path):
    value=path.absolute().as_posix();return '/'+value[0].lower()+value[2:]
with tempfile.TemporaryDirectory(prefix='wrapper 中文 空格 ',dir=project/'artifacts') as temporary:
    root=Path(temporary);package=root/'native package 中文';package.mkdir();cwd=root/'other cwd';cwd.mkdir()
    executable=package/'r7';executable.write_bytes(b'#!/bin/sh\nset -eu\nprintf "%s\\0" "$@" > "$R7_WRAPPER_CAPTURE"\n');executable.chmod(0o755)
    for filename,command in (('install-service.sh','install-services'),('uninstall-service.sh','uninstall-services')):
        origin=repo/'packaging/linux'/filename;script=package/filename;shutil.copyfile(origin,script)
        capture=root/'argv.bin';args=['--config','/etc/r7/設定 空格.json','--literal','$(touch MUST_NOT_EXIST); * -x']
        for mode in ('syntax','literal-argv'):
            label=filename[:-3]+'-'+mode;log=output/(label+'.log');raw=output/(label+'.raw')
            argv=[str(shell),'-n',msys(script)] if mode=='syntax' else [str(shell),msys(script),*args]
            env=dict(os.environ,PATH='',R7_WRAPPER_CAPTURE=msys(capture),PYTHONPATH='')
            with raw.open('xb') as stream:
                owned=spawn_owned(argv,cwd=cwd,limits=ResourceLimits(15),stdout=stream,stderr=subprocess.STDOUT,env=env);code=owned.wait()
            text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
            preserved=mode=='syntax' or capture.read_bytes()==b'\0'.join(value.encode('utf-8') for value in [command,*args])+b'\0'
            item=dict(name=label,exit_code=code,tree_reaped=owned.termination_report.reaped,literal_arguments_preserved=preserved,
                cwd='OUTSIDE_PACKAGE',product_path='EMPTY',passed=code==0 and owned.termination_report.reaped and preserved,
                wrapper_sha256='sha256:'+hashlib.sha256(origin.read_bytes()).hexdigest(),log=log.name,
                log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())
            report['commands'].append(item)
            if capture.exists():capture.unlink()
            assert not (cwd/'MUST_NOT_EXIST').exists()
report['passed']=len(report['commands'])==4 and all(item['passed'] for item in report['commands'])
(output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)
