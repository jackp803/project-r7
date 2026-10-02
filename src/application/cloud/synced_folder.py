"""Bounded folder transport. A staged file is never a remote acknowledgment."""

import json
import os
from pathlib import Path
import stat
from types import MappingProxyType
import uuid

from application.cloud.manifest import (MANIFEST_LIMIT, byte_hash, canonical_bytes, load_json,
                                        parse_manifest, safe_component, safe_relative, verify_payload)
from application.cloud.protocol import (ArtifactDescriptor, ArtifactBundle, CloudError,
                                        PackageSnapshot, PublishReceipt)
from application.cloud.safe_files import read_bounded, write_immutable


def _reject_links(path: Path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise CloudError("INCOMPLETE_SYNC", "ARTIFACT_MISSING") from None
    except OSError:
        raise CloudError("UNAVAILABLE", "ARTIFACT_METADATA_UNAVAILABLE") from None
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise CloudError("BLOCKED", "LINK_OR_REPARSE_FORBIDDEN")


class SyncedFolderCloudTransport:
    def __init__(self, root: Path, *, expected_root_id: str, fault_hook=None):
        self.root = Path(root).absolute()
        self.expected_root_id = safe_component(expected_root_id)
        self.fault_hook = fault_hook

    def _check_root(self):
        try:
            marker = load_json(read_bounded(self.root, ".r7-root.json", 4096))
        except CloudError as error:
            if error.code == "BLOCKED" and "REPARSE" in error.reason:
                raise
            raise CloudError("CLOUD_NOT_CONNECTED", "ROOT_MARKER_UNAVAILABLE") from None
        if marker != {"root_id": self.expected_root_id}:
            raise CloudError("CLOUD_NOT_CONNECTED", "ROOT_IDENTITY_MISMATCH")

    def discover(self):
        self._check_root()
        inbox = self.root / "inbox/strategies"
        if not inbox.exists():
            return
        for ancestor in (self.root / "inbox", inbox):
            _reject_links(ancestor)
        # Bounded batch. Repeated scans are hints; the durable ledger owns effects.
        names = []
        with os.scandir(inbox) as entries:
            for entry in entries:
                if len(names) >= 1000:
                    raise CloudError("BLOCKED", "DISCOVERY_BATCH_LIMIT")
                names.append(entry.name)
        collisions = set()
        for name in sorted(names):
            safe_component(name)
            if name.casefold() in collisions:
                raise CloudError("BLOCKED", "SUBMISSION_CASE_COLLISION")
            collisions.add(name.casefold())
            folder = inbox / name
            _reject_links(folder)
            if folder.is_dir() and (folder / "manifest.json").exists():
                yield ArtifactDescriptor(name, "inbox/strategies/" + name)

    def read_verified(self, descriptor: ArtifactDescriptor, limit_bytes: int):
        self._check_root()
        safe_component(descriptor.submission_id)
        expected = "inbox/strategies/" + descriptor.submission_id
        if descriptor.logical_path != expected:
            raise CloudError("BLOCKED", "DESCRIPTOR_PATH_MISMATCH")
        return read_bounded(self.root, expected + "/manifest.json", limit_bytes)

    def snapshot(self, descriptor: ArtifactDescriptor, snapshot_root: Path):
        raw_manifest = self.read_verified(descriptor, MANIFEST_LIMIT)
        manifest = parse_manifest(raw_manifest)
        if manifest.submission_id != descriptor.submission_id:
            raise CloudError("BLOCKED", "SUBMISSION_IDENTITY_MISMATCH")
        raw_payloads = {}
        for spec in manifest.payloads:
            raw = read_bounded(self.root, descriptor.logical_path + "/" + spec.relative_path, spec.limit)
            verify_payload(spec, raw)
            raw_payloads[spec.role] = raw
        # Check structure/secrets before staging any rejected strategy bytes.
        from application.cloud.manifest import STRATEGY_LIMIT
        load_json(raw_payloads["strategy_definition"], STRATEGY_LIMIT)
        folder = self.root / descriptor.logical_path
        seen = 0
        for base, directories, files in os.walk(folder, followlinks=False):
            for name in directories + files:
                seen += 1
                if seen > 32:
                    raise CloudError("BLOCKED", "PACKAGE_FILE_LIMIT")
                path = Path(base) / name
                _reject_links(path)
                if path.suffix.lower() in {".exe", ".dll", ".com", ".bat", ".cmd", ".ps1", ".py", ".sh", ".js"}:
                    raise CloudError("BLOCKED", "EXECUTABLE_ARTIFACT_FORBIDDEN")
        # Re-read only to detect an evolving manifest; execution uses already read
        # verified bytes and never reopens the cloud payload.
        if self.read_verified(descriptor, MANIFEST_LIMIT) != raw_manifest:
            raise CloudError("INCOMPLETE_SYNC", "MANIFEST_CHANGED_DURING_READ")
        local = Path(snapshot_root).absolute()
        if local.is_relative_to(self.root) or self.root.is_relative_to(local):
            raise CloudError("BLOCKED", "SNAPSHOT_ROOT_MUST_BE_LOCAL_AND_DISJOINT")
        try:
            for ancestor in reversed(local.parents):
                if ancestor.exists(): _reject_links(ancestor)
            local.mkdir(parents=True, exist_ok=True, mode=0o700)
            _reject_links(local)
        except OSError:
            raise CloudError("UNAVAILABLE", "LOCAL_SNAPSHOT_WRITE_FAILED") from None
        target = local / (manifest.submission_id + "-" + manifest.manifest_hash[7:])
        payload_paths = MappingProxyType({spec.role:target / spec.relative_path for spec in manifest.payloads})
        snapshot = PackageSnapshot(target, manifest.manifest_hash, payload_paths)
        if target.exists():
            from application.cloud.manifest import validate_package
            validate_package(snapshot)
            return snapshot
        staging = local / ("staging-" + uuid.uuid4().hex)
        try:
            staging.mkdir(mode=0o700)
            (staging / "manifest.json").write_bytes(raw_manifest)
            for spec in manifest.payloads:
                path = staging / spec.relative_path
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                path.write_bytes(raw_payloads[spec.role])
            seal = {"schema_version":"r7-package-snapshot-v0.2", "manifest_hash":manifest.manifest_hash,
                    "manifest_byte_hash":byte_hash(raw_manifest),
                    "payload_hashes":{role:byte_hash(raw) for role, raw in raw_payloads.items()}}
            (staging / ".seal.json").write_bytes(canonical_bytes(seal))
            os.rename(staging, target)
        except OSError:
            # Retain incomplete private staging for diagnosis; never recursively
            # remove a computed path or classify a disk failure as strategy failure.
            raise CloudError("UNAVAILABLE", "LOCAL_SNAPSHOT_WRITE_FAILED") from None
        return snapshot

    def publish(self, bundle: ArtifactBundle, operation_id: str):
        self._check_root()
        safe_relative(bundle.logical_path)
        if not isinstance(operation_id, str) or not operation_id or len(operation_id) > 256:
            raise CloudError("BLOCKED", "PUBLICATION_OPERATION_INVALID")
        if not bundle.logical_path.startswith(("receipts/", "reports/", "capabilities/", "research/", "candidates/", "paper/", "live/")):
            raise CloudError("BLOCKED", "AUTHOR_NAMESPACE_READ_ONLY")
        if not bundle.payloads or len(bundle.payloads) > 32:
            raise CloudError("BLOCKED", "PUBLICATION_BUNDLE_LIMIT")
        hashes, folded = {}, set()
        for name, raw in bundle.payloads.items():
            safe_relative(name)
            if name.casefold() in folded or name.casefold() == "manifest.json":
                raise CloudError("BLOCKED", "PUBLICATION_PATH_COLLISION")
            if not isinstance(raw, bytes) or len(raw) > 256 * 1024:
                raise CloudError("BLOCKED", "PUBLICATION_PAYLOAD_LIMIT")
            folded.add(name.casefold())
            hashes[name] = byte_hash(raw)
        content_hash = byte_hash(canonical_bytes(hashes))
        target = self.root / bundle.logical_path
        for name, raw in bundle.payloads.items():
            write_immutable(self.root,bundle.logical_path+"/"+name,raw,fault_hook=self.fault_hook)
        raw_manifest = canonical_bytes({"schema_version":"r7-result-bundle-v0.2", "operation_id":operation_id,
                                        "artifact_hash":content_hash, "payload_hashes":hashes})
        write_immutable(self.root,bundle.logical_path+"/manifest.json",raw_manifest,fault_hook=self.fault_hook)
        return PublishReceipt(operation_id, "LOCAL_STAGED", content_hash)
