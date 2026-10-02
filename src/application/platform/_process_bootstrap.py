"""Private worker gate: descendants start only after OS ownership is established."""

import subprocess
import sys


def main():
    if sys.stdin.readline() != "GO\n":
        return 125
    try:
        child = subprocess.Popen(sys.argv[1:], shell=False, stdin=subprocess.DEVNULL)
        return child.wait()
    except (OSError, ValueError):
        return 126


if __name__ == "__main__":
    raise SystemExit(main())
