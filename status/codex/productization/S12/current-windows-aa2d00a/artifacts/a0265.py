"""Local, exact-clean fresh ZIP install and installed offline authoring proof."""
from contextlib import nullcontext
from datetime import datetime,timezone
import hashlib,io,json,os,re,stat,sys,zipfile
from pathlib import Path,PurePosixPath
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(BASE),str(BASE.parent)]
from application.qualification import revision_fact
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.paper.inventory import current_target,fixed_profile
from application.paper.producer import _guard
from run_current_checkpoint import command
from verify_native_product import verify
from local_windows_qualification_awake import awake_request
from application.platform.supervision import _local_path
from application.datasets.catalog import read_local,decode
from application.cloud.manifest import parse_manifest,verify_payload,canonical_bytes
from strategy import parse_strategy_definition
from strategy.v02.capabilities import build_capability_snapshot

def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

def require_version(kit,expected):
    if read_local(kit,'version.json',1024*1024)!=expected:raise ValueError('Delivered version metadata changed')

def archive_subject(build,revision,facts):
    raw=read_local(build,'build-result.json',65536);result=decode(raw)
    name='r7-product-0.2.0-windows-'+revision[:7]+'.zip'
    if (result.get('archive')!=name or result.get('identity')!=facts
            or result.get('source',{}).get('revision')!=revision
            or result.get('source',{}).get('worktree')!='CLEAN'
            or result.get('source',{}).get('implementation_hash')!=facts['implementation_hash']):
        raise ValueError('Fixed build archive identity required')
    archive=build/name;_local_path(archive)
    if archive.stat().st_size>512*1024*1024:raise ValueError('Bounded archive required')
    packed=read_local(build,name,512*1024*1024)
    if sha(packed)!='sha256:'+result['archive_sha256']:raise ValueError('Actual ZIP checksum differs')
    return archive,raw,packed

def validate_authoring(kit,export,authored):
    raw=read_local(kit,'capabilities.json',1024*1024)
    snapshot=build_capability_snapshot()
    if (export.get('status')!='CAPABILITIES_EXPORTED' or export.get('execution_evidence')!='NOT_RUN'
            or export.get('snapshot_hash')!=sha(raw) or raw!=snapshot.canonical_json.encode()):
        raise ValueError('Actual current native capability bytes required')
    if (authored.get('status')!='AUTHORING_PACKAGE_CREATED' or authored.get('execution_evidence')!='NOT_RUN'
            or authored.get('financial_authority')!='NONE' or authored.get('capability_snapshot_hash')!=sha(raw)):
        raise ValueError('Actual offline author response required')
    folder=kit/'engineering-package';manifest_raw=read_local(folder,'manifest.json',256*1024);manifest=parse_manifest(manifest_raw)
    if (manifest.manifest_hash!=authored.get('manifest_hash') or manifest.submission_id!=authored.get('submission_id')
            or manifest.strategy_content_hash!=authored.get('strategy_content_hash')
            or manifest.raw.get('capability_snapshot_hash')!=sha(raw) or manifest_raw!=canonical_bytes(manifest.raw)):
        raise ValueError('Actual emitted manifest differs')
    payloads={}
    for spec in manifest.payloads:
        payload=read_local(folder,spec.relative_path,spec.limit);verify_payload(spec,payload)
        payloads[spec.relative_path]=sha(payload)
        if spec.role=='strategy_definition':
            parsed=parse_strategy_definition(payload)
            if parsed.content_hash!=manifest.strategy_content_hash:raise ValueError('Actual E2 strategy differs')
    if (payloads!=authored.get('payload_hashes') or
            {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}!={'manifest.json',*payloads}):
        raise ValueError('Complete author payload closure required')
    return {p.relative_to(kit).as_posix():sha(p.read_bytes()) for p in kit.rglob('*') if p.is_file()}

def run(revision):
    if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Exact committed source required')
    revision_fact(ROOT,revision,True)
    build=BASE/('build-'+revision[:7]);source=build/'dist/R7'
    facts=verify_distribution(source);profile=fixed_profile(current_target())
    _guard(ROOT,revision,source,facts,profile)
    output=BASE/('portable-'+revision[:7]+'-first')
    installed=PROJECT/'installations'/('windows-'+revision[:7]+'-clean')
    if output.exists() or installed.exists():raise ValueError('Fresh portable directories required')
    create_private_directory(output)
    report=dict(revision=revision,passed=False,identity=facts,started_at=datetime.now(timezone.utc).isoformat(),
        additional_provider_requests=0,cumulative_public_requests=8,cumulative_public_responses=8,
        credentials='NONE',private_requests=0,provider_mutation=0,capital='NONE',github_compute='NOT_USED',
        ordinary_paper='NOT_INFERRED',master='IN_PROGRESS',helper_hash=sha(Path(__file__).read_bytes()))
    with awake_request() if os.name=='nt' else nullcontext() as awake:
        try:
            archive,build_metadata,packed=archive_subject(build,revision,facts);digest=sha(packed)
            _local_path(installed)
            if not installed.resolve().is_relative_to(PROJECT.resolve()):raise ValueError('Local installation containment required')
            if not installed.parent.exists():create_private_directory(installed.parent)
            _local_path(installed.parent)
            with zipfile.ZipFile(io.BytesIO(packed)) as zip:
                infos=zip.infolist();seen=set();total=0
                if not 1<=len(infos)<=4096:raise ValueError('Bounded ZIP inventory required')
                for item in infos:
                    path=PurePosixPath(item.filename);parts=path.parts
                    if (not parts or parts[0]!='R7' or path.is_absolute() or
                            any(part in ('','.','..') or ':' in part or '\\' in part for part in parts)
                            or stat.S_ISLNK(item.external_attr>>16)):
                        raise ValueError('Unsafe ZIP member')
                    key=item.filename.casefold()
                    if key in seen:raise ValueError('Duplicate ZIP member')
                    seen.add(key);total+=item.file_size
                if total>512*1024*1024:raise ValueError('ZIP uncompressed byte bound exceeded')
                create_private_directory(installed)
                for item in infos:
                    target=installed.joinpath(*PurePosixPath(item.filename).parts[1:]);_local_path(target)
                    if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with target.open('xb') as destination:destination.write(zip.read(item))
            if verify_distribution(installed)!=facts:raise ValueError('Fresh installed identity differs')
            original={p.relative_to(source).as_posix():sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}
            extracted={p.relative_to(installed).as_posix():sha(p.read_bytes()) for p in installed.rglob('*') if p.is_file()}
            if original!=extracted:raise ValueError('Fresh installed complete bytes differ')
            report.update(archive_ref=archive.relative_to(PROJECT).as_posix(),archive_hash=digest,
                installation_ref=installed.relative_to(PROJECT).as_posix(),extracted_files=len(extracted),
                uncompressed_bytes=total,complete_bytes_identical=True,copied_configuration=False,copied_auth=False)
            if verify(installed,output/'first-run-smoke')!=0:raise ValueError('Actual fresh native smoke incomplete')
            smoke=json.loads((output/'first-run-smoke/native-smoke.json').read_bytes())
            if not smoke['passed'] or any(not row['tree_reaped'] for row in smoke['commands']):
                raise ValueError('Complete owned first-run proof required')
            report['first_run']=dict(passed=True,commands=len(smoke['commands']),scenarios=smoke['scenario_count'],
                native_path=smoke['product_path'],pythonpath=smoke['pythonpath'],auth='FRESH_NOT_CONFIGURED',
                runtime='NOT_STARTED',paper='NOT_STARTED')
            kit=output/'chat-authoring-kit';create_private_directory(kit)
            export=command([installed/'R7.exe','export-capabilities','--destination',kit/'capabilities.json'],output,'export-capabilities',60)
            for ref,name in [('docs/strategy/chat-authoring-kit-v0.2.md','README.md'),
                    ('docs/strategy/authoring-v0.2/README.md','authoring-reference.md'),
                    ('docs/strategy/authoring-v0.2/examples/four-hour/strategy.json','engineering-example-not-gpt.json')]:
                write_private_new(kit/name,(ROOT/ref).read_bytes())
            authored=command([installed/'R7.exe','author-package','--definition',kit/'engineering-example-not-gpt.json',
                '--destination',kit/'engineering-package','--submission-id','engineering-baseline-'+revision[:7],
                '--dataset-profile','okx-btc-4h','--validation-profile','diagnostic','--robustness-profile','diagnostic'],
                output,'author-engineering-example',60)
            report['authoring']=dict(capability_export=export,actual_package=authored,
                strategy_origin='ENGINEERING_BASELINE_NOT_GPT',research_execution='NOT_RUN_IN_PORTABLE_SMOKE',
                software_or_financial_qualification='NOT_INFERRED')
            kit_closure=validate_authoring(kit,export,authored)
            version=dict(identity=facts,archive_hash=digest,capability_snapshot_hash=export['snapshot_hash'],
                strategy_origin='ENGINEERING_BASELINE_NOT_GPT',financial_authority='NONE',
                files=[dict(ref=p.relative_to(kit).as_posix(),hash=sha(p.read_bytes())) for p in sorted(kit.rglob('*')) if p.is_file()])
            version_bytes=(json.dumps(version,indent=2)+'\n').encode()
            write_private_new(kit/'version.json',version_bytes)
            require_version(kit,version_bytes)
            if ({p.relative_to(kit).as_posix():sha(p.read_bytes()) for p in kit.rglob('*') if p.is_file() and p.name!='version.json'}!=kit_closure
                    or validate_authoring(kit,export,authored)!={**kit_closure,'version.json':sha(version_bytes)}):
                raise ValueError('Delivered author kit changed')
            archive_after,metadata_after,packed_after=archive_subject(build,revision,facts)
            if archive_after!=archive or metadata_after!=build_metadata or sha(packed_after)!=digest:
                raise ValueError('Final archive or metadata changed')
            if verify_distribution(installed)!=facts:raise ValueError('Installed bytes changed after smoke/authoring')
            _guard(ROOT,revision,source,facts,profile)
            require_version(kit,version_bytes)
            report['passed']=True
        except BaseException as error:report.update(passed=False,error_type=type(error).__name__)
        finally:
            report['finished_at']=datetime.now(timezone.utc).isoformat()
            revision_fact(ROOT,revision,True);report['source_unchanged']=True
    write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({key:value for key,value in report.items() if key not in ('authoring',)}),flush=True)
    return 0 if report['passed'] else 2

if __name__=='__main__':raise SystemExit(run(*sys.argv[1:]))
