"""Refuse lost/changed artifacts and self-reported coverage before retention."""
from pathlib import Path,PurePath
import hashlib,json,re,stat

NATIVE_COMMANDS={
 'smoke':['01-doctor','02-init-profile','03-preserve-profile','04-first-control-start-second-process-denied','04-first-control-start',
          '05-control-restart','06-control-config-change','07-unconfigured-research-worker','08-tampered-resource-denied'],
 'cloud':['capabilities','author-legacy','author-four-hour','author-multitimeframe','author-tactical','pull','import-dataset',
          'queue-feedback','publish','publish-idempotent','private-prestage-denied','root-loss'],
 'restore':['01-backup-product-data','02-verify-product-backup','03-restore-product-data','04-existing-generation-denied',
            '04a-backup-databases','04b-verify-databases','04c-restore-databases','05-active-owner-denied',
            '06-control-restart-1','06-control-restart-2','07-backup-restored-product','08-restore-second-product',
            '09-missing-ready-marker-denied','10-tampered-bundle-denied','11-tampered-restore-denied'],
 'denial':['control','research','export']}
NATIVE_SCENARIOS={
 'smoke':['NATIVE_HARDWARE_WITH_EMPTY_PATH','CHINESE_PROFILE_DEFAULTS_AND_PRESERVATION','SECOND_NATIVE_CONTROL_PROCESS_DENIED',
          'ACTUAL_NATIVE_E6_MIGRATIONS','CONTROL_RESTART_AUTH_AND_LOOPBACK_DENIAL','NATIVE_CONFIG_DRIFT_STOPS_CONTROL',
          'NATIVE_UNSELECTED_WORKER_TRUTHFUL','TAMPERED_MIGRATION_DENIED_BEFORE_START'],
 'cloud':['actual-native-current-capability-availability-without-platform-authority',
          'actual-native-authoring-legacy','actual-native-authoring-four-hour','actual-native-authoring-multitimeframe','actual-native-authoring-tactical',
          'actual-native-owned-copy-download-and-author-staging','actual-native-private-dataset-seal-without-oos-decoding-or-namespace-relabel',
          'actual-native-owner-feedback-with-default-opt-out-and-chat-holdout-observation',
          'actual-native-receipt-and-feedback-remote-byte-ack-through-local-compiled-fake',
          'actual-native-durable-ack-does-not-republish-completed-outboxes',
          'actual-native-private-outbox-rejected-before-any-synchronized-stage-write-and-not-acknowledged',
          'actual-native-root-loss-denied-without-empty-root-initialization'],
 'restore':['NATIVE_COMPLETE_EIGHT_STORE_AND_SELECTED_FILE_BACKUP','NATIVE_PRIVATE_BUNDLE_VERIFICATION',
            'NATIVE_FRESH_INHIBITED_RESTORE_PRIVATE_ACL_AND_BYTE_PRESERVATION','RESTORED_SELECTED_SNAPSHOT_SETTINGS_AND_APPLICATION_LEASE_FENCES',
            'E6_UNCERTAINTY_AND_PAPER_STATE_PRESERVED_WITH_NEW_PROCESS_GENERATIONS','EXISTING_RESTORATION_GENERATION_PRESERVED',
            'LEGACY_SEVEN_STORE_NATIVE_RECOVERY_REMAINS_EXPLICITLY_INCOMPLETE','ACTIVE_RUNTIME_OWNER_BLOCKS_RESTORATION',
            'TWO_ACTUAL_NATIVE_CONTROL_RESTARTS_REJECT_COPIED_SESSION_AND_RETAIN_FENCE',
            'NATIVE_COMPLETE_RESTORED_PRODUCT_SUPPORTS_LATER_FRESH_BACKUP_AND_RESTORE','PARTIAL_RESTORATION_CANNOT_START_NATIVE_CONTROL',
            'SAME_SIZE_BUNDLE_TAMPER_FAILS_BEFORE_RESTORATION_CREATION'],
 'denial':['unsupported-Windows-control-denied','unsupported-Windows-research-denied','unsupported-Windows-export-denied']}
PROFILES=('empty','research','paper','protected','temporal','approval','deployment')
IMAGES={'overview.png':'empty','health.png':'empty','supervised-health.png':'research',
        'protected-paper.png':'protected','approval-preview.png':'approval','deployment-pause.png':'deployment'}

def digest(path):
    hasher=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):hasher.update(chunk)
    return 'sha256:'+hasher.hexdigest()

def require_artifact(folder,name,expected):
    folder=Path(folder)
    if not folder.is_absolute() or '..' in folder.parts:raise ValueError('Absolute canonical evidence folder required')
    if (not isinstance(name,str) or not name or PurePath(name).is_absolute() or Path(name).name!=name
            or name in ('.','..') or '/' in name or '\\' in name):raise ValueError('Local basename evidence reference required')
    if not isinstance(expected,str):raise ValueError('Recorded artifact commitment required')
    expected=expected if expected.startswith('sha256:') else 'sha256:'+expected
    if not re.fullmatch(r'sha256:[0-9a-f]{64}',expected):raise ValueError('Recorded artifact commitment required')
    path=folder/name
    try:
        for part in (*reversed(path.parents),path):
            info=part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise ValueError('Linked evidence forbidden')
        if not stat.S_ISREG(info.st_mode) or info.st_size>512*1024*1024:raise ValueError('Bounded regular evidence required')
        if digest(path)!=expected:raise ValueError('Recorded artifact bytes changed')
    except OSError:raise ValueError('Required evidence missing or inaccessible') from None
    return path

def require_sequence(rows,expected,*,key='name'):
    if [row.get(key) for row in rows]!=list(expected):raise ValueError('Authoritative coverage sequence mismatch')

def publish_retention_manifest(target,manifest,index,required,*,repository_root=None):
    """Verify the explicit required index and all retained bytes before acceptance."""
    target=Path(target);manifest=Path(manifest)
    repository_root=Path(repository_root) if repository_root is not None else target.parent
    by_ref={row['original_ref']:row for row in index}
    if len(by_ref)!=len(index) or len({row['retained_file'] for row in index})!=len(index):
        raise ValueError('Duplicate retained evidence reference')
    for reference,expected in required.items():
        row=by_ref.get(reference)
        if row is None or row['original_sha256']!=expected:raise ValueError('Required evidence missing from retention index')
    for row in index:
        relative=Path(row['retained_file'])
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid retained evidence reference')
        require_artifact(target/relative.parent,relative.name,row['retained_sha256'])
    files={file.relative_to(repository_root).as_posix():digest(file)
        for file in sorted(target.rglob('*')) if file.is_file()}
    manifest.write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8',newline='\n')
    if json.loads(manifest.read_bytes())!=files:raise ValueError('Published evidence manifest differs')
    for reference,expected in files.items():
        if digest(repository_root/reference)!=expected:
            raise ValueError('Retained evidence changed during manifest publication')
    return files

def require_native_lists(report,kind):
    require_sequence(report['commands'],NATIVE_COMMANDS[kind]);require_sequence(report['scenarios'],NATIVE_SCENARIOS[kind])
    for key,list_name in [('command_count','commands'),('scenario_count','scenarios')]:
        if key in report and report[key]!=len(report[list_name]):raise ValueError('Native counter differs from actual list')
    if not all(row.get('passed') is True and row.get('tree_reaped') is True for row in report['commands']):
        raise ValueError('All native owned commands must pass')
    if not all(row.get('passed') is True or row.get('result')=='PASS' for row in report['scenarios']):
        raise ValueError('All named native scenarios must pass')

def require_browser_subject(report,*,identity,cases,assets):
    if (report['native_build_identity']!=identity or report['native_browser_assets']!='EXACT_INVENTORY_MATCH'
            or report['build_hashes']!=assets or report['expected_cases']!=list(cases)
            or len(report['browser_cases_observed'])!=len(cases) or len(set(report['browser_cases_observed']))!=len(cases)
            or set(report['browser_cases_observed'])!=set(cases)):
        raise ValueError('Authoritative browser/native subject differs')

def browser_cases(repo):
    source=(Path(repo)/'ui/qa/control-center.spec.ts').read_text(encoding='utf-8')
    cases=re.findall(r"test\('([^']+)',async\(\{page\}\)=>\{(.*?)(?=\ntest\(|\Z)",source,re.S)
    if len(cases)!=11 or len({title for title,body in cases})!=11:raise ValueError('Exact authoritative browser cases required')
    groups={profile:[] for profile in PROFILES}
    for title,body in cases:
        profiles=re.findall(r"await login\(page,'([^']+)'\)",body)
        if len(profiles)!=1 or profiles[0] not in groups:raise ValueError('Exact browser fixture binding required')
        groups[profiles[0]].append(title)
    if not all(groups.values()):raise ValueError('All authoritative browser profiles required')
    return [title for title,body in cases],groups

def specs(suites):
    for suite in suites:
        yield from suite.get('specs',[])
        yield from specs(suite.get('suites',[]))

def validate_primary_artifacts(repo,revision,source,full,ui_root,ui,frontend_root,frontend,build_root,build,native_roots,reports,denial_root,denial,browser_launcher):
    from application.qualification import FOCUSED,discover_suites,parse_result
    from dataclasses import asdict
    from application.platform.distribution import verify_distribution
    verified={}
    project=repo.parent.parent
    def verify(folder,name,expected):
        path=require_artifact(folder,name,expected)
        verified[path.relative_to(project).as_posix()]=expected if expected.startswith('sha256:') else 'sha256:'+expected
        return path
    def snapshot(folder,name,data):
        path=Path(folder)/name
        raw=path.read_bytes()
        if json.loads(raw)!=data:raise ValueError('Loaded report changed before retention')
        verify(folder,name,'sha256:'+hashlib.sha256(raw).hexdigest())
    snapshot(source,'qualification.json',full);snapshot(ui_root,'ui-qualification.json',ui)
    snapshot(frontend_root,'ui-qualification.json',frontend);snapshot(build_root,'build-result.json',build)
    for kind,filename in [('smoke','native-smoke.json'),('research','native-selected-research.json'),('cloud','native-S14.json'),('restore','native-recovery.json')]:
        snapshot(native_roots[kind],filename,reports[kind])
    snapshot(denial_root,'native-service-denial.json',denial)
    identity=verify_distribution(build_root/'dist/R7')
    if identity!=build['identity'] or identity['executable_revision']!=revision:raise ValueError('Current native identity changed')
    inventory=discover_suites(repo)
    if full['inventory']!=[dict(suite=s.name,files=len(s.test_files)) for s in inventory]:raise ValueError('Authoritative test file inventory changed')
    expected=[('phase_1',name,pattern) for name,pattern in FOCUSED]+[('phase_2',s.name,'test_*.py') for s in inventory]
    actual=[(c['phase'],c['suite'],c['pattern']) for c in full['commands']]
    if actual!=expected or full['tests_run']!=sum(c['tests_run'] for c in full['commands']):raise ValueError('Complete source sequence/count mismatch')
    for index,c in enumerate(full['commands'],1):
        name=f'{index:03d}-{c["phase"]}-{c["suite"].replace("/","-")}.log'
        if c['log']!=name:raise ValueError('Source log reference mismatch')
        log=verify(source,name,c['log_sha256'])
        parsed=asdict(parse_result(log.read_text(encoding='utf-8'),returncode=c['returncode']))
        if any(c[key]!=value for key,value in parsed.items()):raise ValueError('Source log outcome differs from report')
        if c['tests_passed']!=c['tests_run'] or c['source_after']!=dict(revision=revision,worktree='CLEAN'):
            raise ValueError('Source count/current revision mismatch')
    archive=Path(build['archive'])
    if str(archive)!=archive.name:raise ValueError('Native archive basename required')
    verify(build_root,archive.name,build['archive_sha256'])
    distribution=json.loads((build_root/'dist/R7/distribution.json').read_bytes())
    if build['files']!=len(distribution['files']):raise ValueError('Native build file count differs from actual manifest')
    assets={name[len('_internal/ui/'):]:value for name,value in distribution['files'].items() if name.startswith('_internal/ui/')}
    cases,groups=browser_cases(repo)
    require_browser_subject(ui,identity=identity,cases=cases,assets=assets)
    current_assets={}
    dist=repo/'ui/dist'
    require_artifact(dist,'index.html',assets['index.html'])
    for entry in sorted(dist.rglob('*')):
        info=entry.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise ValueError('Linked current browser build forbidden')
        if stat.S_ISREG(info.st_mode):current_assets[entry.relative_to(dist).as_posix()]=digest(entry)
        elif not stat.S_ISDIR(info.st_mode):raise ValueError('Regular current browser build required')
    if current_assets!=assets:raise ValueError('Current complete browser asset inventory changed')
    if ui['launcher_hash']!=digest(browser_launcher) or ui['original_spec_sha256']!=digest(repo/'ui/qa/control-center.spec.ts') or ui['original_config_sha256']!=digest(repo/'ui/playwright.config.ts'):
        raise ValueError('Actual browser launcher/spec/config identity changed')
    if frontend['launcher_hash']!=digest(browser_launcher.parent/'s14_feedback_ui_frontend.py'):
        raise ValueError('Actual frontend launcher identity changed')
    for name in ['ui/package-lock.json','ui/src/api.generated.ts','contracts/control_api_v0_2.openapi.json']:
        if ui['input_hashes'].get(name)!=digest(repo/name) or frontend['input_hashes'].get(name)!=digest(repo/name):raise ValueError('Authoritative UI input changed')
    expected_frontend=[['npm','--prefix','ui',*args] for args in [['ci','--ignore-scripts','--no-fund'],['run','types:check'],['run','typecheck'],['test'],['run','build']]]
    if [c['command'] for c in frontend['commands']]!=expected_frontend or ui['frontend_commands']!=frontend['commands']:
        raise ValueError('Authoritative frontend sequence mismatch')
    for index,c in enumerate(frontend['commands']):
        if not c['passed'] or not c['tree_reaped'] or c['exit_code']!=0:raise ValueError('Frontend command did not pass')
        log=verify(frontend_root,c['log'],c['log_sha256'])
        if index==3:
            matches=re.search(r'Tests\s+(\d+) passed',log.read_text(encoding='utf-8'))
            if not matches or int(matches[1])!=c['tests_passed'] or c['tests_passed']!=15:raise ValueError('Actual UI test count differs')
    if frontend['build_hashes']!=assets:raise ValueError('Frontend/native asset bytes differ')
    require_sequence(ui['commands'],PROFILES,key='profile')
    observed=[]
    for row in ui['commands']:
        profile=row['profile']
        if row['expected_cases']!=groups[profile] or row['observed_cases']!=groups[profile] or row['build_inventory_after']!='MATCH':raise ValueError('Actual profile coverage/build check differs')
        verify(ui_root,row['log'],row['log_sha256'])
        verify(ui_root,profile+'.config.mjs',row['config_sha256'])
        result_file=verify(ui_root,profile+'-browser-results.json',row['browser_results_sha256'])
        result=json.loads(result_file.read_bytes());entries=list(specs(result['suites']))
        if [e['title'] for e in entries]!=groups[profile] or result['stats']!=row['browser_stats'] or result.get('errors'):
            raise ValueError('Actual browser result differs from report')
        if not all(e['ok'] and len(e['tests'])==1 and e['tests'][0]['status']=='expected' and len(e['tests'][0]['results'])==1 and e['tests'][0]['results'][0]['status']=='passed' for e in entries):
            raise ValueError('Actual browser outcomes not complete PASS')
        observed.extend(row['observed_cases'])
    if observed!=ui['browser_cases_observed']:raise ValueError('Browser observed list differs from actual profiles')
    if set(ui['screenshot_hashes'])!=set(IMAGES):raise ValueError('Complete required screenshots missing')
    for name in IMAGES:verify(ui_root,name,ui['screenshot_hashes'][name])
    for kind,report in reports.items():
        if kind=='research':
            log=verify(native_roots[kind],'selected-native-worker.log',report['log_sha256'])
            if json.loads(log.read_bytes())!=report['worker_result']:raise ValueError('Research native output mismatch')
            continue
        require_native_lists(report,kind)
        for index,c in enumerate(report['commands'],1):
            name=(f'{index:02d}-' if kind=='cloud' else '')+c['name']+'.log'
            if c['log']!=name:raise ValueError('Native command log reference mismatch')
            log=verify(native_roots[kind],name,c['log_sha256'])
            if 'expected_exit_code' in c and c['exit_code']!=c['expected_exit_code']:raise ValueError('Native exit disposition mismatch')
            if kind=='cloud' and json.loads(log.read_bytes())!=c['result']:raise ValueError('Cloud native observed output differs')
    require_native_lists(denial,'denial')
    for c in denial['commands']:
        if c['log']!=c['name']+'.log':raise ValueError('Native denial log reference mismatch')
        verify(denial_root,c['log'],c['log_sha256'])
    return dict(source_commands=len(expected),native_scenarios=sum(len(r['scenarios']) for k,r in reports.items() if k!='research')+1+len(denial['scenarios']),
        native_commands=sum(len(r['commands']) for k,r in reports.items() if k!='research')+1+len(denial['commands']),
        required_artifacts='EXISTENCE_AND_RECORDED_HASH_VERIFIED',browser_binding='ACTUAL_SPEC_CONFIG_LAUNCHER_NATIVE_ASSETS_RESULTS_AND_SCREENSHOTS',
        verified_artifact_hashes=verified)
