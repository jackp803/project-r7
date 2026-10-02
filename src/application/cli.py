"""Portable diagnostics; new operational commands are added by their owners."""

import argparse
import json
from pathlib import Path

from application.platform.resources import ResourcePolicy, inspect_hardware


def main(argv=None):
    parser = argparse.ArgumentParser(prog="r7")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Local hardware diagnostics")
    doctor.add_argument("--hardware", action="store_true", required=True)
    doctor.add_argument("--data-root", type=Path, required=True)
    doctor.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
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
