"""Owned research child used only by explicit synthetic namespace tests."""
import argparse
from application.config import load_config
from application.local_owners import LocalOwners


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--generation', required=True, type=int)
    args = parser.parse_args()
    owners = LocalOwners(load_config(args.config), namespace='FIXTURE')
    result = owners.queue.step(args.run_id, args.generation)
    return 0 if result['state'] in ('COMPLETE', 'BLOCKED', 'CANCELED') else 2


if __name__ == '__main__':
    raise SystemExit(main())
