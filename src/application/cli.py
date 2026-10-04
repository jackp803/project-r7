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
    parser = argparse.ArgumentParser(prog="r7")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Local hardware diagnostics")
    doctor.add_argument("--hardware", action="store_true", required=True)
    doctor.add_argument("--data-root", type=Path, required=True)
    doctor.add_argument("--json", action="store_true")
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
    args = parser.parse_args(argv)
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
            return serve(config, desktop=args.desktop)
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
    except Exception:
        print('R7: local configuration or startup validation failed', file=sys.stderr)
        return 2
