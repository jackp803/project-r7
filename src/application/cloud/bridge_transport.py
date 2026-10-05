"""Existing folder intake plus independently verified copy-bridge publishing."""
from application.cloud.rclone_bridge import RcloneBridge
from application.cloud.manifest import byte_hash, canonical_bytes
from application.cloud.protocol import ArtifactBundle, CloudError


class RcloneCloudTransport:
    def __init__(self, bridge):
        if type(bridge) is not RcloneBridge:
            raise ValueError('Trusted locally configured bridge required')
        self.bridge = bridge

    def discover(self):
        # Reading local verified input does not depend on an available cloud.
        return self.bridge.stage.discover()

    def read_verified(self, descriptor, limit_bytes):
        return self.bridge.stage.read_verified(descriptor, limit_bytes)

    def snapshot(self, descriptor, snapshot_root):
        return self.bridge.stage.snapshot(descriptor, snapshot_root)

    def publish(self, bundle, operation_id):
        if not isinstance(operation_id, str) or not 1 <= len(operation_id) <= 256:
            raise CloudError('BLOCKED', 'PUBLICATION_OPERATION_INVALID')
        # Copy the mapping once; validation and staging use exactly these bytes.
        bundle = ArtifactBundle(bundle.logical_path, dict(bundle.payloads))
        hashes = {name: byte_hash(raw) for name, raw in bundle.payloads.items() if isinstance(raw, bytes)}
        manifest = canonical_bytes(dict(schema_version='r7-result-bundle-v0.2', operation_id=operation_id,
            artifact_hash=byte_hash(canonical_bytes(hashes)), payload_hashes=hashes))
        self.bridge.validate_publication(bundle.logical_path, bundle.payloads, len(manifest))
        local = self.bridge.stage.publish(bundle, operation_id)
        remote = self.bridge.push_bundle(bundle.logical_path)
        if remote.operation_id != local.operation_id or remote.artifact_hash != local.artifact_hash:
            raise CloudError('CONFLICT', 'BRIDGE_PUBLICATION_IDENTITY_CHANGED')
        return remote
