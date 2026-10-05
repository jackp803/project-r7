"""Existing folder intake plus independently verified copy-bridge publishing."""
from application.cloud.rclone_bridge import RcloneBridge


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
        local = self.bridge.stage.publish(bundle, operation_id)
        remote = self.bridge.push_bundle(bundle.logical_path)
        if remote.operation_id != local.operation_id or remote.artifact_hash != local.artifact_hash:
            from application.cloud.protocol import CloudError
            raise CloudError('CONFLICT', 'BRIDGE_PUBLICATION_IDENTITY_CHANGED')
        return remote
