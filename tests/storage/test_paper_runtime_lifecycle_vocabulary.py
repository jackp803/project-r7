from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from storage._runtime_validation import validate_position_projection
from storage.runtime import RuntimeValidationError, open_paper_runtime_journal


SUPPORTED_STATES = (
    "PENDING_ENTRY",
    "OPEN_UNPROTECTED",
    "OPEN_PROTECTED",
    "PROFIT_PROTECTED",
    "EXIT_REQUESTED",
    "CLOSED",
    "EMERGENCY",
    "RECONCILIATION_REQUIRED",
)

SUPPORTED_EVENTS = (
    "ENTRY_FILL_OBSERVED",
    "ENTRY_TERMINATED",
    "PROTECTION_VERIFIED",
    "PROFIT_PROTECTION_VERIFIED",
    "PROTECTION_FAILED",
    "PROTECTION_LOST",
    "EXIT_REQUESTED",
    "EXIT_FAILED",
    "POSITION_CLOSED",
    "STATE_UNKNOWN",
    "RECONCILED_FLAT",
    "RECONCILED_OPEN_UNPROTECTED",
    "RECONCILED_OPEN_PROTECTED",
)


def _projection(
    *,
    state: str,
    revision: int = 0,
    kind: str = "GENESIS",
    event: str | None = None,
    previous_id: str | None = None,
    interpreted_at: str = "2026-08-24T07:00:20Z",
) -> dict:
    payload = {
        "schema_version": "contracts-v0.1",
        "position_id": "position-e6-vocabulary-001",
        "symbol": "BTC_USDT_PERP",
        "side": "LONG",
        "actual_quantity": "0.0012",
        "average_entry_price": "60000",
        "opened_at": "2026-08-24T07:00:10Z",
        "broker_state_observed_at": "2026-08-24T07:00:20Z",
        "reconciliation_status": "CONSISTENT",
        "lifecycle_state": state,
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "position_lifecycle_projection_profile_version": "position-lifecycle-projection-v0.1",
        "lifecycle_revision": revision,
        "previous_lifecycle_projection_id": previous_id,
        "lifecycle_projection_kind": kind,
        "lifecycle_event": event,
        "lifecycle_interpreted_at": interpreted_at,
        "lifecycle_source_broker_state_observed_at": "2026-08-24T07:00:20Z",
    }
    identity_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload["lifecycle_projection_id"] = "posproj_" + hashlib.sha256(
        identity_json.encode("utf-8")
    ).hexdigest()
    return payload


class PaperRuntimeLifecycleVocabularyDefinitions(unittest.TestCase):
    def test_unsupported_state_valid_hash_is_rejected_without_current_advancement(self) -> None:
        bad = _projection(state="FUTURE_UNPUBLISHED_STATE")
        with tempfile.TemporaryDirectory() as temp:
            journal = open_paper_runtime_journal(Path(temp) / "runtime.sqlite3")
            try:
                with self.assertRaises(RuntimeValidationError) as caught:
                    journal.persist_position_projection(bad)
                self.assertEqual("UNSUPPORTED_LIFECYCLE_STATE", caught.exception.code)
                recovered = journal.recover(position_id=bad["position_id"])
                self.assertIsNone(recovered.current_position_projection)
                self.assertEqual((), recovered.lifecycle_history)
            finally:
                journal.close()

    def test_unsupported_transition_event_does_not_replace_valid_current_projection(self) -> None:
        genesis = _projection(state="OPEN_UNPROTECTED")
        bad_transition = _projection(
            state="OPEN_PROTECTED",
            revision=1,
            previous_id=genesis["lifecycle_projection_id"],
            kind="TRANSITION",
            event="FUTURE_UNPUBLISHED_EVENT",
            interpreted_at="2026-08-24T07:00:21Z",
        )
        with tempfile.TemporaryDirectory() as temp:
            journal = open_paper_runtime_journal(Path(temp) / "runtime.sqlite3")
            try:
                journal.persist_position_projection(genesis)
                with self.assertRaises(RuntimeValidationError) as caught:
                    journal.persist_position_projection(bad_transition)
                self.assertEqual("UNSUPPORTED_LIFECYCLE_EVENT", caught.exception.code)
                recovered = journal.recover(position_id=genesis["position_id"])
                self.assertIsNotNone(recovered.current_position_projection)
                self.assertEqual(
                    genesis["lifecycle_projection_id"],
                    recovered.current_position_projection.canonical_id,
                )
                self.assertEqual(1, len(recovered.lifecycle_history))
            finally:
                journal.close()

    def test_all_shared_lifecycle_states_remain_mechanically_supported(self) -> None:
        for state in SUPPORTED_STATES:
            with self.subTest(state=state):
                facts = validate_position_projection(_projection(state=state))
                self.assertEqual(state, facts["lifecycle_state"])

    def test_all_shared_transition_events_remain_mechanically_supported(self) -> None:
        predecessor = "posproj_" + "0" * 64
        for event in SUPPORTED_EVENTS:
            with self.subTest(event=event):
                facts = validate_position_projection(
                    _projection(
                        state="OPEN_PROTECTED",
                        revision=1,
                        previous_id=predecessor,
                        kind="TRANSITION",
                        event=event,
                        interpreted_at="2026-08-24T07:00:21Z",
                    )
                )
                self.assertEqual(event, facts["event"])

    def test_genesis_and_reattestation_still_require_null_event(self) -> None:
        with self.assertRaises(RuntimeValidationError) as genesis_error:
            validate_position_projection(
                _projection(state="OPEN_UNPROTECTED", event="PROTECTION_VERIFIED")
            )
        self.assertEqual("INVALID_GENESIS_PROJECTION", genesis_error.exception.code)

        predecessor = "posproj_" + "0" * 64
        with self.assertRaises(RuntimeValidationError) as reattestation_error:
            validate_position_projection(
                _projection(
                    state="OPEN_UNPROTECTED",
                    revision=1,
                    previous_id=predecessor,
                    kind="REATTESTATION",
                    event="PROTECTION_VERIFIED",
                    interpreted_at="2026-08-24T07:00:21Z",
                )
            )
        self.assertEqual(
            "REATTESTATION_EVENT_FORBIDDEN", reattestation_error.exception.code
        )

    def test_transition_still_requires_non_null_event_and_unknown_kind_fails_closed(self) -> None:
        predecessor = "posproj_" + "0" * 64
        with self.assertRaises(RuntimeValidationError) as transition_error:
            validate_position_projection(
                _projection(
                    state="OPEN_PROTECTED",
                    revision=1,
                    previous_id=predecessor,
                    kind="TRANSITION",
                    event=None,
                    interpreted_at="2026-08-24T07:00:21Z",
                )
            )
        self.assertEqual("LIFECYCLE_EVENT_REQUIRED", transition_error.exception.code)

        unknown_kind = _projection(state="OPEN_UNPROTECTED", kind="FUTURE_KIND")
        with self.assertRaises(RuntimeValidationError) as kind_error:
            validate_position_projection(unknown_kind)
        self.assertEqual("INVALID_LIFECYCLE_PROJECTION_KIND", kind_error.exception.code)


if __name__ == "__main__":
    unittest.main()
