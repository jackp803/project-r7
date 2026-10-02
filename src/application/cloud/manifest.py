"""Strict independent package adapters; exact byte and semantic hashes differ."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from types import MappingProxyType

from strategy import StrategyError, parse_strategy_definition
from application.cloud.protocol import CloudError, PackageSnapshot

MANIFEST_LIMIT = 64 * 1024
STRATEGY_LIMIT = 256 * 1024
NOTES_LIMIT = 64 * 1024
COMMON = {"package_schema_version", "submission_id", "strategy_id", "strategy_version",
          "strategy_content_hash", "created_at", "created_by", "research_hypothesis",
          "requested_dataset_profile", "requested_validation_profile", "requested_robustness_profile"}
HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
SECRET_NAMES = {"api_key", "api_secret", "token", "password", "private_key", "secret", "credential", "credentials"}


def byte_hash(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def safe_component(value):
    if not isinstance(value, str) or not COMPONENT.fullmatch(value) or value.endswith("."):
        raise CloudError("BLOCKED", "UNSAFE_PATH_COMPONENT")
    stem = value.split(".", 1)[0].upper()
    if stem in {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(10)), *(f"LPT{n}" for n in range(10))}:
        raise CloudError("BLOCKED", "RESERVED_PATH_COMPONENT")
    return value


def safe_relative(value):
    if not isinstance(value, str) or len(value) > 384:
        raise CloudError("BLOCKED", "UNSAFE_RELATIVE_PATH")
    parts = value.split("/")
    if len(parts) > 8:
        raise CloudError("BLOCKED", "PATH_DEPTH_LIMIT")
    for part in parts:
        safe_component(part)
    return value


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CloudError("BLOCKED", "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def scan_untrusted(value):
    stack = [(value, 0)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if depth > 32 or nodes > 4096:
            raise CloudError("BLOCKED", "JSON_COMPLEXITY_LIMIT")
        if isinstance(current, dict):
            for key, item in current.items():
                name = key.strip().lower()
                if name in SECRET_NAMES or any(name.endswith("_" + suffix) for suffix in SECRET_NAMES):
                    raise CloudError("BLOCKED", "SECRET_FIELD_FORBIDDEN")
                stack.append((item, depth + 1))
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)


def load_json(raw: bytes, limit=MANIFEST_LIMIT):
    if not isinstance(raw, bytes) or len(raw) > limit:
        raise CloudError("BLOCKED", "JSON_SIZE_LIMIT")
    def invalid_number(_):
        raise CloudError("BLOCKED", "INVALID_JSON_NUMBER")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                           parse_constant=invalid_number, parse_float=invalid_number)
    except CloudError:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise CloudError("BLOCKED", "MALFORMED_JSON") from None
    if not isinstance(value, dict):
        raise CloudError("BLOCKED", "JSON_OBJECT_REQUIRED")
    scan_untrusted(value)
    return value


def utc(value):
    if not isinstance(value, str) or len(value) > 40 or not value.endswith("Z"):
        raise CloudError("BLOCKED", "UTC_TIMESTAMP_REQUIRED")
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise CloudError("BLOCKED", "INVALID_TIMESTAMP") from None
    if result.utcoffset() != timezone.utc.utcoffset(result):
        raise CloudError("BLOCKED", "UTC_TIMESTAMP_REQUIRED")
    return result


@dataclass(frozen=True)
class PayloadSpec:
    role: str
    relative_path: str
    media_type: str
    byte_length: int | None
    sha256: str

    @property
    def limit(self):
        return STRATEGY_LIMIT if self.role == "strategy_definition" else NOTES_LIMIT


@dataclass(frozen=True)
class PackageManifest:
    schema_version: str
    submission_id: str
    strategy_id: str
    strategy_version: str
    strategy_content_hash: str
    manifest_hash: str
    payloads: tuple[PayloadSpec, ...]
    raw: dict


def parse_manifest(raw: bytes) -> PackageManifest:
    value = load_json(raw)
    version = value.get("package_schema_version")
    if version == "r7-strategy-package-v0.1":
        required = COMMON | {"strategy_definition_file", "strategy_definition_sha256"}
    elif version == "r7-strategy-package-v0.2":
        required = COMMON | {"required_runtime_profile", "capability_snapshot_hash", "payloads", "intent_class", "validity"}
    else:
        raise CloudError("BLOCKED", "UNSUPPORTED_PACKAGE_VERSION")
    if value.keys() != required:
        raise CloudError("BLOCKED", "MANIFEST_FIELDS_INVALID")
    for name in ("submission_id", "strategy_id", "strategy_version", "requested_dataset_profile",
                 "requested_validation_profile", "requested_robustness_profile"):
        safe_component(value[name])
    if not isinstance(value["strategy_content_hash"], str) or not HASH.fullmatch(value["strategy_content_hash"]):
        raise CloudError("BLOCKED", "INVALID_SEMANTIC_HASH")
    utc(value["created_at"])
    for name, maximum in (("created_by", 256), ("research_hypothesis", 8192)):
        if not isinstance(value[name], str) or len(value[name]) > maximum or "\x00" in value[name]:
            raise CloudError("BLOCKED", "INVALID_DISPLAY_METADATA")
    if version.endswith("v0.1"):
        path = safe_relative(value["strategy_definition_file"])
        digest = value["strategy_definition_sha256"]
        if not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise CloudError("BLOCKED", "INVALID_BYTE_HASH")
        payloads = (PayloadSpec("strategy_definition", path, "application/json", None, digest),)
    else:
        runtime = value["required_runtime_profile"]
        if (not isinstance(runtime, dict) or runtime.keys() != {"runtime_family", "runtime_version"}
                or any(not isinstance(item, str) or not item or len(item) > 96 for item in runtime.values())):
            raise CloudError("BLOCKED", "INVALID_RUNTIME_PROFILE")
        if not isinstance(value["capability_snapshot_hash"], str) or not HASH.fullmatch(value["capability_snapshot_hash"]):
            raise CloudError("BLOCKED", "INVALID_CAPABILITY_HASH")
        rows = value["payloads"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 2:
            raise CloudError("BLOCKED", "INVALID_PAYLOADS")
        payloads = []
        seen_paths, seen_roles = set(), set()
        for row in rows:
            if not isinstance(row, dict) or row.keys() != {"role", "relative_path", "media_type", "byte_length", "sha256"}:
                raise CloudError("BLOCKED", "INVALID_PAYLOAD_FIELDS")
            role, path = row["role"], safe_relative(row["relative_path"])
            media = {"strategy_definition":"application/json", "research_notes":"text/markdown"}
            if not isinstance(role, str) or role not in media or row["media_type"] != media[role]:
                raise CloudError("BLOCKED", "INVALID_PAYLOAD_ROLE")
            if role in seen_roles or path.casefold() in seen_paths or path.casefold() == "manifest.json":
                raise CloudError("BLOCKED", "PAYLOAD_COLLISION")
            if type(row["byte_length"]) is not int or not 0 <= row["byte_length"] <= (STRATEGY_LIMIT if role == "strategy_definition" else NOTES_LIMIT):
                raise CloudError("BLOCKED", "PAYLOAD_SIZE_LIMIT")
            if not isinstance(row["sha256"], str) or not HASH.fullmatch(row["sha256"]):
                raise CloudError("BLOCKED", "INVALID_BYTE_HASH")
            seen_roles.add(role)
            seen_paths.add(path.casefold())
            payloads.append(PayloadSpec(role, path, row["media_type"], row["byte_length"], row["sha256"]))
        if "strategy_definition" not in seen_roles:
            raise CloudError("BLOCKED", "STRATEGY_PAYLOAD_REQUIRED")
        if not isinstance(value["intent_class"],str) or value["intent_class"] not in {"EVERGREEN_STRATEGY", "TACTICAL_STRATEGY"}:
            raise CloudError("BLOCKED", "INVALID_INTENT_CLASS")
        validity = value["validity"]
        if not isinstance(validity, dict) or validity.keys() != {"from", "until"}:
            raise CloudError("BLOCKED", "INVALID_VALIDITY")
        lower = utc(validity["from"]) if validity["from"] is not None else None
        upper = utc(validity["until"]) if validity["until"] is not None else None
        if (lower is not None and upper is not None and lower >= upper
                or value["intent_class"] == "TACTICAL_STRATEGY" and (lower is None or upper is None)):
            raise CloudError("BLOCKED", "INVALID_VALIDITY_INTERVAL")
        payloads = tuple(payloads)
    return PackageManifest(version, value["submission_id"], value["strategy_id"], value["strategy_version"],
                           value["strategy_content_hash"], byte_hash(canonical_bytes(value)), payloads, value)


def verify_payload(spec: PayloadSpec, raw: bytes, *, corrupt=False):
    code = "SNAPSHOT_CORRUPT" if corrupt else "INCOMPLETE_SYNC"
    if len(raw) > spec.limit or spec.byte_length is not None and len(raw) != spec.byte_length or byte_hash(raw) != spec.sha256:
        raise CloudError(code, "PAYLOAD_INTEGRITY_MISMATCH")
    if spec.role == "research_notes":
        try:
            notes = raw.decode("utf-8")
        except UnicodeError:
            raise CloudError("BLOCKED", "NOTES_NOT_UTF8") from None
        if re.search(r"(?i)(api[_ -]?(key|secret)|password|access[_ -]?token)\s*[:=]|-----BEGIN .*PRIVATE KEY", notes):
            raise CloudError("BLOCKED", "SECRET_CONTENT_FORBIDDEN")


@dataclass(frozen=True)
class VerifiedPackage:
    manifest: PackageManifest
    strategy: object
    definition_bytes: bytes
    snapshot: PackageSnapshot
    compatibility_execution_pass: bool = False


def validate_package(snapshot: PackageSnapshot) -> VerifiedPackage:
    from application.cloud.safe_files import read_bounded
    try:
        raw = read_bounded(snapshot.root, "manifest.json", MANIFEST_LIMIT)
        manifest = parse_manifest(raw)
        seal = load_json(read_bounded(snapshot.root, ".seal.json", MANIFEST_LIMIT))
        if (manifest.manifest_hash != snapshot.manifest_hash or seal.get("manifest_hash") != snapshot.manifest_hash
                or seal.get("manifest_byte_hash") != byte_hash(raw)):
            raise CloudError("SNAPSHOT_CORRUPT", "SNAPSHOT_SEAL_MISMATCH")
        strategy_bytes = None
        for spec in manifest.payloads:
            payload = read_bounded(snapshot.root, spec.relative_path, spec.limit)
            verify_payload(spec, payload, corrupt=True)
            if seal.get("payload_hashes", {}).get(spec.role) != byte_hash(payload):
                raise CloudError("SNAPSHOT_CORRUPT", "SNAPSHOT_SEAL_MISMATCH")
            if spec.role == "strategy_definition":
                strategy_bytes = payload
        load_json(strategy_bytes, STRATEGY_LIMIT)
        strategy = parse_strategy_definition(strategy_bytes)
        if (strategy.strategy_id, strategy.strategy_version, strategy.content_hash) != (
                manifest.strategy_id, manifest.strategy_version, manifest.strategy_content_hash):
            raise CloudError("BLOCKED", "E2_IDENTITY_MISMATCH")
        if manifest.schema_version.endswith("v0.2") and manifest.raw["required_runtime_profile"] != {
                "runtime_family":strategy.runtime_family, "runtime_version":strategy.runtime_version}:
            raise CloudError("BLOCKED", "RUNTIME_PROFILE_MISMATCH")
        return VerifiedPackage(manifest, strategy, strategy_bytes, snapshot)
    except StrategyError:
        raise CloudError("BLOCKED", "E2_DEFINITION_REJECTED") from None
    except CloudError as error:
        if error.code in {"INCOMPLETE_SYNC", "CLOUD_NOT_CONNECTED"}:
            raise CloudError("SNAPSHOT_CORRUPT", "LOCAL_SNAPSHOT_UNAVAILABLE") from None
        raise
