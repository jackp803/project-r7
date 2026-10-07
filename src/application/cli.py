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
    profile.add_argument('--instance-id', default=None)
    profile.add_argument('--port', type=int, default=8765)
    enroll = commands.add_parser('enroll-owner', help='Enroll first local owner using hidden terminal input')
    enroll.add_argument('--config', type=Path, required=True)
    enroll.add_argument('--username', required=True)
    server = commands.add_parser('serve', help='Start authenticated loopback Control Center')
    server.add_argument('--config', type=Path, required=True)
    server.add_argument('--desktop', action='store_true')
    worker = commands.add_parser('research-worker', help='Supervise one resource-admitted research child at a time')
    worker.add_argument('--config', type=Path, required=True)
    worker.add_argument('--once', action='store_true')
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
    job = commands.add_parser('_research-job', help=argparse.SUPPRESS)
    job.add_argument('--config', type=Path, required=True)
    job.add_argument('--run-id', required=True)
    job.add_argument('--generation', type=int, required=True)
    job.add_argument('--expected-config-hash')
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
    if args.command == 'queue-research-feedback':
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
                operation=queue_feedback(service,args.run_id,performance_opt_in=args.performance_opt_in)
        print(json.dumps(dict(status='FEEDBACK_QUEUED',operation_id=operation,cloud='NOT_CONTACTED')))
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
                from application.cloud.publisher import Publisher
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
                                from application.cloud.publisher import PublishSummary
                                summary=PublishSummary(**{name:value+getattr(second,name) for name,value in asdict(summary).items()})
                result = dict(status='COMPLETE' if not summary.unavailable and not summary.conflicts else 'INCOMPLETE', **asdict(summary))
                code = 0 if result['status'] == 'COMPLETE' else 2
        except CloudError as error:
            result, code = dict(status=error.code, reason=error.reason), 2
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
    if args.command == 'research-worker':
        from application.research.worker import research_worker
        return research_worker(args.config, once=args.once)
    if args.command == '_research-job':
        from application.research.worker import run_research_job
        result = run_research_job(args.config, args.run_id, args.generation, expected_config_hash=args.expected_config_hash)
        print(json.dumps(result))
        return 0 if result['status'] in ('COMPLETE', 'BLOCKED', 'CANCELED') else 2
    if args.command == 'init-profile':
        from application.entrypoints import initialize_profile
        result = initialize_profile(args.config, args.data_root,
                                    instance_id=args.instance_id or str(uuid.uuid4()), port=args.port)
        print(json.dumps(result, ensure_ascii=False))
        return 0
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
    except Exception:
        print('R7: local configuration or startup validation failed', file=sys.stderr)
        return 2
