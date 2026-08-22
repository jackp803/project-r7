from __future__ import annotations

import json
import unittest

from registry import (
    CompatibilityEvidence,
    EvidenceGateError,
    LifecycleTransitionRecord,
    StrategyIdentity,
    StrategyPlatformService,
    StrategyVersionRecord,
    ValidationEvidenceRecord,
)
from storage._sqlite_registry import (
    _apply_migrations as apply_migrations,
    _connect as connect,
    _internal_store_for_tests as SQLiteRegistryStore,
)


def strategy_record(strategy_id: str) -> StrategyVersionRecord:
    identity = StrategyIdentity(strategy_id, "1.0.0")
    return StrategyVersionRecord(
        identity=identity,
        strategy_schema_version="contracts-v0.1",
        content_hash=f"sha256:{strategy_id}",
        name="Evidence Authority Strategy",
        symbol="BTC_USDT_PERP",
        declared_runtime_family="project-r7-e2-strategy-runtime",
        declared_runtime_version="0.1.0",
        definition_json='{"fixture":true}',
        upstream_created_at="2026-08-20T00:00:00Z",
        registered_at="2026-08-20T00:01:00Z",
    )


def strategy_payload(strategy_id: str) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "strategy_id": strategy_id,
        "strategy_version": "1.0.0",
        "name": "Evidence Authority Strategy",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["1h"],
        "parameters": {"fast": 2, "slow": 3},
        "rules": {"dsl_version": "0.1", "long": {}, "short": {}},
        "runtime_compatibility": {
            "runtime_family": "project-r7-e2-strategy-runtime",
            "runtime_version": "0.1.0",
        },
        "content_hash": f"sha256:{strategy_id}",
        "created_at": "2026-08-20T00:00:00Z",
    }


def compatibility(
    identity: StrategyIdentity,
    *,
    suffix: str,
    checker: str = "E2_TEST_FIXTURE",
    status: str = "PASS",
    verification_kind: str = "LOCAL_EXECUTION",
    source_revision: str | None = "e2-synthetic-revision",
    environment: str | None = "local-test-fixture",
    command: str | None = "synthetic-e2-compat-check",
    result_ref: str | None = "synthetic-pass",
) -> CompatibilityEvidence:
    return CompatibilityEvidence(
        compatibility_id=f"compat-{suffix}",
        identity=identity,
        status=status,
        verification_kind=verification_kind,
        checker=checker,
        checked_at="2026-08-20T00:01:00Z",
        reason_codes=("SYNTHETIC_TEST_EVIDENCE",),
        details={"fixture": True},
        source_revision=source_revision,
        environment=environment,
        command=command,
        result_ref=result_ref,
    )


def transition(
    record: StrategyVersionRecord,
    previous_state: str,
    new_state: str,
    expected_revision: int,
    *,
    suffix: str,
    primary_evidence_id: str | None = None,
) -> LifecycleTransitionRecord:
    return LifecycleTransitionRecord(
        transition_id=f"transition-{suffix}",
        identity=record.identity,
        previous_state=previous_state,
        new_state=new_state,
        changed_at="2026-08-20T08:00:00Z",
        changed_by="unit-test",
        reason_codes=("SYNTHETIC_AUTHORITY_TEST",),
        primary_evidence_id=primary_evidence_id,
        expected_registry_revision=expected_revision,
        resulting_registry_revision=expected_revision + 1,
    )


def backtest_payload(record: StrategyVersionRecord, result_id: str) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "backtest_result_id": result_id,
        "strategy_id": record.identity.strategy_id,
        "strategy_version": record.identity.strategy_version,
        "strategy_content_hash": record.content_hash,
        "runtime_version": "0.1.0",
        "dataset_id": "synthetic-dataset",
        "dataset_hash": "sha256:dataset",
        "dataset_start": "2026-08-20T00:00:00Z",
        "dataset_end": "2026-08-20T06:00:00Z",
        "cost_model_version": "test-cost-v1",
        "created_at": "2026-08-20T07:00:00Z",
        "total_trades": 1,
        "wins": 1,
        "losses": 0,
        "breakeven": 0,
        "gross_pnl": "1",
        "net_pnl": "1",
        "total_fees": "0",
        "profit_factor": None,
        "expectancy": "1",
        "max_drawdown": "0",
        "max_consecutive_losses": 0,
    }


def decision_payload(
    record: StrategyVersionRecord,
    backtest_result_id: str,
    decision_id: str,
    *,
    decision: str = "PASS",
) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "validation_decision_id": decision_id,
        "strategy_id": record.identity.strategy_id,
        "strategy_version": record.identity.strategy_version,
        "backtest_result_id": backtest_result_id,
        "validation_policy_version": "test-policy-v1",
        "decision": decision,
        "reason_codes": ["SYNTHETIC_TEST_DECISION"],
        "decided_at": "2026-08-20T07:01:00Z",
    }


def validation_record(
    *,
    evidence_id: str,
    evidence_type: str,
    upstream_object_id: str,
    strategy: StrategyVersionRecord,
    payload: dict,
    producer: str = "E3",
    decision: str | None = None,
    parent_evidence_id: str | None = None,
    strategy_content_hash: str | None = None,
    verification_status: str = "PASS",
    verification_kind: str = "LOCAL_EXECUTION",
    source_revision: str | None = "e3-synthetic-revision",
    environment: str | None = "local-test-fixture",
    command: str | None = "synthetic-e3-local-test",
    result_ref: str | None = "synthetic-pass",
) -> ValidationEvidenceRecord:
    return ValidationEvidenceRecord(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        upstream_object_id=upstream_object_id,
        identity=strategy.identity,
        strategy_content_hash=strategy_content_hash or strategy.content_hash,
        upstream_schema_version="contracts-v0.1",
        producer=producer,
        payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        recorded_at="2026-08-20T07:02:00Z",
        verification_status=verification_status,
        verification_kind=verification_kind,
        decision=decision,
        parent_evidence_id=parent_evidence_id,
        source_revision=source_revision,
        environment=environment,
        command=command,
        result_ref=result_ref,
    )


class LocalPassE2Boundary:
    def check(self, definition: dict) -> CompatibilityEvidence:
        return compatibility(
            StrategyIdentity(definition["strategy_id"], definition["strategy_version"]),
            suffix=definition["strategy_id"],
        )


LOCAL_E3_PASS = {
    "verification_status": "PASS",
    "verification_kind": "LOCAL_EXECUTION",
    "source_revision": "e3-synthetic-revision",
    "environment": "local-test-fixture",
    "command": "synthetic-e3-local-test",
    "result_ref": "synthetic-pass",
}


class LifecycleEvidenceAuthorityTests(unittest.TestCase):
    def _new_store(self, strategy_id: str):
        connection = connect(":memory:")
        apply_migrations(connection)
        store = SQLiteRegistryStore(connection)
        record = strategy_record(strategy_id)
        store.register_strategy(record)
        return connection, store, record

    def _to_backtesting(self, store, record) -> None:
        store.save_compatibility(compatibility(record.identity, suffix=record.identity.strategy_id))
        store.append_transition(
            transition(record, "DRAFT", "BACKTESTING", 0, suffix=f"{record.identity.strategy_id}-bt")
        )

    def _snapshot(self, connection, store, identity):
        current = store.get_strategy(identity)
        self.assertIsNotNone(current)
        count = connection.execute("SELECT COUNT(*) FROM lifecycle_transitions").fetchone()[0]
        return current.current_lifecycle_state, current.registry_revision, count

    def _assert_rejected_unchanged(self, connection, store, record, action) -> None:
        before = self._snapshot(connection, store, record.identity)
        with self.assertRaises(EvidenceGateError):
            action()
        self.assertEqual(before, self._snapshot(connection, store, record.identity))

    def _save_backtest(self, store, record, suffix: str, **overrides):
        result_id = f"bt-{suffix}"
        kwargs = dict(
            evidence_id=f"evidence-bt-{suffix}",
            evidence_type="BACKTEST_RESULT",
            upstream_object_id=result_id,
            strategy=record,
            payload=backtest_payload(record, result_id),
        )
        kwargs.update(overrides)
        evidence = validation_record(**kwargs)
        store.save_validation_evidence(evidence)
        return evidence

    def _save_decision(self, store, record, backtest, suffix: str, *, decision="PASS", payload=None, **overrides):
        decision_id = f"vd-{suffix}"
        kwargs = dict(
            evidence_id=f"evidence-vd-{suffix}",
            evidence_type="VALIDATION_DECISION",
            upstream_object_id=decision_id,
            strategy=record,
            payload=payload or decision_payload(record, backtest.upstream_object_id, decision_id, decision=decision),
            decision=decision,
            parent_evidence_id=backtest.evidence_id,
        )
        kwargs.update(overrides)
        evidence = validation_record(**kwargs)
        store.save_validation_evidence(evidence)
        return evidence

    def test_direct_backtesting_requires_durable_e2_authority_and_rolls_back(self) -> None:
        variants = (
            ("no-compatibility", None),
            ("non-e2", {"checker": "OTHER_CHECKER"}),
            ("non-pass", {"status": "FAIL"}),
            ("non-local", {"verification_kind": "STATIC_REVIEW"}),
            ("missing-source-revision", {"source_revision": None}),
            ("missing-environment", {"environment": None}),
            ("missing-command", {"command": None}),
            ("missing-result-ref", {"result_ref": None}),
        )
        for index, (name, overrides) in enumerate(variants):
            with self.subTest(name=name):
                connection, store, record = self._new_store(f"draft-authority-{index}")
                try:
                    if overrides is not None:
                        store.save_compatibility(compatibility(record.identity, suffix=name, **overrides))
                    self._assert_rejected_unchanged(
                        connection,
                        store,
                        record,
                        lambda: store.append_transition(
                            transition(record, "DRAFT", "BACKTESTING", 0, suffix=name)
                        ),
                    )
                finally:
                    connection.close()

    def test_candidate_requires_primary_validation_decision(self) -> None:
        connection, store, record = self._new_store("candidate-no-primary")
        try:
            self._to_backtesting(store, record)
            self._assert_rejected_unchanged(
                connection, store, record,
                lambda: store.append_transition(
                    transition(record, "BACKTESTING", "CANDIDATE", 1, suffix="no-primary")
                ),
            )
        finally:
            connection.close()

    def test_candidate_rejects_wrong_primary_evidence_type(self) -> None:
        connection, store, record = self._new_store("candidate-wrong-type")
        try:
            self._to_backtesting(store, record)
            backtest = self._save_backtest(store, record, "wrong-type")
            self._assert_rejected_unchanged(
                connection, store, record,
                lambda: store.append_transition(
                    transition(record, "BACKTESTING", "CANDIDATE", 1, suffix="wrong-type", primary_evidence_id=backtest.evidence_id)
                ),
            )
        finally:
            connection.close()

    def test_candidate_rejects_non_pass_validation_decisions(self) -> None:
        for value in ("FAIL", "BLOCKED", "NOT_RUN"):
            with self.subTest(decision=value):
                connection, store, record = self._new_store(f"decision-{value.lower()}")
                try:
                    self._to_backtesting(store, record)
                    backtest = self._save_backtest(store, record, value.lower())
                    decision = self._save_decision(store, record, backtest, value.lower(), decision=value)
                    self._assert_rejected_unchanged(
                        connection, store, record,
                        lambda: store.append_transition(
                            transition(record, "BACKTESTING", "CANDIDATE", 1, suffix=value.lower(), primary_evidence_id=decision.evidence_id)
                        ),
                    )
                finally:
                    connection.close()

    def test_candidate_rejects_wrong_strategy_identity_or_content_hash(self) -> None:
        connection, store, record = self._new_store("candidate-target")
        try:
            self._to_backtesting(store, record)
            other = strategy_record("candidate-other")
            store.register_strategy(other)
            other_backtest = self._save_backtest(store, other, "other")
            other_decision = self._save_decision(store, other, other_backtest, "other")
            self._assert_rejected_unchanged(
                connection, store, record,
                lambda: store.append_transition(
                    transition(record, "BACKTESTING", "CANDIDATE", 1, suffix="wrong-identity", primary_evidence_id=other_decision.evidence_id)
                ),
            )

            backtest = self._save_backtest(store, record, "wrong-hash-parent")
            decision = self._save_decision(
                store, record, backtest, "wrong-hash",
                strategy_content_hash="sha256:not-the-registered-content",
            )
            self._assert_rejected_unchanged(
                connection, store, record,
                lambda: store.append_transition(
                    transition(record, "BACKTESTING", "CANDIDATE", 1, suffix="wrong-hash", primary_evidence_id=decision.evidence_id)
                ),
            )
        finally:
            connection.close()

    def test_candidate_rejects_missing_or_wrong_backtest_parent(self) -> None:
        for case in ("missing", "wrong-strategy"):
            with self.subTest(case=case):
                connection, store, record = self._new_store(f"parent-{case}")
                try:
                    self._to_backtesting(store, record)
                    placeholder = self._save_backtest(store, record, f"placeholder-{case}")
                    parent_id = None
                    if case == "wrong-strategy":
                        other = strategy_record(f"other-parent-{case}")
                        store.register_strategy(other)
                        parent_id = self._save_backtest(store, other, f"wrong-{case}").evidence_id
                    decision = validation_record(
                        evidence_id=f"evidence-vd-parent-{case}",
                        evidence_type="VALIDATION_DECISION",
                        upstream_object_id=f"vd-parent-{case}",
                        strategy=record,
                        payload=decision_payload(record, placeholder.upstream_object_id, f"vd-parent-{case}"),
                        decision="PASS",
                        parent_evidence_id=parent_id,
                    )
                    store.save_validation_evidence(decision)
                    self._assert_rejected_unchanged(
                        connection, store, record,
                        lambda: store.append_transition(
                            transition(record, "BACKTESTING", "CANDIDATE", 1, suffix=f"parent-{case}", primary_evidence_id=decision.evidence_id)
                        ),
                    )
                finally:
                    connection.close()

    def test_candidate_rejects_malformed_or_mismatched_canonical_binding(self) -> None:
        for case in ("malformed-decision", "mismatched-backtest-id"):
            with self.subTest(case=case):
                connection, store, record = self._new_store(f"canonical-{case}")
                try:
                    self._to_backtesting(store, record)
                    backtest = self._save_backtest(store, record, f"canonical-{case}")
                    payload = decision_payload(record, backtest.upstream_object_id, f"vd-canonical-{case}")
                    if case == "malformed-decision":
                        payload.pop("reason_codes")
                    else:
                        payload["backtest_result_id"] = "bt-different"
                    decision = self._save_decision(store, record, backtest, f"canonical-{case}", payload=payload)
                    self._assert_rejected_unchanged(
                        connection, store, record,
                        lambda: store.append_transition(
                            transition(record, "BACKTESTING", "CANDIDATE", 1, suffix=f"canonical-{case}", primary_evidence_id=decision.evidence_id)
                        ),
                    )
                finally:
                    connection.close()

    def test_candidate_rejects_missing_or_nonlocal_metadata_on_decision_or_backtest(self) -> None:
        cases = (
            ("decision-nonlocal", "decision", {"verification_kind": "STATIC_REVIEW"}),
            ("decision-missing-metadata", "decision", {"source_revision": None}),
            ("backtest-nonlocal", "backtest", {"verification_kind": "STATIC_REVIEW"}),
            ("backtest-missing-metadata", "backtest", {"result_ref": None}),
        )
        for name, target, overrides in cases:
            with self.subTest(name=name):
                connection, store, record = self._new_store(name)
                try:
                    self._to_backtesting(store, record)
                    backtest = self._save_backtest(
                        store, record, name,
                        **(overrides if target == "backtest" else {}),
                    )
                    decision = self._save_decision(
                        store, record, backtest, name,
                        **(overrides if target == "decision" else {}),
                    )
                    self._assert_rejected_unchanged(
                        connection, store, record,
                        lambda: store.append_transition(
                            transition(record, "BACKTESTING", "CANDIDATE", 1, suffix=name, primary_evidence_id=decision.evidence_id)
                        ),
                    )
                finally:
                    connection.close()

    def test_service_authorized_backtesting_flow_still_works(self) -> None:
        connection = connect(":memory:")
        try:
            apply_migrations(connection)
            store = SQLiteRegistryStore(connection)
            service = StrategyPlatformService(store, LocalPassE2Boundary())
            outcome = service.intake(strategy_payload("service-backtesting"), source_actor="unit-test")
            result = service.begin_backtesting(outcome.strategy.identity, actor="unit-test")
            self.assertEqual("BACKTESTING", result.current_lifecycle_state)
            self.assertEqual(1, result.registry_revision)
        finally:
            connection.close()

    def test_service_authorized_candidate_flow_still_works(self) -> None:
        connection = connect(":memory:")
        try:
            apply_migrations(connection)
            store = SQLiteRegistryStore(connection)
            service = StrategyPlatformService(store, LocalPassE2Boundary())
            outcome = service.intake(strategy_payload("service-candidate"), source_actor="unit-test")
            backtesting = service.begin_backtesting(outcome.strategy.identity, actor="unit-test")
            backtest = service.record_backtest_result(
                backtest_payload(backtesting, "bt-service-candidate"), **LOCAL_E3_PASS
            )
            decision = service.record_validation_decision(
                decision_payload(backtesting, "bt-service-candidate", "vd-service-candidate"),
                backtest_evidence_id=backtest.evidence_id,
                **LOCAL_E3_PASS,
            )
            candidate = service.mark_candidate(
                outcome.strategy.identity,
                actor="unit-test",
                validation_evidence_id=decision.evidence_id,
            )
            self.assertEqual("CANDIDATE", candidate.current_lifecycle_state)
            self.assertEqual(2, candidate.registry_revision)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
