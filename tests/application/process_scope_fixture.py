import argparse
import json
from pathlib import Path
import time

from application.platform.scope_lock import ProcessScopeLock, ScopeBusy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--ready', required=True)
    args = parser.parse_args()
    try:
        with ProcessScopeLock(args.scope, lock_root=Path(args.root)):
            Path(args.ready).write_text(json.dumps({'status': 'LOCKED'}), encoding='utf-8')
            time.sleep(120)
    except ScopeBusy:
        Path(args.ready).write_text(json.dumps({'status': 'BUSY'}), encoding='utf-8')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
