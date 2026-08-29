import copy
import unittest
from dataclasses import replace

from src.integration.runtime_preflight import (
    ELIGIBLE,
    FAIL_CLOSED,
    RuntimePreflightAuthority,
    RuntimePreflightInput,
    RuntimePreflightValidationError,
    evaluate_runtime_preflight,
    runtime_preflight_evidence_is_current,
    stable_runtime_preflight_id,
    validate_runtime_preflight_evidence,
)


class RuntimePreflightV01Tests(unittest.TestCase):
    def setUp(self):
        self.revision = "a" * 40
        self.revision_hash = "sha256:" + "1" * 64
        self.mode_hash = "sha256:" + "2" * 64
        self.config_hash = "sha256:" + "3" * 64
        self.heartbeat_policy_hash = "sha256:" + "4" * 64
        self.supervisor_hash = "sha256:" + "5" * 64
        self.capability_hash = "sha256:" + "6" * 64
        self.reconciliation_hash = "sha256:" + "7" * 64
        self.authorization_capability_hash = self.capability_hash
        self.consumer_config_hash = "sha256:" + "8" * 64
        self.consumer_evidence_hash = "sha256:" + "9" * 64

    def _heartbeat(self, **changes):
        value = {
            "heartbeat_source_id": "heartbeat-fixture-001",
            "heartbeat_policy_generation_id": "heartbeat-policy-gen-001",
            "heartbeat_policy_hash": self.heartbeat_policy_hash,
            "heartbeat_process_instance_id": "process-fixture-001",
            "heartbeat_process_start_generation_id": "process-start-gen-001",
            "heartbeat_observed_at": "2026-08-29T12:00:02Z",
            "heartbeat_received_at": "2026-08-29T12:00:03Z",
            "heartbeat_freshness_status": "FRESH",
        }
        value.update(changes)
        return value

    def _supervisor(self, *, present=False, **changes):
        value = {
            "supervisor_present": present,
            "supervisor_id": "supervisor-fixture-001" if present else None,
            "supervisor_generation_id": "supervisor-gen-001" if present else None,
            "supervisor_config_hash": self.supervisor_hash if present else None,
            "supervisor_compatibility_status": "ACCEPTED" if present else "NOT_APPLICABLE",
            "restart_permission_status": "ALLOWED_BY_CURRENT_EVIDENCE" if present else "NOT_APPLICABLE",
        }
        value.update(changes)
        return value

    def _capability(self, **changes):
        value = {
            "capability_snapshot_ref": "capability-fixture-001",
            "capability_snapshot_hash": self.capability_hash,
            "capability_generation_id": "capability-gen-001",
            "required_action_ids": ["PREPARE_EXACT_REVISION"],
            "registered_action_ids": ["PREPARE_EXACT_REVISION"],
            "allowlisted_action_ids": ["PREPARE_EXACT_REVISION"],
            "capability_status": "READY",
        }
        value.update(changes)
        return value

    def _reconciliation(self, **changes):
        value = {
            "reconciliation_ref": "reconciliation-fixture-001",
            "reconciliation_hash": self.reconciliation_hash,
            "reconciliation_generation_id": "reconciliation-gen-001",
            "reconciliation_observed_at": "2026-08-29T12:00:03Z",
            "reconciliation_status": "READY",
            "fresh_reconciliation_required": False,
        }
        value.update(changes)
        return value

    def _dependency(self, **changes):
        value = {
            "owner": "E5",
            "evidence_class": "RISK_READINESS",
            "evidence_ref": "risk-readiness-fixture-001",
            "evidence_hash": "sha256:" + "b" * 64,
            "evidence_generation_id": "risk-readiness-gen-001",
            "observed_at": "2026-08-29T12:00:03Z",
            "readiness_status": "READY",
        }
        value.update(changes)
        return value

    def _external_consumer(self, **changes):
        value = {
            "external_consumer_id": "agentbridge-fixture-001",
            "external_consumer_generation_id": "agentbridge-gen-001",
            "external_consumer_config_hash": self.consumer_config_hash,
            "compatibility_profile_ref": "adr0010-consumer-fixture-001",
            "compatibility_evidence_hash": self.consumer_evidence_hash,
            "compatibility_status": "ACCEPTED",
            "compatibility_observed_at": "2026-08-29T12:00:03Z",
        }
        value.update(changes)
        return value

    def _authorization(self, *, role="CREDENTIAL_FREE_LOCAL_VERIFICATION", status="VALID", **changes):
        class_by_role = {
            "CREDENTIAL_FREE_LOCAL_VERIFICATION": "CREDENTIAL_FREE_TASK",
            "PROVIDER_READ_ONLY_OBSERVATION": "PROVIDER_READ_ONLY",
            "SHADOW_RUNTIME": "SHADOW_RUNTIME",
            "PAPER_RUNTIME": "PAPER_RUNTIME",
            "BOUNDED_LIVE_FIRE_RUNTIME": "BOUNDED_LIVE_FIRE_RUNTIME",
        }
        value = {
            "authorization_class": class_by_role[role],
            "authorization_ref": f"authorization-fixture-{role.lower()}",
            "authorization_generation_id": f"authorization-gen-{role.lower()}",
            "authorized_project_revision": self.revision,
            "authorized_runtime_role": role,
            "authorized_capability_set_hash": self.authorization_capability_hash,
            "authorization_status": status,
        }
        value.update(changes)
        return value

    def _input(
        self,
        *,
        role="CREDENTIAL_FREE_LOCAL_VERIFICATION",
        launch_intent="START",
        mode=None,
        supervisor=None,
        dependencies=None,
        external_consumer=None,
        authorization=None,
        **changes,
    ):
        if mode is None:
            mode = {
                "CREDENTIAL_FREE_LOCAL_VERIFICATION": "RESEARCH",
                "PROVIDER_READ_ONLY_OBSERVATION": "RESEARCH",
                "SHADOW_RUNTIME": "SHADOW",
                "PAPER_RUNTIME": "PAPER",
                "BOUNDED_LIVE_FIRE_RUNTIME": "LIVE",
            }[role]
        if supervisor is None:
            supervisor = self._supervisor(present=role in {"SHADOW_RUNTIME", "PAPER_RUNTIME", "BOUNDED_LIVE_FIRE_RUNTIME"})
        if dependencies is None:
            dependencies = [] if role == "CREDENTIAL_FREE_LOCAL_VERIFICATION" else [self._dependency()]
        if external_consumer is None and role in {"SHADOW_RUNTIME", "PAPER_RUNTIME", "BOUNDED_LIVE_FIRE_RUNTIME"}:
            external_consumer = self._external_consumer()
        if authorization is None:
            authorization = self._authorization(role=role)
        value = RuntimePreflightInput(
            schema_version="contracts-v0.1",
            runtime_preflight_profile_version="runtime-preflight-v0.1",
            runtime_role=role,
            launch_intent=launch_intent,
            evaluated_at="2026-08-29T12:00:04Z",
            project_revision=self.revision,
            revision_authority_ref="revision-authority-fixture-001",
            revision_authority_hash=self.revision_hash,
            worktree_classification="EXACT_CLEAN",
            requested_operational_mode=mode,
            operational_mode_transition_id="opmode-fixture-001",
            operational_mode_revision=7,
            operational_mode_payload_hash=self.mode_hash,
            runtime_config_generation_id="runtime-config-gen-001",
            runtime_config_hash=self.config_hash,
            process_instance_id="process-fixture-001",
            process_start_generation_id="process-start-gen-001",
            process_started_at="2026-08-29T12:00:01Z",
            single_instance_status="SINGLE",
            heartbeat_evidence=self._heartbeat(),
            supervisor_evidence=supervisor,
            capability_evidence=self._capability(),
            reconciliation_evidence=self._reconciliation(),
            dependency_evidence=tuple(dependencies),
            external_consumer_evidence=external_consumer,
            authorization_evidence=authorization,
        )
        return replace(value, **changes) if changes else value

    def _authority(self, value, *, required_dependencies=None, **changes):
        if required_dependencies is None:
            required_dependencies = tuple(
                {
                    "owner": item["owner"],
                    "evidence_class": item["evidence_class"],
                    "evidence_ref": item["evidence_ref"],
                    "evidence_hash": item["evidence_hash"],
                    "evidence_generation_id": item["evidence_generation_id"],
                }
                for item in value.dependency_evidence
            )
        supervisor = value.supervisor_evidence
        external = value.external_consumer_evidence
        authority = RuntimePreflightAuthority(
            revision_authority={
                "project_revision": self.revision,
                "revision_authority_ref": "revision-authority-fixture-001",
                "revision_authority_hash": self.revision_hash,
                "worktree_classification": "EXACT_CLEAN",
            },
            operational_mode_authority={
                "transition_id": "opmode-fixture-001",
                "mode_revision": 7,
                "mode": value.requested_operational_mode,
                "payload_hash": self.mode_hash,
            },
            runtime_config_authority={
                "runtime_config_generation_id": "runtime-config-gen-001",
                "runtime_config_hash": self.config_hash,
            },
            heartbeat_policy_authority={
                "heartbeat_policy_generation_id": "heartbeat-policy-gen-001",
                "heartbeat_policy_hash": self.heartbeat_policy_hash,
            },
            supervisor_authority=(
                None
                if not supervisor["supervisor_present"]
                else {
                    "supervisor_generation_id": "supervisor-gen-001",
                    "supervisor_config_hash": self.supervisor_hash,
                }
            ),
            capability_authority={
                "capability_snapshot_ref": "capability-fixture-001",
                "capability_snapshot_hash": self.capability_hash,
                "capability_generation_id": "capability-gen-001",
            },
            reconciliation_authority={
                "reconciliation_ref": "reconciliation-fixture-001",
                "reconciliation_hash": self.reconciliation_hash,
                "reconciliation_generation_id": "reconciliation-gen-001",
            },
            required_dependencies=required_dependencies,
            external_consumer_authority=(
                None
                if external is None
                else {
                    "external_consumer_id": external["external_consumer_id"],
                    "external_consumer_generation_id": external["external_consumer_generation_id"],
                    "external_consumer_config_hash": external["external_consumer_config_hash"],
                    "compatibility_profile_ref": external["compatibility_profile_ref"],
                    "compatibility_evidence_hash": external["compatibility_evidence_hash"],
                }
            ),
            authorization_authority=copy.deepcopy(value.authorization_evidence),
        )
        return replace(authority, **changes) if changes else authority

    def _evaluate(self, value=None, authority=None):
        value = self._input() if value is None else value
        authority = self._authority(value) if authority is None else authority
        return evaluate_runtime_preflight(value, authority)

    def test_coherent_credential_free_evidence_is_eligible_without_runtime_authority_side_effects(self):
        value = self._input()
        evidence = self._evaluate(value)
        self.assertEqual(ELIGIBLE, evidence["preflight_status"])
        self.assertEqual(["RUNTIME_PREFLIGHT_ELIGIBLE"], evidence["reason_codes"])
        validate_runtime_preflight_evidence(evidence)
        for forbidden in (
            "provider_mutation_authorized",
            "order_authorized",
            "process_launch_authorized",
            "restart_executed",
            "shadow_authorized",
            "paper_authorized",
            "live_authorized",
            "capital_authorized",
        ):
            self.assertNotIn(forbidden, evidence)

    def test_same_exact_evidence_is_deterministic_and_identity_stable(self):
        value = self._input()
        authority = self._authority(value)
        first = evaluate_runtime_preflight(value, authority)
        second = evaluate_runtime_preflight(value, authority)
        self.assertEqual(first, second)
        self.assertEqual(first["runtime_preflight_id"], stable_runtime_preflight_id(first))
        self.assertTrue(runtime_preflight_evidence_is_current(first, value, authority))

    def test_role_substitution_is_not_transferable(self):
        credential_free = self._input()
        credential_free_evidence = self._evaluate(credential_free)
        shadow = replace(
            credential_free,
            runtime_role="SHADOW_RUNTIME",
            requested_operational_mode="SHADOW",
        )
        shadow_authority = self._authority(
            shadow,
            operational_mode_authority={
                "transition_id": "opmode-fixture-001",
                "mode_revision": 7,
                "mode": "SHADOW",
                "payload_hash": self.mode_hash,
            },
        )
        shadow_evidence = evaluate_runtime_preflight(shadow, shadow_authority)
        self.assertEqual(FAIL_CLOSED, shadow_evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", shadow_evidence["reason_codes"])
        self.assertIn("PREFLIGHT_ROLE_AUTHORITY_EXCEEDED", shadow_evidence["reason_codes"])
        self.assertNotEqual(credential_free_evidence["runtime_preflight_id"], shadow_evidence["runtime_preflight_id"])

    def test_revision_mismatch_and_non_exact_clean_worktree_fail_closed(self):
        value = self._input(project_revision="b" * 40)
        evidence = self._evaluate(value, self._authority(value))
        self.assertIn("PREFLIGHT_REVISION_MISMATCH", evidence["reason_codes"])

        dirty = self._input(worktree_classification="CLEAN_UNQUALIFIED")
        evidence = self._evaluate(dirty, self._authority(dirty))
        self.assertIn("PREFLIGHT_WORKTREE_NOT_EXACT_CLEAN", evidence["reason_codes"])

    def test_operational_mode_value_and_generation_mismatch_fail_closed(self):
        value = self._input(requested_operational_mode="PAUSED")
        authority = self._authority(
            value,
            operational_mode_authority={
                "transition_id": "opmode-fixture-001",
                "mode_revision": 7,
                "mode": "RESEARCH",
                "payload_hash": self.mode_hash,
            },
        )
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertIn("PREFLIGHT_OPERATIONAL_MODE_MISMATCH", evidence["reason_codes"])

        value = self._input(operational_mode_revision=8)
        evidence = self._evaluate(value, self._authority(value))
        self.assertIn("PREFLIGHT_OPERATIONAL_MODE_GENERATION_CONFLICT", evidence["reason_codes"])

    def test_config_generation_mismatch_fails_closed(self):
        value = self._input(runtime_config_generation_id="runtime-config-gen-other")
        evidence = self._evaluate(value, self._authority(value))
        self.assertIn("PREFLIGHT_CONFIG_GENERATION_MISMATCH", evidence["reason_codes"])

    def test_duplicate_or_unknown_single_instance_fails_closed(self):
        for status in ("CONFLICT", "UNKNOWN"):
            with self.subTest(status=status):
                evidence = self._evaluate(self._input(single_instance_status=status))
                self.assertIn("PREFLIGHT_SINGLE_INSTANCE_CONFLICT", evidence["reason_codes"])

    def test_heartbeat_stale_unknown_wrong_process_prior_boot_and_temporal_order_fail_closed(self):
        cases = (
            (self._heartbeat(heartbeat_freshness_status="STALE"), "PREFLIGHT_HEARTBEAT_STALE"),
            (self._heartbeat(heartbeat_freshness_status="UNKNOWN"), "PREFLIGHT_HEARTBEAT_STALE"),
            (self._heartbeat(heartbeat_process_instance_id="process-other"), "PREFLIGHT_HEARTBEAT_WRONG_PROCESS"),
            (self._heartbeat(heartbeat_process_start_generation_id="start-other"), "PREFLIGHT_HEARTBEAT_PRIOR_BOOT"),
            (self._heartbeat(heartbeat_observed_at="2026-08-29T12:00:00Z"), "PREFLIGHT_EVIDENCE_TIME_INVALID"),
            (self._heartbeat(heartbeat_received_at="2026-08-29T12:00:05Z"), "PREFLIGHT_EVIDENCE_TIME_INVALID"),
        )
        for heartbeat, reason in cases:
            with self.subTest(reason=reason):
                evidence = self._evaluate(self._input(heartbeat_evidence=heartbeat))
                self.assertIn(reason, evidence["reason_codes"])

    def test_heartbeat_policy_unknown_or_mismatched_fails_closed(self):
        heartbeat = self._heartbeat(heartbeat_policy_generation_id="heartbeat-policy-other")
        evidence = self._evaluate(self._input(heartbeat_evidence=heartbeat))
        self.assertIn("PREFLIGHT_HEARTBEAT_POLICY_UNKNOWN", evidence["reason_codes"])

    def test_supervisor_incompatible_unknown_and_restart_without_permission_fail_closed(self):
        for compatibility in ("NOT_ACCEPTED", "UNKNOWN"):
            with self.subTest(compatibility=compatibility):
                value = self._input(supervisor=self._supervisor(present=True, supervisor_compatibility_status=compatibility))
                evidence = self._evaluate(value, self._authority(value))
                self.assertIn("PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED", evidence["reason_codes"])

        value = self._input(
            launch_intent="RESTART",
            supervisor=self._supervisor(present=True, restart_permission_status="NOT_ALLOWED"),
        )
        evidence = self._evaluate(value, self._authority(value))
        self.assertIn("PREFLIGHT_RESTART_NOT_AUTHORIZED", evidence["reason_codes"])

    def test_required_action_registered_but_not_allowlisted_fails_closed(self):
        capability = self._capability(allowlisted_action_ids=[])
        evidence = self._evaluate(self._input(capability_evidence=capability))
        self.assertIn("PREFLIGHT_ACTION_CAPABILITY_NOT_ALLOWLISTED", evidence["reason_codes"])

    def test_required_action_allowlisted_but_not_registered_fails_closed(self):
        capability = self._capability(registered_action_ids=[])
        evidence = self._evaluate(self._input(capability_evidence=capability))
        self.assertIn("PREFLIGHT_ACTION_CAPABILITY_MISSING", evidence["reason_codes"])

    def test_capability_unknown_or_not_ready_fails_closed(self):
        for status in ("UNKNOWN", "NOT_READY"):
            with self.subTest(status=status):
                capability = self._capability(capability_status=status)
                evidence = self._evaluate(self._input(capability_evidence=capability))
                self.assertIn("PREFLIGHT_ACTION_CAPABILITY_MISSING", evidence["reason_codes"])

    def test_reconciliation_required_role_not_ready_or_fresh_required_fails_closed(self):
        for reconciliation in (
            self._reconciliation(reconciliation_status="NOT_READY"),
            self._reconciliation(reconciliation_status="UNKNOWN"),
            self._reconciliation(fresh_reconciliation_required=True),
        ):
            with self.subTest(reconciliation=reconciliation):
                value = self._input(role="PROVIDER_READ_ONLY_OBSERVATION", reconciliation_evidence=reconciliation)
                evidence = self._evaluate(value, self._authority(value))
                self.assertIn("PREFLIGHT_RECONCILIATION_NOT_READY", evidence["reason_codes"])

    def test_required_dependency_missing_not_ready_or_unknown_fails_closed(self):
        value = self._input(role="PROVIDER_READ_ONLY_OBSERVATION")
        required = self._authority(value).required_dependencies
        evidence = evaluate_runtime_preflight(value, self._authority(value, required_dependencies=required + ({
            "owner": "E4",
            "evidence_class": "PROVIDER_HEALTH",
            "evidence_ref": "provider-health-fixture-001",
            "evidence_hash": "sha256:" + "c" * 64,
            "evidence_generation_id": "provider-health-gen-001",
        },)))
        self.assertIn("PREFLIGHT_DEPENDENCY_EVIDENCE_NOT_READY", evidence["reason_codes"])

        for status in ("NOT_READY", "UNKNOWN"):
            with self.subTest(status=status):
                dependency = self._dependency(readiness_status=status)
                value = self._input(role="PROVIDER_READ_ONLY_OBSERVATION", dependencies=[dependency])
                evidence = self._evaluate(value, self._authority(value))
                self.assertIn("PREFLIGHT_DEPENDENCY_EVIDENCE_NOT_READY", evidence["reason_codes"])

    def test_required_external_consumer_missing_or_incompatible_for_shadow_fails_closed(self):
        value = self._input(role="SHADOW_RUNTIME", external_consumer_evidence=None)
        evidence = self._evaluate(value, self._authority(value))
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

        value = self._input(
            role="SHADOW_RUNTIME",
            external_consumer=self._external_consumer(compatibility_status="NOT_ACCEPTED"),
        )
        evidence = self._evaluate(value, self._authority(value))
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_authorization_statuses_fail_closed_and_consumed_is_distinct(self):
        for status in ("MISSING", "MISMATCH", "EXPIRED", "UNKNOWN"):
            with self.subTest(status=status):
                authorization = self._authorization(status=status)
                value = self._input(authorization=authorization)
                evidence = self._evaluate(value, self._authority(value))
                self.assertIn("PREFLIGHT_RUNTIME_AUTHORITY_UNKNOWN", evidence["reason_codes"])
        authorization = self._authorization(status="CONSUMED")
        value = self._input(authorization=authorization)
        evidence = self._evaluate(value, self._authority(value))
        self.assertIn("PREFLIGHT_RUNTIME_AUTHORITY_CONSUMED", evidence["reason_codes"])

    def test_authorization_role_revision_or_capability_mismatch_fails_closed(self):
        mismatches = (
            {"authorization_class": "SHADOW_RUNTIME"},
            {"authorized_runtime_role": "SHADOW_RUNTIME"},
            {"authorized_project_revision": "b" * 40},
            {"authorized_capability_set_hash": "sha256:" + "d" * 64},
        )
        for changes in mismatches:
            with self.subTest(changes=changes):
                authorization = self._authorization(**changes)
                value = self._input(authorization=authorization)
                evidence = self._evaluate(value, self._authority(value))
                self.assertIn("PREFLIGHT_ROLE_AUTHORITY_EXCEEDED", evidence["reason_codes"])

    def test_bounded_live_fire_mode_policy_remains_undefined(self):
        value = self._input(role="BOUNDED_LIVE_FIRE_RUNTIME")
        evidence = self._evaluate(value, self._authority(value))
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_ROLE_MODE_POLICY_UNDEFINED", evidence["reason_codes"])

    def test_corrupt_identity_is_rejected_by_validator(self):
        evidence = self._evaluate()
        corrupt = dict(evidence)
        corrupt["runtime_preflight_id"] = "runtimepreflight_" + "0" * 64
        with self.assertRaises(RuntimePreflightValidationError) as caught:
            validate_runtime_preflight_evidence(corrupt)
        self.assertEqual("PREFLIGHT_EVIDENCE_IDENTITY_INVALID", caught.exception.code)

    def test_provider_role_fixture_is_synthetic_and_does_not_create_repository_authority(self):
        value = self._input(role="SHADOW_RUNTIME")
        evidence = self._evaluate(value, self._authority(value))
        self.assertIn(evidence["preflight_status"], {ELIGIBLE, FAIL_CLOSED})
        self.assertNotIn("product_owner_authorization_created", evidence)
        self.assertNotIn("provider_request", evidence)
        self.assertNotIn("credential", evidence)
        self.assertNotIn("process_launch", evidence)
        self.assertNotIn("provider_mutation", evidence)
        self.assertNotIn("capital_exposure", evidence)


class RuntimePreflightExternalConsumerParticipationRegressionTests(unittest.TestCase):
    """E7-113/E7-114 regression definitions for conditional external-consumer participation."""

    def setUp(self):
        self.fixture = RuntimePreflightV01Tests(
            methodName="test_coherent_credential_free_evidence_is_eligible_without_runtime_authority_side_effects"
        )
        self.fixture.setUp()

    def _external_authority(self, **changes):
        external = self.fixture._external_consumer()
        value = {
            "external_consumer_id": external["external_consumer_id"],
            "external_consumer_generation_id": external["external_consumer_generation_id"],
            "external_consumer_config_hash": external["external_consumer_config_hash"],
            "compatibility_profile_ref": external["compatibility_profile_ref"],
            "compatibility_evidence_hash": external["compatibility_evidence_hash"],
        }
        value.update(changes)
        return value

    def test_credential_free_current_external_authority_without_evidence_fails_closed(self):
        value = self.fixture._input()
        authority = self.fixture._authority(
            value,
            external_consumer_authority=self._external_authority(),
        )
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_provider_read_only_current_external_authority_without_evidence_fails_closed(self):
        value = self.fixture._input(role="PROVIDER_READ_ONLY_OBSERVATION")
        authority = self.fixture._authority(
            value,
            external_consumer_authority=self._external_authority(),
        )
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_credential_free_no_external_participation_remains_eligible(self):
        value = self.fixture._input()
        authority = self.fixture._authority(value, external_consumer_authority=None)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(ELIGIBLE, evidence["preflight_status"])
        self.assertEqual(["RUNTIME_PREFLIGHT_ELIGIBLE"], evidence["reason_codes"])

    def test_exact_current_external_evidence_and_authority_remain_admissible(self):
        external = self.fixture._external_consumer()
        value = self.fixture._input(external_consumer=external)
        authority = self.fixture._authority(value)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(ELIGIBLE, evidence["preflight_status"])
        self.assertEqual(["RUNTIME_PREFLIGHT_ELIGIBLE"], evidence["reason_codes"])

    def test_external_evidence_without_current_authority_fails_closed(self):
        external = self.fixture._external_consumer()
        value = self.fixture._input(external_consumer=external)
        authority = self.fixture._authority(value, external_consumer_authority=None)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_mismatched_or_incompatible_external_consumer_fails_closed(self):
        external = self.fixture._external_consumer()
        value = self.fixture._input(external_consumer=external)
        authority = self.fixture._authority(
            value,
            external_consumer_authority=self._external_authority(
                external_consumer_generation_id="agentbridge-gen-stale"
            ),
        )
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

        incompatible = self.fixture._external_consumer(compatibility_status="NOT_ACCEPTED")
        value = self.fixture._input(external_consumer=incompatible)
        authority = self.fixture._authority(value)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_shadow_external_consumer_requirement_remains_unconditional(self):
        value = self.fixture._input(role="SHADOW_RUNTIME")
        value = replace(value, external_consumer_evidence=None)
        authority = self.fixture._authority(value, external_consumer_authority=None)
        evidence = evaluate_runtime_preflight(value, authority)
        self.assertEqual(FAIL_CLOSED, evidence["preflight_status"])
        self.assertIn("PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED", evidence["reason_codes"])

    def test_regression_path_creates_no_runtime_or_financial_authority_fields(self):
        value = self.fixture._input()
        authority = self.fixture._authority(
            value,
            external_consumer_authority=self._external_authority(),
        )
        evidence = evaluate_runtime_preflight(value, authority)
        for forbidden in (
            "provider_request",
            "credential",
            "provider_mutation_authorized",
            "process_launch_authorized",
            "restart_executed",
            "order_authorized",
            "shadow_authorized",
            "paper_authorized",
            "live_authorized",
            "capital_authorized",
        ):
            self.assertNotIn(forbidden, evidence)


if __name__ == "__main__":
    unittest.main()
