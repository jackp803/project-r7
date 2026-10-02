from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .contract_validation import (
    validate_backtest_result_contract,
    validate_validation_decision_contract,
    validate_verification_metadata,
)
from .lifecycle_authority import (
    require_backtesting_authority,
    require_candidate_authority,
    require_rejection_authority,
)
from .models import StrategyIdentity, StrategyVersionRecord, ValidationEvidenceRecord
from .service_base import DeferredCompatibilityBoundary
from .service_base import StrategyPlatformService as _StrategyPlatformServiceBase


class StrategyPlatformService(_StrategyPlatformServiceBase):
    """Public E6 platform service with fail-closed evidence and lifecycle authority gates."""

    def product_assessment(self,run_id):
        return self._store.get_product_assessment(run_id)

    def record_product_assessment(self,identity,*,run_id,actor):
        import json
        from application.research.product_assessment import ExecutedProductAssessmentBoundary
        from .models import EvidenceGateError
        from .product_assessment import ProductAssessmentRecord,_PRODUCT_EVIDENCE_CAPABILITY,canonical,digest
        from .service_base import _utc_now
        boundary=getattr(self,'_product_assessment_boundary',None)
        if not isinstance(boundary,ExecutedProductAssessmentBoundary):
            raise EvidenceGateError('Configured actual product assessment boundary required')
        resolved=boundary.resolve(run_id)
        strategy=self._require_strategy(identity)
        inputs=json.loads(resolved.inputs_json); product=json.loads(resolved.assessment_json)
        definition=inputs['strategy']
        if (definition['strategy_id'],definition['strategy_version'],definition['content_hash'])!=(identity.strategy_id,identity.strategy_version,strategy.content_hash):
            raise EvidenceGateError('Product evidence bound to another strategy version')
        if resolved.namespace!=self._store.get_research_namespace(): raise EvidenceGateError('Product namespace mismatch')
        risk=inputs.get('risk_policy'); risk_raw=None
        if risk is not None:
            from risk.product_policy import parse_product_risk_policy
            risk_raw=parse_product_risk_policy(risk,namespace=resolved.namespace).canonical_json
        decision=None
        if product.get('sealed_backtest') is not None:
            metadata=dict(verification_status='PASS',verification_kind='LOCAL_EXECUTION',
                source_revision=inputs['implementation_hash'],environment=inputs['provenance']['os']+'/'+inputs['provenance']['python'],
                command='E3 actual sealed finalist replay/product assessment',result_ref='research:'+run_id+'/sealed_oos')
            backtest=self.record_backtest_result(product['sealed_backtest'],**metadata)
            decision=self.record_validation_decision(product['canonical_oos_decision'],backtest_evidence_id=backtest.evidence_id,**metadata)
        record=ProductAssessmentRecord('product-'+digest(resolved.assessment_json+str(risk_raw))[7:],run_id,identity,
            strategy.content_hash,resolved.namespace,inputs['implementation_hash'],product['status'],resolved.assessment_json,
            digest(resolved.assessment_json),risk_raw,None if risk_raw is None else digest(risk_raw),
            None if decision is None else decision.evidence_id,_utc_now(),'research:'+run_id+'/product_assessment')
        record=self._store._save_product_assessment(record,capability=_PRODUCT_EVIDENCE_CAPABILITY)
        if strategy.current_lifecycle_state=='BACKTESTING':
            if record.status=='PASS' and risk_raw is not None:
                self.mark_candidate(identity,actor=actor,validation_evidence_id=record.validation_evidence_id)
            elif record.status=='FAIL':
                self.reject_from_backtesting(identity,actor=actor,reason_codes=tuple(product['reason_codes'])+('PRODUCT_ASSESSMENT:'+record.assessment_id,),
                    evidence_id=record.validation_evidence_id)
        return record

    def record_backtest_result(
        self,
        payload: Mapping[str, Any],
        *,
        verification_status: str = "NOT_RUN",
        verification_kind: str = "NOT_RUN",
        source_revision: str | None = None,
        environment: str | None = None,
        command: str | None = None,
        result_ref: str | None = None,
    ) -> ValidationEvidenceRecord:
        validate_backtest_result_contract(payload)
        validate_verification_metadata(
            status=verification_status,
            verification_kind=verification_kind,
        )
        return super().record_backtest_result(
            payload,
            verification_status=verification_status,
            verification_kind=verification_kind,
            source_revision=source_revision,
            environment=environment,
            command=command,
            result_ref=result_ref,
        )

    def record_validation_decision(
        self,
        payload: Mapping[str, Any],
        *,
        backtest_evidence_id: str,
        verification_status: str = "NOT_RUN",
        verification_kind: str = "NOT_RUN",
        source_revision: str | None = None,
        environment: str | None = None,
        command: str | None = None,
        result_ref: str | None = None,
    ) -> ValidationEvidenceRecord:
        validate_validation_decision_contract(payload)
        validate_verification_metadata(
            status=verification_status,
            verification_kind=verification_kind,
        )
        return super().record_validation_decision(
            payload,
            backtest_evidence_id=backtest_evidence_id,
            verification_status=verification_status,
            verification_kind=verification_kind,
            source_revision=source_revision,
            environment=environment,
            command=command,
            result_ref=result_ref,
        )

    def begin_backtesting(self, identity: StrategyIdentity, *, actor: str) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state == "DRAFT":
            require_backtesting_authority(self._store, strategy)
        return super().begin_backtesting(identity, actor=actor)

    def mark_candidate(
        self,
        identity: StrategyIdentity,
        *,
        actor: str,
        validation_evidence_id: str,
    ) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state == "BACKTESTING":
            require_candidate_authority(self._store, strategy, validation_evidence_id)
        return super().mark_candidate(
            identity,
            actor=actor,
            validation_evidence_id=validation_evidence_id,
        )

    def reject_from_backtesting(
        self,
        identity: StrategyIdentity,
        *,
        actor: str,
        reason_codes: Sequence[str],
        evidence_id: str | None = None,
    ) -> StrategyVersionRecord:
        strategy = self._require_strategy(identity)
        if strategy.current_lifecycle_state == "BACKTESTING":
            require_rejection_authority(
                self._store,
                strategy,
                reason_codes=reason_codes,
                primary_evidence_id=evidence_id,
            )
        return super().reject_from_backtesting(
            identity,
            actor=actor,
            reason_codes=reason_codes,
            evidence_id=evidence_id,
        )
