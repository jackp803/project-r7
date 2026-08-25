from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from registry.models import EARLY_LIFECYCLE_STATES
from storage._sqlite_registry import _apply_migrations, _connect
from storage.operational_mode import (
    OPERATIONAL_MODES,
    OperationalModeAuthorityError,
    OperationalModeValidationError,
    open_operational_mode_store,
)
from storage.runtime import open_paper_runtime_journal
from test_paper_runtime_durability import risk_decision


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _seed_legacy_mode(connection: sqlite3.Connection, mode: str) -> None:
    payload = {
        "schema_version": "contracts-v0.1",
        "mode": mode,
        "changed_at": "2026-08-25T04:00:00Z",
        "changed_by": "legacy-test-fixture",
        "reason_codes": ["SYNTHETIC_EXISTING_MODE"],
        "approval_record_id": None,
        "previous_mode": None,
        "mode_revision": 0,
        "evidence_ref": "synthetic-existing-mode",
    }
    payload_json = _canonical_json(payload)
    transition_id = "opmode_" + hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    connection.execute(
        """
        INSERT INTO operational_mode_transitions (
            transition_id, mode_revision, schema_version, previous_mode, new_mode,
            changed_at, changed_by, reason_codes_json, approval_record_id,
            evidence_ref, payload_json, payload_hash
        ) VALUES (?, 0, 'contracts-v0.1', NULL, ?, ?, ?, ?, NULL, ?, ?, ?)
        """,
        (
            transition_id,
            mode,
            payload["changed_at"],
            payload["changed_by"],
            _canonical_json(payload["reason_codes"]),
            payload["evidence_ref"],
            payload_json,
            _sha256_text(payload_json),
        ),
    )
    connection.commit()


def _checkpoint(*, observed_at: str = "2026-08-25T04:01:00Z", suffix: str = "001") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "provider": "OKX",
        "environment_classification": "PRODUCTION_READ_ONLY_SHADOW",
        "regional_hostname_ref": "okx-global",
        "canonical_instrument": "BTC_USDT_PERP",
        "provider_instrument": "BTC-USDT-SWAP",
        "observed_at": observed_at,
        "permission_category": "read_only",
        "market_healthy": True,
        "account_config_known": True,
        "balance_known": True,
        "position_truth_known": True,
        "isolated_leverage_known": True,
        "unexpected_exposure": False,
        "pending_order_count": 0,
        "unreconciled_fill_count": 0,
        "provider_observation_ref": f"r7obs_shadow_{suffix}",
        "provider_observation_hash": "sha256:" + suffix[-1] * 64,
        "reason_codes": [],
    }


class OperationalModeShadowDefinitions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "gate-c.sqlite3"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _shadow_store(self):
        store = open_operational_mode_store(self.db_path)
        store.initialize(
            "RESEARCH",
            changed_at="2026-08-25T04:00:00Z",
            changed_by="product-owner",
            reason_codes=["GATE_C_BASELINE"],
            evidence_ref="gate-c-phase1-authority",
        )
        store.transition(
            "SHADOW",
            expected_revision=0,
            changed_at="2026-08-25T04:00:30Z",
            changed_by="product-owner",
            reason_codes=["SHADOW_ONLY_AUTHORIZED"],
            evidence_ref="gate-c-shadow-only-authority",
        )
        return store

    def test_all_shared_operational_modes_are_distinctly_representable_and_restorable(self) -> None:
        self.assertEqual(
            {"RESEARCH", "PAPER", "SHADOW", "LIVE", "PAUSED", "LOCKED"},
            set(OPERATIONAL_MODES),
        )
        for mode in sorted(OPERATIONAL_MODES):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "mode.sqlite3"
                if mode == "SHADOW":
                    store = open_operational_mode_store(path)
                    store.initialize(
                        "RESEARCH",
                        changed_at="2026-08-25T04:00:00Z",
                        changed_by="product-owner",
                        reason_codes=["SYNTHETIC_MODE_TEST"],
                        evidence_ref="synthetic-mode-test",
                    )
                    store.transition(
                        "SHADOW",
                        expected_revision=0,
                        changed_at="2026-08-25T04:00:01Z",
                        changed_by="product-owner",
                        reason_codes=["SYNTHETIC_SHADOW_TEST"],
                        evidence_ref="synthetic-shadow-test",
                    )
                    store.close()
                elif mode == "LIVE":
                    connection = _connect(path)
                    _apply_migrations(connection)
                    _seed_legacy_mode(connection, "LIVE")
                    connection.close()
                else:
                    store = open_operational_mode_store(path)
                    store.initialize(
                        mode,
                        changed_at="2026-08-25T04:00:00Z",
                        changed_by="product-owner",
                        reason_codes=["SYNTHETIC_MODE_TEST"],
                        evidence_ref="synthetic-mode-test",
                    )
                    store.close()

                restored = open_operational_mode_store(path)
                try:
                    recovery = restored.recover()
                    self.assertIsNotNone(recovery.current_mode)
                    self.assertEqual(mode, recovery.current_mode.mode)
                    if mode == "LIVE":
                        self.assertEqual("LIVE_UNAUTHORIZED", recovery.status)
                        self.assertFalse(recovery.shadow_planning_safe)
                finally:
                    restored.close()

    def test_shadow_is_operational_mode_not_strategy_lifecycle_state(self) -> None:
        self.assertIn("SHADOW", OPERATIONAL_MODES)
        self.assertNotIn("SHADOW", EARLY_LIFECYCLE_STATES)
        store = self._shadow_store()
        try:
            self.assertEqual("SHADOW", store.recover().current_mode.mode)
        finally:
            store.close()

    def test_authorized_shadow_transition_is_append_only_and_auditable(self) -> None:
        store = self._shadow_store()
        try:
            history = store.history()
            self.assertEqual(2, len(history))
            self.assertEqual("RESEARCH", history[0].mode)
            self.assertEqual("SHADOW", history[1].mode)
            self.assertEqual("RESEARCH", history[1].previous_mode)
            self.assertEqual(1, history[1].mode_revision)
            self.assertEqual("product-owner", history[1].changed_by)
            self.assertEqual(("SHADOW_ONLY_AUTHORIZED",), history[1].reason_codes)
            self.assertEqual("gate-c-shadow-only-authority", history[1].evidence_ref)
        finally:
            store.close()

        connection = sqlite3.connect(self.db_path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE operational_mode_transitions SET new_mode='LIVE' WHERE mode_revision=1"
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM operational_mode_transitions WHERE mode_revision=1"
                )
        finally:
            connection.close()

    def test_no_supported_or_direct_transition_into_live_exists_for_gate_c(self) -> None:
        store = open_operational_mode_store(self.db_path)
        try:
            with self.assertRaises(OperationalModeAuthorityError):
                store.initialize(
                    "LIVE",
                    changed_at="2026-08-25T04:00:00Z",
                    changed_by="product-owner",
                    reason_codes=["FORBIDDEN_TEST"],
                    evidence_ref="forbidden-test",
                )
            store.initialize(
                "RESEARCH",
                changed_at="2026-08-25T04:00:00Z",
                changed_by="product-owner",
                reason_codes=["GATE_C_BASELINE"],
                evidence_ref="gate-c-phase1-authority",
            )
            with self.assertRaises(OperationalModeAuthorityError):
                store.transition(
                    "LIVE",
                    expected_revision=0,
                    changed_at="2026-08-25T04:00:01Z",
                    changed_by="product-owner",
                    reason_codes=["FORBIDDEN_TEST"],
                    evidence_ref="forbidden-test",
                )
            self.assertFalse(hasattr(store, "submit_order"))
            self.assertFalse(hasattr(store, "enable_live"))
            self.assertFalse(hasattr(store, "promote_live"))
        finally:
            store.close()

        connection = sqlite3.connect(self.db_path)
        try:
            payload = {
                "schema_version": "contracts-v0.1",
                "mode": "LIVE",
                "changed_at": "2026-08-25T04:00:02Z",
                "changed_by": "synthetic-direct-sql",
                "reason_codes": ["FORBIDDEN_DIRECT_LIVE"],
                "approval_record_id": None,
                "previous_mode": "RESEARCH",
                "mode_revision": 1,
                "evidence_ref": "forbidden-direct-live",
            }
            payload_json = _canonical_json(payload)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO operational_mode_transitions (
                        transition_id, mode_revision, schema_version, previous_mode, new_mode,
                        changed_at, changed_by, reason_codes_json, approval_record_id,
                        evidence_ref, payload_json, payload_hash
                    ) VALUES (?, 1, 'contracts-v0.1', 'RESEARCH', 'LIVE', ?, ?, ?, NULL, ?, ?, ?)
                    """,
                    (
                        "opmode_" + hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
                        payload["changed_at"],
                        payload["changed_by"],
                        _canonical_json(payload["reason_codes"]),
                        payload["evidence_ref"],
                        payload_json,
                        _sha256_text(payload_json),
                    ),
                )
        finally:
            connection.close()

    def test_shadow_checkpoint_is_exact_after_restart_but_fresh_reconciliation_is_required(self) -> None:
        store = self._shadow_store()
        first_payload = _checkpoint()
        first = store.record_shadow_checkpoint(first_payload)
        same_session = store.recover()
        self.assertEqual("READY", same_session.status)
        self.assertTrue(same_session.shadow_planning_safe)
        self.assertEqual(first_payload, same_session.last_shadow_checkpoint.payload)
        store.close()

        restored = open_operational_mode_store(self.db_path)
        try:
            recovery = restored.recover()
            self.assertEqual("SHADOW", recovery.current_mode.mode)
            self.assertEqual("RECONCILIATION_REQUIRED", recovery.status)
            self.assertTrue(recovery.fresh_reconciliation_required)
            self.assertFalse(recovery.shadow_planning_safe)
            self.assertEqual(first.checkpoint_id, recovery.last_shadow_checkpoint.checkpoint_id)
            self.assertEqual(first_payload, recovery.last_shadow_checkpoint.payload)

            replay = restored.record_shadow_checkpoint(first_payload)
            self.assertEqual(first.checkpoint_id, replay.checkpoint_id)
            self.assertEqual("RECONCILIATION_REQUIRED", restored.recover().status)

            second_payload = _checkpoint(observed_at="2026-08-25T04:01:01Z", suffix="002")
            second = restored.record_shadow_checkpoint(second_payload)
            current = restored.recover()
            self.assertEqual("READY", current.status)
            self.assertTrue(current.shadow_planning_safe)
            self.assertEqual(second.checkpoint_id, current.last_shadow_checkpoint.checkpoint_id)
            self.assertEqual(second_payload, current.last_shadow_checkpoint.payload)
        finally:
            restored.close()

    def test_missing_or_corrupt_shadow_checkpoint_fails_closed(self) -> None:
        store = self._shadow_store()
        try:
            missing = store.recover()
            self.assertEqual("RECONCILIATION_REQUIRED", missing.status)
            self.assertIn("SHADOW_CHECKPOINT_MISSING", missing.reason_codes)
        finally:
            store.close()

        connection = sqlite3.connect(self.db_path)
        try:
            corrupt_payload = _checkpoint()
            payload_json = _canonical_json(corrupt_payload)
            connection.execute(
                """
                INSERT INTO shadow_provider_checkpoints (
                    checkpoint_id, checkpoint_revision, mode_revision,
                    observed_at, provider_observation_ref, payload_json, payload_hash
                ) VALUES (?, 0, 1, ?, ?, ?, ?)
                """,
                (
                    "shadowcp_" + "0" * 64,
                    corrupt_payload["observed_at"],
                    corrupt_payload["provider_observation_ref"],
                    payload_json,
                    "sha256:" + "0" * 64,
                ),
            )
            connection.commit()
        finally:
            connection.close()

        restored = open_operational_mode_store(self.db_path)
        try:
            recovery = restored.recover()
            self.assertEqual("CONFLICT", recovery.status)
            self.assertTrue(recovery.fresh_reconciliation_required)
            self.assertFalse(recovery.shadow_planning_safe)
        finally:
            restored.close()

    def test_paper_evidence_cannot_satisfy_shadow_provider_checkpoint(self) -> None:
        paper = open_paper_runtime_journal(self.db_path)
        try:
            paper.persist_risk_decision(risk_decision())
        finally:
            paper.close()

        store = self._shadow_store()
        try:
            recovery = store.recover()
            self.assertEqual("RECONCILIATION_REQUIRED", recovery.status)
            self.assertIn("SHADOW_CHECKPOINT_MISSING", recovery.reason_codes)
            self.assertFalse(recovery.shadow_planning_safe)
        finally:
            store.close()

    def test_checkpoint_metadata_never_promotes_mode_and_sensitive_fields_are_rejected(self) -> None:
        store = self._shadow_store()
        try:
            for forbidden_field, value in (
                ("api_secret", "secret-value"),
                ("provider_order_id", "provider-order-123"),
                ("exact_account_balance", "12345.67"),
                ("credentials_present", True),
                ("provider_available", True),
            ):
                with self.subTest(field=forbidden_field):
                    payload = _checkpoint()
                    payload[forbidden_field] = value
                    with self.assertRaises(OperationalModeValidationError):
                        store.record_shadow_checkpoint(payload)
                    self.assertEqual("SHADOW", store.recover().current_mode.mode)
            self.assertFalse(hasattr(store, "submit_provider_order"))
            self.assertFalse(hasattr(store, "account_mutation"))
        finally:
            store.close()

    def test_non_read_only_or_provider_activity_cannot_be_accepted_as_shadow_checkpoint(self) -> None:
        store = self._shadow_store()
        try:
            cases = (
                ("permission_category", "trade"),
                ("market_healthy", False),
                ("balance_known", False),
                ("unexpected_exposure", True),
                ("pending_order_count", 1),
                ("unreconciled_fill_count", 1),
                ("environment_classification", "DEMO"),
            )
            for field, value in cases:
                with self.subTest(field=field):
                    payload = _checkpoint()
                    payload[field] = value
                    with self.assertRaises(OperationalModeValidationError):
                        store.record_shadow_checkpoint(payload)
                    recovery = store.recover()
                    self.assertEqual("RECONCILIATION_REQUIRED", recovery.status)
                    self.assertFalse(recovery.shadow_planning_safe)
        finally:
            store.close()

    def test_operational_mode_migration_is_additive_and_idempotent(self) -> None:
        connection = _connect(self.db_path)
        try:
            _apply_migrations(connection)
            connection.execute(
                """
                INSERT INTO paper_runtime_conflicts (
                    reason_code, object_kind, canonical_id
                ) VALUES ('SYNTHETIC_GATE_B_SENTINEL', 'TEST_SENTINEL', 'sentinel-001')
                """
            )
            connection.commit()
            _apply_migrations(connection)
            expected = sorted(path.name for path in Path("src/storage/migrations").glob("*.sql"))
            actual = [
                row[0]
                for row in connection.execute(
                    "SELECT migration_name FROM schema_migrations ORDER BY migration_name"
                )
            ]
            self.assertIn("0004_operational_mode_shadow.sql", expected)
            self.assertEqual(expected, actual)
            sentinel = connection.execute(
                "SELECT reason_code FROM paper_runtime_conflicts WHERE canonical_id='sentinel-001'"
            ).fetchone()
            self.assertEqual("SYNTHETIC_GATE_B_SENTINEL", sentinel[0])
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("operational_mode_transitions", tables)
            self.assertIn("shadow_provider_checkpoints", tables)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
