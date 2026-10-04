"""Frozen product entrypoint, including the owned-process bootstrap dispatcher."""
from application.cli import run

if __name__ == '__main__':
    raise SystemExit(run())
