"""Portable diagnostics and trusted local product entrypoints."""

import argparse
import json
from pathlib import Path
import sys
import uuid

from application.platform.resources import ResourcePolicy, inspect_hardware


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if getattr(sys, 'frozen', False) and argv and argv[0] == '_owned-process-bootstrap':
        from application.platform._process_bootstrap import main as bootstrap
        return bootstrap(argv[1:])
    if argv and argv[0] == '_auth-status-probe':
        from application.platform._loopback_probe import main as auth_status_probe
        return auth_status_probe(argv[1:])
    parser = argparse.ArgumentParser(prog="r7")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Local hardware diagnostics")
    doctor.add_argument("--hardware", action="store_true", required=True)
    doctor.add_argument("--data-root", type=Path, required=True)
    doctor.add_argument("--json", action="store_true")
    tunnel=commands.add_parser('plan-ssh-tunnel',help='Display an operator SSH loopback-forward command without connecting')
    tunnel.add_argument('--host',required=True)
    tunnel.add_argument('--username',required=True)
    tunnel.add_argument('--port',type=int,default=8765)
    tunnel.add_argument('--ssh-port',type=int,default=22)
    access=commands.add_parser('probe-control-access',help='Check public loopback control status without credentials')
    access.add_argument('--port',type=int,required=True)
    access.add_argument('--expected-namespace',choices=('LOCAL_RESEARCH','FIXTURE'),default='LOCAL_RESEARCH')
    access.add_argument('--deadline-seconds',type=int,default=4)
    profile = commands.add_parser('init-profile', help='Create explicit non-trading local settings')
    profile.add_argument('--config', type=Path, required=True)
    profile.add_argument('--data-root', type=Path, required=True)
    profile.add_argument('--cloud-root', type=Path)
    profile.add_argument('--instance-id', default=None)
    profile.add_argument('--port', type=int, default=8765)
    profile.add_argument('--execution-mode', choices=('LOCAL_RESEARCH','FIXTURE'), default='LOCAL_RESEARCH')
    profile.add_argument('--enable-paper-runtime',action='store_true',help='Select ordinary Paper process capability; separate policy/workflow/qualification still required')
    fixture = commands.add_parser('prepare-fixture', help='Generate fresh labeled synthetic inputs for explicit isolated FIXTURE mode')
    fixture.add_argument('--config', type=Path, required=True)
    fixture.add_argument('--scenario', choices=('positive','oos-loss','insufficient-oos'), required=True)
    from application.fixtures.temporal import CASES as fixture_temporal_cases
    fixture.add_argument('--temporal-case',choices=fixture_temporal_cases,default='none',
        help='Closed isolated synthetic expiry inputs; no result or ordinary authority')
    from application.fixtures.faults import CASES as fixture_paper_cases
    fixture.add_argument('--paper-case',choices=fixture_paper_cases,default='normal',
        help='Closed sealed synthetic recovery market inputs; no terminal state or authority')
    setup = commands.add_parser('configure-research', help='Select explicit local research inputs while all owners are stopped')
    setup.add_argument('--config', type=Path, required=True)
    setup.add_argument('--selection-profile', type=Path, required=True)
    market_setup=commands.add_parser('configure-market-data',help='Select keyless BTC public reads while all owners are stopped; grants no Paper eligibility')
    market_setup.add_argument('--config',type=Path,required=True)
    market_setup.add_argument('--selection-profile',type=Path,required=True)
    public_data=commands.add_parser('acquire-public-data',help='Acquire bounded keyless OKX BTC 4H candles and realized funding; counts actual public requests')
    public_data.add_argument('--config',type=Path,required=True)
    public_data.add_argument('--dataset-id',required=True)
    public_data.add_argument('--start',required=True)
    public_data.add_argument('--end',required=True)
    paper_setup = commands.add_parser('configure-paper', help='Select explicit local Paper policies while all owners are stopped')
    paper_setup.add_argument('--config', type=Path, required=True)
    paper_setup.add_argument('--selection-profile', type=Path, required=True)
    paper_worker = commands.add_parser('paper-worker', help='Run independent selected Paper owner; ordinary startup requires complete native qualification')
    paper_worker.add_argument('--config', type=Path, required=True)
    paper_worker.add_argument('--maximum-ticks', type=int)
    fixture_publish=commands.add_parser('publish-fixture-outbox',help='Stage actual FIXTURE receipts and reports in the selected synthetic local folder')
    fixture_publish.add_argument('--config',type=Path,required=True)
    fixture_publish.add_argument('--limit',type=int,default=10)
    enroll = commands.add_parser('enroll-owner', help='Enroll first local owner using hidden terminal input')
    enroll.add_argument('--config', type=Path, required=True)
    enroll.add_argument('--username', required=True)
    server = commands.add_parser('serve', help='Start authenticated loopback Control Center')
    server.add_argument('--config', type=Path, required=True)
    server.add_argument('--desktop', action='store_true')
    worker = commands.add_parser('research-worker', help='Supervise one resource-admitted research child at a time')
    worker.add_argument('--config', type=Path, required=True)
    worker.add_argument('--once', action='store_true')
    worker.add_argument('--job-timeout-seconds',type=int,default=900,
        help='Owned research child deadline in seconds (1..900; default 900)')
    run_product=commands.add_parser('run-product',help='Run explicitly selected local services and schedules with one headless owner; changes no host settings')
    run_product.add_argument('--config',type=Path,required=True)
    run_product.add_argument('--operations-profile',type=Path,required=True)
    run_product.add_argument('--maximum-cycles',type=int,help='Bounded verification only; omitted for normal continuous operation')
    product_status=commands.add_parser('product-status',help='Read actual local service heartbeats without granting financial permission')
    product_status.add_argument('--config',type=Path,required=True)
    product_child=commands.add_parser('_product-service',help=argparse.SUPPRESS)
    product_child.add_argument('--config',type=Path,required=True)
    product_child.add_argument('--role',choices=('control','research','runtime'),required=True)
    product_child.add_argument('--expected-config-hash',required=True)
    market_child=commands.add_parser('_paper-market-acquire',help=argparse.SUPPRESS)
    market_child.add_argument('--config',type=Path,required=True)
    for name in ('runtime-token','attempt-id','request-hash','expected-config-hash','selection-hash'):
        market_child.add_argument('--'+name,required=True)
    boundary_check=commands.add_parser('_paper-native-boundary-check',help=argparse.SUPPRESS)
    boundary_check.add_argument('--config',type=Path,required=True)
    stale_check=commands.add_parser('_paper-native-stale-check',help=argparse.SUPPRESS)
    stale_check.add_argument('--config',type=Path,required=True)
    stale_check.add_argument('--run-id',required=True)
    stop_service=commands.add_parser('stop-product',help='Request cooperative stop of the current local owner; does not assert flat exposure')
    stop_service.add_argument('--config',type=Path,required=True)
    from application.platform.supervision import PROCESS_ROLES
    stop_service.add_argument('--role',choices=PROCESS_ROLES,required=True)
    for name, description in (('plan-services','Export an exact native Ubuntu control/research plan without installation'),
                              ('guarded-service','Start an exact native Ubuntu control/research subject under its dedicated account'),
                              ('install-services','Preview or explicitly apply bounded native Ubuntu service files'),
                              ('uninstall-services','Preview or explicitly remove verified owned native Ubuntu service files')):
        service = commands.add_parser(name, help=description)
        service.add_argument('--config', type=Path, required=True)
        service.add_argument('--expected-revision', required=True)
        service.add_argument('--expected-build-hash', required=True)
        service.add_argument('--expected-config-hash', required=True)
        service.add_argument('--expected-memory-bytes', type=int, required=True)
        service.add_argument('--service-user', required=True)
        if name == 'plan-services':
            service.add_argument('--output', type=Path, required=True)
        elif name == 'guarded-service':
            service.add_argument('--role', choices=('control','research'), required=True)
        else:
            service.add_argument('--apply',action='store_true')
            service.add_argument('--operation-hash')
    author = commands.add_parser('author-package', help='Create actual offline JSON files through E2')
    author.add_argument('--definition', type=Path, required=True)
    author.add_argument('--destination', type=Path, required=True)
    author.add_argument('--submission-id', required=True)
    author.add_argument('--package-version', choices=('0.1','0.2'), default='0.2')
    author.add_argument('--notes', type=Path)
    author.add_argument('--dataset-profile', default='unselected')
    author.add_argument('--validation-profile', default='unselected')
    author.add_argument('--robustness-profile', default='unselected')
    author.add_argument('--valid-from')
    author.add_argument('--valid-until')
    capabilities = commands.add_parser('export-capabilities', help='Write current implementation availability, without claiming execution evidence')
    capabilities.add_argument('--destination', type=Path, required=True)
    feedback = commands.add_parser('queue-research-feedback', help='Queue sanitized actual owner feedback locally; performance defaults to opt-out')
    feedback.add_argument('--config', type=Path, required=True)
    feedback.add_argument('--run-id', required=True)
    feedback.add_argument('--namespace', choices=('LOCAL_RESEARCH','FIXTURE'), default='LOCAL_RESEARCH')
    feedback.add_argument('--performance-opt-in', action='store_true')
    candidate_index = commands.add_parser('queue-candidate-index', help='Queue the actual completed candidate evidence index; no financial authority')
    candidate_index.add_argument('--config', type=Path, required=True)
    candidate_index.add_argument('--run-id', required=True)
    candidate_index.add_argument('--namespace', choices=('LOCAL_RESEARCH','FIXTURE'), default='LOCAL_RESEARCH')
    for name, description in (
        ('cloud-pull', 'Copy a bounded author-input batch from the explicitly selected R7 root'),
        ('cloud-import-dataset', 'Seal downloaded dataset bytes locally without decoding sealed OOS prices'),
        ('cloud-publish-outbox', 'Publish durable receipt outbox items with exact remote readback')):
        bridge = commands.add_parser(name, help=description)
        bridge.add_argument('--config', type=Path, required=True)
        bridge.add_argument('--bridge-profile', type=Path, required=True)
        if name == 'cloud-publish-outbox':
            bridge.add_argument('--limit', type=int, default=10)
        elif name == 'cloud-import-dataset':
            bridge.add_argument('--dataset-id', required=True)
            bridge.add_argument('--revision', required=True)
    for name, description in (
        ('backup-databases', 'Create a private local SQLite snapshot after native owners stop'),
        ('verify-database-backup', 'Verify private snapshot bytes and schemas without restoration')):
        backup = commands.add_parser(name, help=description)
        backup.add_argument('--config', type=Path, required=True)
        backup.add_argument('--destination', type=Path, required=True)
    restore = commands.add_parser('restore-databases', help='Stage verified database copies into a new private inhibited generation')
    restore.add_argument('--config', type=Path, required=True)
    restore.add_argument('--backup', type=Path, required=True)
    restore.add_argument('--destination', type=Path, required=True)
    for name, description in (
        ('backup-product-data', 'Create a private complete supported local product-data bundle'),
        ('verify-product-backup', 'Verify a private product-data bundle without restoration'),
        ('restore-product-data', 'Stage product data into a fresh inhibited local generation')):
        product = commands.add_parser(name, help=description)
        product.add_argument('--config', type=Path, required=True)
        product.add_argument('--destination', type=Path, required=True)
        if name == 'restore-product-data':
            product.add_argument('--backup', type=Path, required=True)
    upgrade = commands.add_parser('preflight-product-upgrade', help='Check a verified backup against this release without restoration or activation')
    upgrade.add_argument('--config',type=Path,required=True)
    upgrade.add_argument('--backup',type=Path,required=True)
    upgrade.add_argument('--timeout-seconds',type=int,default=30)
    job = commands.add_parser('_research-job', help=argparse.SUPPRESS)
    job.add_argument('--config', type=Path, required=True)
    job.add_argument('--run-id', required=True)
    job.add_argument('--generation', type=int, required=True)
    job.add_argument('--expected-config-hash')
    observe=commands.add_parser('_paper-release-observe',help=argparse.SUPPRESS)
    observe.add_argument('--config',type=Path,required=True)
    observe.add_argument('--receipt-ref',required=True)
    observe.add_argument('--mode',choices=('software','management','runtime'),required=True)
    observe.add_argument('--runtime-token')
    args = parser.parse_args(argv)
    if args.command=='plan-ssh-tunnel':
        from application.platform.ssh_access import plan_ssh_tunnel
        print(json.dumps(plan_ssh_tunnel(args.host,args.username,api_port=args.port,ssh_port=args.ssh_port)))
        return 0
    if args.command=='probe-control-access':
        from application.platform.ssh_access import probe_loopback_auth_status
        result=probe_loopback_auth_status(args.port,expected_namespace=args.expected_namespace,deadline_seconds=args.deadline_seconds)
        print(json.dumps(result))
        return 0 if result['status']=='PUBLIC_AUTH_STATUS_AVAILABLE' else 2
    if args.command in ('install-services','uninstall-services'):
        from application.platform.service_admin import manage_services
        result=manage_services(args.config,action='install' if args.command=='install-services' else 'uninstall',
            apply=args.apply,operation_hash=args.operation_hash,expected_revision=args.expected_revision,
            expected_build_hash=args.expected_build_hash,expected_config_hash=args.expected_config_hash,
            service_user=args.service_user,expected_memory_bytes=args.expected_memory_bytes)
        print(json.dumps(result,ensure_ascii=False))
        return 0 if result['status'] in ('DRY_RUN','ALREADY_INSTALLED','FILES_INSTALLED','FILES_REMOVED') else 2
    if args.command in ('plan-services','guarded-service'):
        from application.platform.service_guard import export_service_plan, run_guarded_service
        expected=dict(expected_revision=args.expected_revision,expected_build_hash=args.expected_build_hash,
            expected_config_hash=args.expected_config_hash,service_user=args.service_user,expected_memory_bytes=args.expected_memory_bytes)
        if args.command == 'guarded-service':
            return run_guarded_service(args.config,role=args.role,**expected)
        print(json.dumps(export_service_plan(args.config,args.output,**expected)))
        return 0
    if args.command == 'acquire-public-data':
        from application.config import load_config,product_namespace
        from application.cloud.manifest import safe_component
        from application.datasets.catalog import utc
        from application.datasets.okx_public import acquire_okx_public_dataset
        from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
        from application.entrypoints import _outside_installation
        config=load_config(args.config);safe_component(args.dataset_id)
        _outside_installation(config.local_data_root)
        if product_namespace(config)!='LOCAL_RESEARCH': raise ValueError('Public data acquisition requires explicit LOCAL_RESEARCH config')
        with ProcessScopeLock('public-data:'+config.product_instance_id,lock_root=operational_lock_root(config)):
            result=acquire_okx_public_dataset(config.local_data_root/'datasets'/args.dataset_id,start=utc(args.start),end=utc(args.end))
        print(json.dumps(result,ensure_ascii=False))
        return 0 if result['status']=='DATASET_ACQUIRED' else 2
    if args.command == 'author-package':
        from application.cloud.authoring import emit_package
        from application.cloud.safe_files import read_bounded
        definition=read_bounded(args.definition.absolute().parent,args.definition.name,256*1024)
        notes=None if args.notes is None else read_bounded(args.notes.absolute().parent,args.notes.name,64*1024).decode('utf-8')
        tactical=args.valid_from is not None or args.valid_until is not None
        result=emit_package(definition,args.destination,submission_id=args.submission_id,package_version=args.package_version,notes=notes,
            requested_dataset_profile=args.dataset_profile,requested_validation_profile=args.validation_profile,requested_robustness_profile=args.robustness_profile,
            intent_class='TACTICAL_STRATEGY' if tactical else 'EVERGREEN_STRATEGY',
            validity={'from':args.valid_from,'until':args.valid_until} if tactical else None)
        print(json.dumps(result))
        return 0
    if args.command == 'export-capabilities':
        from strategy.v02.capabilities import build_capability_snapshot
        from application.cloud.safe_files import write_immutable
        from application.platform.supervision import _local_path
        destination=args.destination.absolute();_local_path(destination)
        if destination.exists():raise ValueError('Fresh capability artifact required')
        snapshot=build_capability_snapshot()
        write_immutable(destination.parent,destination.name,snapshot.canonical_json.encode('utf-8'))
        print(json.dumps(dict(status='CAPABILITIES_EXPORTED',snapshot_hash=snapshot.snapshot_hash,execution_evidence='NOT_RUN')))
        return 0
    if args.command in ('queue-research-feedback','queue-candidate-index'):
        from application.config import load_config
        from application.cloud.feedback import queue_feedback
        from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
        from application.research.service import ResearchService
        config=load_config(args.config)
        if not (config.local_data_root/'research.sqlite').is_file() or not config.database_path.is_file():
            raise ValueError('Actual existing research owner stores required')
        with ProcessScopeLock('research:'+config.product_instance_id,lock_root=operational_lock_root(config)):
            with ResearchService(local_root=config.local_data_root,database_path=config.local_data_root/'research.sqlite',
                                 registry_path=config.database_path,namespace=args.namespace,owner_id='feedback-'+config.product_instance_id) as service:
                if args.command=='queue-candidate-index':
                    from application.cloud.candidate_index import queue_candidate_index
                    operation=queue_candidate_index(service,args.run_id)
                else:
                    operation=queue_feedback(service,args.run_id,performance_opt_in=args.performance_opt_in)
        print(json.dumps(dict(status='CANDIDATE_INDEX_QUEUED' if args.command=='queue-candidate-index' else 'FEEDBACK_QUEUED',
            operation_id=operation,cloud='NOT_CONTACTED')))
        return 0
    if args.command in ('cloud-pull', 'cloud-import-dataset', 'cloud-publish-outbox'):
        from dataclasses import asdict
        from application.config import load_config
        from application.cloud.rclone_bridge import RcloneBridge, load_bridge_profile
        from application.cloud.protocol import CloudError
        from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
        try:
            config = load_config(args.config)
            bridge = RcloneBridge(load_bridge_profile(args.bridge_profile, config))
            if args.command == 'cloud-pull':
                with ProcessScopeLock('cloud:'+config.product_instance_id,lock_root=operational_lock_root(config)):
                    result = bridge.pull_once()
                code = 0
            elif args.command == 'cloud-import-dataset':
                with ProcessScopeLock('cloud:'+config.product_instance_id,lock_root=operational_lock_root(config)):
                    result = bridge.import_dataset(args.dataset_id,args.revision)
                code = 0
            else:
                if not 1 <= args.limit <= 100:
                    raise CloudError('BLOCKED', 'BRIDGE_PUBLICATION_BATCH_LIMIT')
                from application.cloud.bridge_transport import RcloneCloudTransport
                from application.cloud.publisher import Publisher, PublishSummary
                from application.intake.ledger import IntakeLedger
                # A stopped-owner snapshot must also fence this local DB writer.
                with ProcessScopeLock('cloud:' + config.product_instance_id, lock_root=operational_lock_root(config)):
                    with IntakeLedger(config.local_data_root/'intake.sqlite', instance_id=config.product_instance_id) as ledger:
                        summary = Publisher(ledger, RcloneCloudTransport(bridge)).flush(args.limit)
                    research=config.local_data_root/'research.sqlite'
                    if research.is_file():
                        from application.research.evidence import ResearchJournal
                        from application.cloud.feedback import flush_feedback
                        with ResearchJournal(research) as journal:
                            remaining=args.limit-summary.attempted
                            if remaining:
                                second=flush_feedback(journal,RcloneCloudTransport(bridge),limit=remaining)
                                summary=PublishSummary(**{name:value+getattr(second,name) for name,value in asdict(summary).items()})
                            remaining=args.limit-summary.attempted
                            if remaining:
                                from application.cloud.candidate_index import flush_candidate_indexes
                                candidates=flush_candidate_indexes(journal,RcloneCloudTransport(bridge),limit=remaining)
                                summary=PublishSummary(**{name:value+getattr(candidates,name) for name,value in asdict(summary).items()})
                    remaining=args.limit-summary.attempted
                    if remaining and config.database_path.is_file():
                        from application.platform.supervision import _local_path
                        from storage.paper_feedback import PaperFeedbackOutbox
                        from storage.paper_process import open_paper_process_journal
                        # Historical publication never attaches a runtime or
                        # renews its generation; use the existing E6 store.
                        _local_path(config.database_path)
                        with open_paper_process_journal(config.database_path,require_existing=True) as journal:
                            third=PaperFeedbackOutbox(journal).flush(RcloneCloudTransport(bridge),limit=remaining)
                            summary=PublishSummary(**{name:value+getattr(third,name) for name,value in asdict(summary).items()})
                result = dict(status='COMPLETE' if not summary.unavailable and not summary.conflicts else 'INCOMPLETE', **asdict(summary))
                code = 0 if result['status'] == 'COMPLETE' else 2
        except CloudError as error:
            result, code = dict(status=error.code, reason=error.reason), 2
        print(json.dumps(result))
        return code
    if args.command == 'preflight-product-upgrade':
        from application.config import load_config
        from application.platform.upgrade_preflight import preflight_product_upgrade,UpgradePreflightError
        try:
            result=preflight_product_upgrade(load_config(args.config),args.backup,
                config_path=args.config,timeout_seconds=args.timeout_seconds)
            code=0
        except UpgradePreflightError as error:
            result=dict(status='BLOCKED',reason_codes=[str(error)],financial_authority='NONE',
                database_mutations=0,owner_starts=0)
            code=2
        print(json.dumps(result))
        return code
    if args.command in ('backup-product-data','verify-product-backup','restore-product-data'):
        from application.config import load_config
        from application.platform.product_backup import create_product_backup,verify_product_backup,restore_product_backup
        config=load_config(args.config)
        if args.command=='restore-product-data':
            result=restore_product_backup(config,args.backup,args.destination,config_path=args.config)
        elif args.command=='backup-product-data':
            result=create_product_backup(config,args.destination,config_path=args.config)
        else:
            result=verify_product_backup(config,args.destination)
        print(json.dumps(result))
        return 0
    if args.command == 'restore-databases':
        from application.config import load_config
        from application.platform.database_restore import restore_database_backup
        result=restore_database_backup(load_config(args.config),args.backup,args.destination,config_path=args.config)
        print(json.dumps(result))
        return 0
    if args.command in ('backup-databases', 'verify-database-backup'):
        from application.config import load_config
        from application.platform.backup import create_database_backup, verify_database_backup
        config = load_config(args.config)
        result = (create_database_backup(config, args.destination, config_path=args.config)
                  if args.command == 'backup-databases' else verify_database_backup(config, args.destination))
        print(json.dumps(result))
        return 0
    if args.command == 'stop-product':
        from application.config import load_config
        from application.platform.service_stop import request_service_stop
        print(json.dumps(request_service_stop(load_config(args.config),args.role)))
        return 0
    if args.command=='run-product':
        from application.coordinator import run_product
        result=run_product(args.config,args.operations_profile,maximum_cycles=args.maximum_cycles)
        print(json.dumps(result))
        return 0 if result['status']=='STOPPED' and result['all_owned_trees_reaped'] and all(value.get('status') not in ('RESTART_BUDGET_EXHAUSTED','FAILED','FORCED_STOP') for value in result['roles'].values()) else 2
    if args.command=='_product-service':
        from application.coordinator import run_selected_service
        return run_selected_service(args.config,args.role,args.expected_config_hash)
    if args.command=='_paper-market-acquire':
        from application.paper.public_feed import run_market_acquire
        print(json.dumps(run_market_acquire(args.config,args.runtime_token,args.attempt_id,args.request_hash,
            args.expected_config_hash,args.selection_hash)))
        return 0
    if args.command=='_paper-native-boundary-check':
        from application.paper.native_boundary_checks import run_native_boundary_checks
        print(json.dumps(run_native_boundary_checks(args.config)))
        return 0
    if args.command=='_paper-native-stale-check':
        from application.paper.native_boundary_checks import run_native_stale_paper_check
        print(json.dumps(run_native_stale_paper_check(args.config,args.run_id)))
        return 0
    if args.command=='product-status':
        from application.config import load_config
        from application.platform.supervision import process_health,PROCESS_ROLES
        config=load_config(args.config)
        print(json.dumps(dict(roles={role:process_health(config,role) for role in PROCESS_ROLES},financial_authority='NONE',exposure_status='NOT_ASSERTED')))
        return 0
    if args.command == 'research-worker':
        from application.research.worker import research_worker
        return research_worker(args.config, once=args.once,job_timeout_seconds=args.job_timeout_seconds)
    if args.command == 'paper-worker':
        from application.paper.entrypoint import paper_worker
        return paper_worker(args.config, maximum_ticks=args.maximum_ticks)
    if args.command == '_research-job':
        from application.research.worker import run_research_job
        result = run_research_job(args.config, args.run_id, args.generation, expected_config_hash=args.expected_config_hash)
        print(json.dumps(result))
        return 0 if result['status'] in ('COMPLETE', 'BLOCKED', 'CANCELED') else 2
    if args.command=='_paper-release-observe':
        from application.paper.release_observation import observe_native_subject
        print(json.dumps(observe_native_subject(args.config,args.receipt_ref,mode=args.mode,runtime_token=args.runtime_token)))
        return 0
    if args.command == 'init-profile':
        from application.entrypoints import initialize_profile
        result = initialize_profile(args.config, args.data_root,
                                    instance_id=args.instance_id or str(uuid.uuid4()), port=args.port,
                                    cloud_root=args.cloud_root, execution_mode=args.execution_mode,
                                    paper_runtime_enabled=args.enable_paper_runtime)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if args.command == 'configure-research':
        from application.research.setup import configure_research
        print(json.dumps(configure_research(args.config, args.selection_profile), ensure_ascii=False))
        return 0
    if args.command=='configure-market-data':
        from application.paper.public_market import configure_market_data
        print(json.dumps(configure_market_data(args.config,args.selection_profile)))
        return 0
    if args.command == 'prepare-fixture':
        from application.fixtures.recipe import prepare_fixture
        print(json.dumps(prepare_fixture(args.config,args.scenario,temporal_case=args.temporal_case,paper_case=args.paper_case), ensure_ascii=False))
        return 0
    if args.command == 'configure-paper':
        from application.paper.setup import configure_paper
        print(json.dumps(configure_paper(args.config, args.selection_profile), ensure_ascii=False))
        return 0
    if args.command == 'publish-fixture-outbox':
        from application.fixtures.publication import publish_fixture_outbox
        result=publish_fixture_outbox(args.config,limit=args.limit)
        print(json.dumps(result))
        return 0 if result['status']=='LOCAL_STAGED' else 2
    if args.command in ('enroll-owner', 'serve'):
        from application.config import load_config
        from application.entrypoints import enroll_owner, serve
        config = load_config(args.config)
        if args.command == 'serve':
            return serve(config, desktop=args.desktop, config_path=args.config)
        print(json.dumps(enroll_owner(config, args.username), ensure_ascii=False))
        return 0
    hardware = inspect_hardware(args.data_root)
    policy = ResourcePolicy.conservative(hardware.physical_memory_bytes)
    result = hardware.to_dict()
    result["research"] = {
        "worker_count": policy.worker_count,
        "memory_soft_budget_bytes": policy.memory_soft_budget_bytes,
        "memory_enforcement": policy.memory_enforcement,
        "admission": policy.admission(available_memory_bytes=hardware.available_memory_bytes,
                                      disk_free_bytes=hardware.disk_free_bytes,
                                      disk_total_bytes=hardware.disk_total_bytes).__dict__,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    return 0


def _startup_diagnostic(error):
    """Fixed categories and source locations only; never exception text/args."""
    from application.cloud.protocol import CloudError
    from application.platform.scope_lock import ScopeBusy
    from application.paper.errors import NativePaperReleaseUnavailable,QUALIFICATION_DENIALS
    known_reasons={'PUBLICATION_FINALIZE_FAILED','PUBLICATION_STAGE_WRITE_FAILED',
        'PUBLICATION_STAGE_FLUSH_FAILED','PUBLICATION_PARENT_WRITE_FAILED',
        'ARTIFACT_READ_DENIED','ARTIFACT_MISSING','HARDLINK_ALIAS_FORBIDDEN','REPARSE_POINT_FORBIDDEN'}
    known_files={'cli.py','setup.py','safe_files.py','scope_lock.py','config.py',
        'distribution.py','local_owners.py','paths.py','resources.py','supervision.py'}
    result=dict(schema_version='r7-startup-diagnostic-v0.2',error_kind='VALIDATION' if isinstance(error,ValueError) else 'OTHER',
        reason_code='LOCAL_STARTUP_VALIDATION_FAILED',os_error=None,windows_error=None,source_location=None)
    seen=set()
    for _ in range(8):
        if error is None or id(error) in seen:break
        seen.add(id(error))
        if isinstance(error,ScopeBusy):result['error_kind']='OWNER_SCOPE_BUSY'
        if isinstance(error,NativePaperReleaseUnavailable) and type(error.reason_code) is str and error.reason_code in QUALIFICATION_DENIALS:
            result['reason_code']=error.reason_code
        if isinstance(error,CloudError) and type(error.reason) is str and error.reason in known_reasons:result['reason_code']=error.reason
        if isinstance(error,OSError):
            result['error_kind']='OS_FAILURE'
            for attribute,key in (('errno','os_error'),('winerror','windows_error')):
                value=getattr(error,attribute,None)
                if type(value) is int and 0<=value<2**31:result[key]=value
        frame=error.__traceback__
        for _ in range(32):
            if frame is None:break
            name=Path(frame.tb_frame.f_code.co_filename).name
            if name in known_files:result['source_location']=dict(file=name,line=frame.tb_lineno)
            frame=frame.tb_next
        error=error.__cause__
    return result


def run():
    """Sanitized executable boundary; argparse retains its ordinary exit codes."""
    try:
        if getattr(sys, 'frozen', False):
            from application.platform.distribution import verify_distribution
            verify_distribution(Path(sys.executable).resolve().parent)
        return main()
    except KeyboardInterrupt:
        print('R7: stopped', file=sys.stderr)
        return 130
    except Exception as error:
        print('R7: local configuration or startup validation failed', file=sys.stderr)
        print(json.dumps(_startup_diagnostic(error)),file=sys.stderr)
        return 2
