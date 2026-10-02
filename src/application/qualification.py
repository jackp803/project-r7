"""Local-only, inventory-checked qualification with exact revision provenance."""

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

from application.platform.processes import ResourceLimits, spawn_owned

LEGACY_ORDER = ("market_data", "indicators", "strategy", "backtest", "validation", "execution",
                "brokers", "risk", "position", "storage", "platform", "integration", "e2e", "safety")
FOCUSED = (
    ("brokers", "test_okx_action_capability.py"),
    ("position", "test_protection_trigger_validity.py"),
    ("execution", "test_protection_trigger_consumer.py"),
    ("execution", "test_external_close_evidence.py"),
    ("position", "test_external_close_reinterpretation.py"),
    ("brokers", "test_okx_close_sizing.py"),
    ("execution", "test_protection_registry_evidence.py"),
    ("position", "test_protection_registry_policy.py"),
    ("storage", "test_protection_registry_currentness.py"),
    ("storage", "test_external_close_currentness.py"),
    ("storage", "test_external_close_currentness_supersession.py"),
    ("integration", "test_runtime_preflight.py"),
    ("integration", "test_p0_fp02_fp16_composition.py"),
    ("integration", "test_p0_integrated_failure_prevention.py"),
    ("safety", "test_p0_integrated_fail_closed.py"),
    ("e2e", "test_p0_reconciliation_restart_e2e.py"),
)


class QualificationError(ValueError):
    pass


@dataclass(frozen=True)
class Suite:
    name: str
    directory: Path
    test_files: tuple[Path, ...]


@dataclass(frozen=True)
class TestResult:
    tests_run: int
    failures: int
    errors: int
    skipped: int
    expected_failures: int
    unexpected_successes: int
    returncode: int
    passed: bool

    @property
    def tests_passed(self):
        return max(0, self.tests_run - self.failures - self.errors - self.skipped
                   - self.expected_failures - self.unexpected_successes)


def discover_suites(root: Path) -> tuple[Suite, ...]:
    root = Path(root).resolve()
    paths = sorted((root / "tests").glob("**/test_*.py"))
    if not paths:
        raise QualificationError("No test inventory found")
    groups = {}
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise QualificationError("Test inventory escapes source root")
        # One discovery invocation per containing directory prevents a namespace
        # directory from silently hiding nested tests from unittest discovery.
        name = path.parent.relative_to(root / "tests").as_posix()
        groups.setdefault(name, []).append(path)
    ordered = [name for name in LEGACY_ORDER if name in groups]
    ordered += sorted(groups.keys() - set(ordered))
    return tuple(Suite(name, root / "tests" / name, tuple(groups[name])) for name in ordered)


def select_suites(inventory, names):
    if names == ["all"]:
        return tuple(inventory)
    if not names or len(names) != len(set(names)):
        raise QualificationError("Unique nonempty suite selection required")
    indexed = {suite.name: suite for suite in inventory}
    if any(name not in indexed for name in names):
        raise QualificationError("Requested suite missing from inventory")
    return tuple(indexed[name] for name in names)


def parse_result(output: str, *, returncode: int) -> TestResult:
    matches = re.findall(r"^Ran (\d+) tests? in [^\r\n]+$", output, re.MULTILINE)
    count = int(matches[0]) if len(matches) == 1 else 0
    summary = re.findall(r"^(OK|FAILED)(?: \(([^\r\n]*)\))?\s*$", output, re.MULTILINE)
    details = summary[0][1] if len(summary) == 1 else ""
    counts = {name.strip(): int(value) for name, value in re.findall(r"([a-z ]+)=(\d+)", details)}
    result = TestResult(count, counts.get("failures", 0), counts.get("errors", 0),
                        counts.get("skipped", 0), counts.get("expected failures", 0),
                        counts.get("unexpected successes", 0), returncode, False)
    success = (returncode == 0 and count > 0 and len(summary) == 1
               and summary[0][0] == "OK" and not details)
    return TestResult(**{**asdict(result), "passed": success})


def validate_output_root(root: Path, output_root: Path):
    root, output = Path(root).resolve(), Path(output_root).resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise QualificationError("Evidence must be outside the executable worktree")
    if output.exists() and any(output.iterdir()):
        raise QualificationError("Evidence output must be a new or empty directory")
    return output


def _git(root, *arguments):
    result = subprocess.run(["git", *arguments], cwd=root, shell=False, check=True,
                            capture_output=True, encoding="utf-8")
    return result.stdout.strip()


def revision_fact(root, expected=None, require_clean=False):
    revision = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    if expected is not None and revision != expected:
        raise QualificationError("Executable revision mismatch")
    if require_clean and status:
        raise QualificationError("Executable worktree must be exact clean")
    return {"revision": revision, "worktree": "CLEAN" if not status else "DIRTY"}


def _sanitize(output, root):
    for path, replacement in ((str(Path(root).resolve()), "<SOURCE_ROOT>"),
                              (str(Path.home()), "<USER_HOME>")):
        output = output.replace(path, replacement).replace(path.replace("\\", "/"), replacement)
        output = output.replace(path.replace("\\", "\\\\"), replacement)
    return output


def run_qualification(root, output_root, *, suites=("all",), include_focused=False,
                      expected_revision=None, require_clean=False, timeout_seconds=600):
    root = Path(root).resolve()
    output = validate_output_root(root, output_root)
    before = revision_fact(root, expected_revision, require_clean)
    inventory = discover_suites(root)
    selected = select_suites(inventory, list(suites))
    commands = []
    if include_focused:
        for name, pattern in FOCUSED:
            if not (root / "tests" / name / pattern).is_file():
                raise QualificationError("Required focused test file missing")
            commands.append(("phase_1", name, pattern))
    commands += [("phase_2", suite.name, "test_*.py") for suite in selected]
    output.mkdir(parents=True, exist_ok=True)
    # Inherit the local environment without inspecting/printing its values.
    environment = os.environ.copy()
    environment.update(PYTHONPATH=str(root / "src"), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    report = {
        "schema_version": "r7-local-qualification-v0.2", "source_before": before,
        "python": platform.python_version(), "os": platform.system(),
        "os_version": platform.version(), "architecture": platform.machine(),
        "execution": "LOCAL", "github_compute": "NOT_USED", "real_provider_calls": 0,
        "real_credentials": "NONE", "capital": "NONE",
        "inventory": [{"suite": suite.name, "files": len(suite.test_files)} for suite in inventory],
        "commands": [], "passed": False,
    }
    for index, (phase, name, pattern) in enumerate(commands, 1):
        revision_fact(root, before["revision"], require_clean)
        argv = [sys.executable, "-m", "unittest", "discover", "-s", "tests/" + name, "-p", pattern, "-v"]
        raw_path = output / f"{index:03d}.raw"
        start = time.monotonic()
        with raw_path.open("wb") as stream:
            handle = spawn_owned(argv, cwd=root, limits=ResourceLimits(timeout_seconds),
                                 stdout=stream, stderr=subprocess.STDOUT, env=environment)
            code = handle.wait(timeout=timeout_seconds + 10)
        text = raw_path.read_text(encoding="utf-8", errors="replace")
        sanitized = _sanitize(text, root)
        log = f"{index:03d}-{phase}-{name.replace('/', '-')}.log"
        (output / log).write_text(sanitized, encoding="utf-8", newline="\n")
        raw_path.unlink()  # Only the runner's own newly created raw file.
        result = parse_result(text, returncode=code)
        fact = revision_fact(root, before["revision"], require_clean)
        command = {"phase": phase, "suite": name, "pattern": pattern, **asdict(result),
                   "tests_passed": result.tests_passed, "duration_seconds": time.monotonic() - start,
                   "tree_reaped": handle.termination_report.reaped, "source_after": fact,
                   "log": log, "log_sha256": hashlib.sha256(sanitized.encode("utf-8")).hexdigest()}
        report["commands"].append(command)
        print(f"{index}/{len(commands)} {phase}/{name}: {'PASS' if result.passed else 'FAIL'} {result.tests_run} tests", flush=True)
        (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if not result.passed or not handle.termination_report.reaped:
            break
    report["source_after"] = revision_fact(root, before["revision"], require_clean)
    report["passed"] = (len(report["commands"]) == len(commands)
                        and all(item["passed"] and item["tree_reaped"] for item in report["commands"]))
    report["tests_run"] = sum(item["tests_run"] for item in report["commands"])
    (output / "qualification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
