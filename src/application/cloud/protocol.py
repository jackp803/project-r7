from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Protocol


class CloudError(ValueError):
    def __init__(self, code: str, reason: str = "PACKAGE_UNAVAILABLE"):
        self.code, self.reason = code, reason
        super().__init__(f"{code}: {reason}")


@dataclass(frozen=True)
class ArtifactDescriptor:
    submission_id: str
    logical_path: str


@dataclass(frozen=True)
class PackageSnapshot:
    root: Path
    manifest_hash: str
    payload_paths: Mapping[str, Path]


@dataclass(frozen=True)
class ArtifactBundle:
    logical_path: str
    payloads: Mapping[str, bytes]


@dataclass(frozen=True)
class PublishReceipt:
    operation_id: str
    status: str
    artifact_hash: str


class CloudArtifactTransport(Protocol):
    def discover(self) -> Iterable[ArtifactDescriptor]: ...
    def read_verified(self, descriptor: ArtifactDescriptor, limit_bytes: int) -> bytes: ...
    def publish(self, bundle: ArtifactBundle, operation_id: str) -> PublishReceipt: ...
