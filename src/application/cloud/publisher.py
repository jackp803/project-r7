"""Independent bounded publication; remote completion needs a real transport ack."""

from dataclasses import dataclass

from application.cloud.manifest import byte_hash, canonical_bytes
from application.cloud.protocol import ArtifactBundle, CloudError


@dataclass(frozen=True)
class PublishSummary:
    attempted: int
    local_staged: int
    cloud_acknowledged: int
    unavailable: int
    conflicts: int


class Publisher:
    def __init__(self, ledger, transport, *, fault_hook=None):
        self.ledger, self.transport, self.fault_hook = ledger, transport, fault_hook

    def flush(self, limit: int) -> PublishSummary:
        counts = dict(local_staged=0, cloud_acknowledged=0, unavailable=0, conflicts=0)
        items = self.ledger.pending_outbox(limit)
        for item in items:
            try:
                if byte_hash(item.payload) != item.payload_hash:
                    raise CloudError("CONFLICT", "OUTBOX_CONTENT_CORRUPT")
                receipt = self.transport.publish(ArtifactBundle(item.logical_path,{"receipt.json":item.payload}),item.operation_id)
                if self.fault_hook is not None: self.fault_hook("AFTER_UPLOAD_BEFORE_ACK")
                expected_hash = byte_hash(canonical_bytes({"receipt.json":item.payload_hash}))
                if (receipt.operation_id != item.operation_id or receipt.status not in {"LOCAL_STAGED","CLOUD_ACKNOWLEDGED"}
                        or receipt.artifact_hash != expected_hash):
                    raise CloudError("UNAVAILABLE", "TRANSPORT_RECEIPT_INVALID")
                self.ledger.record_publication(item.operation_id,receipt.status,artifact_hash=receipt.artifact_hash)
                counts["local_staged" if receipt.status == "LOCAL_STAGED" else "cloud_acknowledged"] += 1
            except CloudError as error:
                status = "CONFLICT" if error.code == "CONFLICT" else "UNAVAILABLE"
                self.ledger.record_publication(item.operation_id,status)
                counts["conflicts" if status == "CONFLICT" else "unavailable"] += 1
        return PublishSummary(len(items),**counts)
