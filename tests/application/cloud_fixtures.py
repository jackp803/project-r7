import hashlib
import json
from pathlib import Path

from tests.strategy.test_slice1_runtime import make_definition


def bytes_hash(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def package(root: Path, submission="submission-1", *, version="0.1", definition=None):
    folder = root / "inbox/strategies" / submission
    folder.mkdir(parents=True, exist_ok=True)
    strategy = definition or make_definition()
    raw = (json.dumps(strategy, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (folder / "strategy.json").write_bytes(raw)
    manifest = {
        "package_schema_version": "r7-strategy-package-v" + version,
        "submission_id": submission, "strategy_id": strategy["strategy_id"],
        "strategy_version": strategy["strategy_version"],
        "strategy_content_hash": strategy["content_hash"], "created_at": "2026-10-02T00:00:00Z",
        "created_by": "offline author fixture", "research_hypothesis": "測試宣告式策略",
        "requested_dataset_profile": "fixture-data", "requested_validation_profile": "diagnostic",
        "requested_robustness_profile": "diagnostic",
    }
    if version == "0.1":
        manifest.update(strategy_definition_file="strategy.json", strategy_definition_sha256=bytes_hash(raw))
    else:
        manifest.update(required_runtime_profile=strategy["runtime_compatibility"],
                        capability_snapshot_hash="sha256:" + "a" * 64,
                        payloads=[{"role":"strategy_definition", "relative_path":"strategy.json", "media_type":"application/json", "byte_length":len(raw), "sha256":bytes_hash(raw)}],
                        intent_class="EVERGREEN_STRATEGY", validity={"from":None, "until":None})
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return folder, manifest, strategy
