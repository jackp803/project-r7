from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,shutil,subprocess,sys,time
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import revision_fact,_sanitize
from application.platform.processes import ResourceLimits,spawn_owned
revision=sys.argv[1]; assert re.fullmatch('[0-9a-f]{40}',revision)
output=project/('artifacts/r7-productization-S13-recovery-ui-qualified-'+revision[:7]+'-safe-logs')
assert not output.exists(); output.mkdir()
node=shutil.which('node'); npm=shutil.which('npm.cmd' if os.name=='nt' else 'npm')
assert node and npm
npm_cli=Path(npm).parent/'node_modules/npm/bin/npm-cli.js'
assert npm_cli.is_file()
def stamp():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def digest(file):return 'sha256:'+hashlib.sha256(file.read_bytes()).hexdigest()
def write_report():
    (output/'ui-qualification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
report=dict(schema_version='r7-local-ui-qualification-v0.2',source_before=revision_fact(root,revision,True),started_at_utc=stamp(),
    launcher_hash=digest(Path(__file__)),commands=[],passed=False,execution='LOCAL',github_compute='NOT_USED',real_provider_calls=0,real_credentials='NONE',capital='NONE',
    node=subprocess.check_output([node,'--version'],text=True).strip(),npm=subprocess.check_output([node,str(npm_cli),'--version'],text=True).strip(),
    browser_channel='msedge',browser_mode='HEADLESS_ISOLATED_FIXTURE',platform='Windows11-x86_64/10.0.26200',
    semantics='S13 recovery UI adds strict restoration health DTO and Traditional-Chinese reconciliation/reauthorization reasons; preserves observed control heartbeat, an available queue without a worker, stopped/failed/unknown and unconfigured services in Traditional Chinese. Actual supervised source browser fixture uses an explicitly synthetic clock and no financial authority. Existing actual isolated auth/E6/intake/research/PAPER/deployment cases remain covered; real cloud/forward/provider/native-service acceptance is not implied')
edge=Path(os.environ['PROGRAMFILES(X86)'])/'Microsoft/Edge/Application/msedge.exe'
assert edge.is_file()
report['browser_version']=subprocess.check_output(['powershell','-NoProfile','-Command',"(Get-Item -LiteralPath 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe').VersionInfo.ProductVersion"],text=True).strip()
commands=[['ci','--ignore-scripts','--no-fund'],['run','types:check'],['run','typecheck'],['test'],['run','build'],['run','test:browser']]
environment=os.environ.copy(); environment.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',NO_COLOR='1')
environment['R7_BROWSER_ARTIFACT_ROOT']=str(output/'browser')
for index,command in enumerate(commands,1):
    revision_fact(root,revision,True); start=time.monotonic(); started=stamp()
    argv=[node,str(npm_cli),'--prefix','ui',*command]; label=(command[-1] if command[0]=='run' else command[0]).replace(':','-')
    log=output/f'{index:02d}-{label}.log'
    with log.open('wb') as stream:
        handle=spawn_owned(argv,cwd=root,limits=ResourceLimits(600),stdout=stream,stderr=subprocess.STDOUT,env=environment)
        code=handle.wait(timeout=610)
    raw=log.read_bytes(); text=_sanitize(raw.decode('utf-8',errors='replace'),root)
    text=re.sub(r'\x1b\[[0-9;]*[a-zA-Z]','',text).replace('\r\n','\n'); log.write_text(text,encoding='utf-8',newline='\n')
    item=dict(command=['npm','--prefix','ui',*command],started_at_utc=started,finished_at_utc=stamp(),duration_seconds=time.monotonic()-start,
        exit_code=code,tree_reaped=handle.termination_report.reaped,log=log.name,original_log_sha256='sha256:'+hashlib.sha256(raw).hexdigest(),
        log_sha256=digest(log),passed=code==0 and handle.termination_report.reaped,source_after=revision_fact(root,revision,True))
    if command==['test']:
        matched=re.search(r'Tests\s+(\d+) passed',text); item['tests_passed']=int(matched[1]) if matched else 0
        item['passed']=item['passed'] and item['tests_passed']>0 and not re.search(r'\d+ failed',text)
    if command==['run','test:browser']:
        source=output/'browser'; browser=json.loads((source/'results.json').read_bytes()); stats=browser['stats']
        item['tests_passed']=stats['expected']; item['browser_stats']=stats
        item['passed']=item['passed'] and stats['expected']>0 and stats['unexpected']==stats['skipped']==stats['flaky']==0
        (output/'browser-results.json').write_text(_sanitize(json.dumps(browser,ensure_ascii=False,indent=2),root)+'\n',encoding='utf-8',newline='\n')
        item['browser_errors']=len(browser.get('errors',[]))
        item['passed']=item['passed'] and item['browser_errors']==0
        if item['passed']:
            for name in ['overview.png','protected-paper.png','approval-preview.png','deployment-pause.png','health.png','supervised-health.png']:shutil.copyfile(source/name,output/name)
    report['commands'].append(item); write_report(); print(f'{index}/{len(commands)} {command}: {"PASS" if item["passed"] else "FAIL"}',flush=True)
    if not item['passed']:break
report['source_after']=revision_fact(root,revision,True)
report['finished_at_utc']=stamp(); report['build_hashes']={file.relative_to(root/'ui/dist').as_posix():digest(file) for file in sorted((root/'ui/dist').rglob('*')) if file.is_file()}
report['input_hashes']={name:digest(root/name) for name in ['ui/package-lock.json','ui/src/api.generated.ts','contracts/control_api_v0_2.openapi.json']}
report['passed']=len(report['commands'])==len(commands) and all(item['passed'] for item in report['commands'])
write_report(); print(json.dumps(dict(passed=report['passed'],commands=len(report['commands']))))
raise SystemExit(0 if report['passed'] else 1)
