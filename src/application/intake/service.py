"""Actual E2 parser -> atomic E6 DRAFT intake, with a recoverable app outbox."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3

from registry import IdentityConflict
from application.cloud.manifest import canonical_bytes, parse_manifest, validate_package
from application.cloud.protocol import CloudError
from application.intake.ledger import IntakeLedger, ManifestConflict, OutboxCapacityError


@dataclass(frozen=True)
class SubmissionOutcome:
    submission_id: str
    state: str
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScanSummary:
    discovered: int
    accepted: int
    idempotent: int
    blocked: int
    incomplete: int
    conflicts: int
    busy: int
    results: tuple[SubmissionOutcome, ...]


class StrategyInboxService:
    def __init__(self, transport, ledger: IntakeLedger, e6, *, snapshot_root: Path,
                 owner_id: str, fault_hook=None, capability_snapshot_hash=None):
        self.transport, self.ledger, self.e6 = transport, ledger, e6
        self.snapshot_root, self.owner_id = Path(snapshot_root), owner_id
        self.fault_hook = fault_hook
        self.capability_snapshot_hash = capability_snapshot_hash

    def _fault(self, point):
        if self.fault_hook is not None: self.fault_hook(point)

    def scan_once(self, now: datetime) -> ScanSummary:
        results = []
        counts = dict(accepted=0, idempotent=0, blocked=0, incomplete=0, conflicts=0, busy=0)
        for descriptor in self.transport.discover():
            if not self.ledger.retry_allowed(descriptor.submission_id,now):
                counts["incomplete"] += 1
                results.append(SubmissionOutcome(descriptor.submission_id,"SYNC_RETRY_WAIT",("BOUNDED_SYNC_BACKOFF",)))
                continue
            manifest = None
            existing = self.ledger.get_submission(descriptor.submission_id)
            try:
                manifest = parse_manifest(self.transport.read_verified(descriptor, 64*1024))
                if existing is not None and existing.manifest_hash != manifest.manifest_hash:
                    raise CloudError("CONFLICT", "IMMUTABLE_SUBMISSION_CHANGED")
                verified = validate_package(self.transport.snapshot(descriptor, self.snapshot_root))
                if manifest.schema_version.endswith("v0.2"):
                    if self.capability_snapshot_hash is None:
                        raise CloudError("BLOCKED", "CAPABILITY_SNAPSHOT_NOT_CONFIGURED")
                    if manifest.raw["capability_snapshot_hash"] != self.capability_snapshot_hash:
                        raise CloudError("BLOCKED", "CAPABILITY_SNAPSHOT_MISMATCH")
                claim = self.ledger.claim(manifest.submission_id, manifest.manifest_hash, self.owner_id, now)
                if not claim.acquired:
                    state = "IDEMPOTENT" if claim.state == "INTAKE_ACCEPTED" else "CLAIM_BUSY"
                    counts["idempotent" if state == "IDEMPOTENT" else "busy"] += 1
                    results.append(SubmissionOutcome(manifest.submission_id, state))
                    continue
                self.ledger.ensure_outbox_capacity()
                outcome = self.e6.intake(verified.definition_bytes, source_actor="R7_INTAKE:" + self.ledger.instance_id,
                                         operation_id=self.ledger.operation_key(manifest.submission_id))
                self._fault("AFTER_E6_INTAKE")
                receipt = canonical_bytes({"schema_version":"r7-intake-receipt-v0.2", "submission_id":manifest.submission_id,
                                           "strategy_id":verified.strategy.strategy_id, "strategy_version":verified.strategy.strategy_version,
                                           "strategy_content_hash":verified.strategy.content_hash, "manifest_hash":manifest.manifest_hash,
                                           "intake_id":outcome.receipt.intake_id, "received_at":outcome.receipt.received_at,
                                           "state":"INTAKE_ACCEPTED", "strategy_lifecycle":outcome.strategy.current_lifecycle_state,
                                           "parser_status":"VALID", "compatibility_status":outcome.compatibility.status,
                                           "verification_kind":outcome.compatibility.verification_kind})
                self.ledger.commit_effect(claim, outcome.receipt.intake_id, receipt, now=now)
                self._fault("AFTER_OUTBOX_COMMIT")
                counts["accepted"] += 1
                results.append(SubmissionOutcome(manifest.submission_id, "INTAKE_ACCEPTED"))
            except (IdentityConflict, ManifestConflict):
                error = CloudError("CONFLICT", "CANONICAL_INTAKE_IDENTITY_CONFLICT")
                self.ledger.observe(descriptor.submission_id, error.code, error.reason, now,
                                    manifest.manifest_hash if manifest else None)
                counts["conflicts"] += 1
                results.append(SubmissionOutcome(descriptor.submission_id,error.code,(error.reason,)))
            except CloudError as error:
                if existing is not None and error.code == "INCOMPLETE_SYNC" and error.reason == "PAYLOAD_INTEGRITY_MISMATCH":
                    error = CloudError("CONFLICT", "ACCEPTED_PAYLOAD_CHANGED")
                observed_state = self.ledger.observe(descriptor.submission_id,error.code if error.code != "SNAPSHOT_CORRUPT" else "UNAVAILABLE",error.reason,now,
                                                     manifest.manifest_hash if manifest else None)
                category = {"INCOMPLETE_SYNC":"incomplete", "CONFLICT":"conflicts"}.get(error.code,"blocked")
                counts[category] += 1
                results.append(SubmissionOutcome(descriptor.submission_id,observed_state,(error.reason,)))
            except sqlite3.Error:
                raise CloudError("UNAVAILABLE", "LOCAL_STORAGE_FAILED") from None
            except OutboxCapacityError:
                self.ledger.observe(descriptor.submission_id,"UNAVAILABLE","OUTBOX_CAPACITY_REACHED",now,manifest.manifest_hash)
                counts["blocked"] += 1
                results.append(SubmissionOutcome(descriptor.submission_id,"UNAVAILABLE",("OUTBOX_CAPACITY_REACHED",)))
        return ScanSummary(len(results), **counts, results=tuple(results))
