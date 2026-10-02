"""Local runner; no provider connection or hosted compute integration."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from application.qualification import QualificationError, discover_suites, run_qualification


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", action="append")
    parser.add_argument("--focused", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-revision")
    parser.add_argument("--require-clean", action="store_true")
    options = parser.parse_args()
    try:
        if options.list:
            for suite in discover_suites(ROOT):
                print(f"{suite.name}: {len(suite.test_files)} files")
            return 0
        if options.output is None:
            parser.error("--output outside executable worktree is required")
        report = run_qualification(ROOT, options.output, suites=options.suite or ["all"],
                                   include_focused=options.focused,
                                   expected_revision=options.expected_revision,
                                   require_clean=options.require_clean)
        return 0 if report["passed"] else 1
    except QualificationError as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
