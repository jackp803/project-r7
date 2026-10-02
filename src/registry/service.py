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

    def list_strategies(self,*,limit=50,offset=0):
        """Bounded current canonical inventory; exposes no persistence writer."""
        if type(limit) is not int or not 1<=limit<=200 or type(offset) is not int or not 0<=offset<=100000:
            raise ValueError('Bounded inventory page required')
        return self._store.list_strategies(limit=limit,offset=offset)

    def lifecycle_counts(self):
        return self._store.lifecycle_counts()

    @property
    def research_namespace(self):
        return self._store.get_research_namespace()

    def human_approval_for_command(self,command_id):
        """Read retained audit, never renew a permission from its receipt."""
        from .operational_authority import text
        from .models import EvidenceGateError
        from .product_assessment import digest
        record=self._store.human_approval_for_command(text(command_id))
        if record is not None and (record.namespace!=self.research_namespace or digest(record.payload_json)!=record.payload_hash or digest(record.envelope_json)!=record.envelope_hash):
            raise EvidenceGateError('Immutable actual approval integrity required')
        return record

    def current_deployment_envelope(self,identity,*,envelope_ref,expected_revision):
        strategy,boundary=self._operational_context(identity,expected_revision,('READY_FOR_APPROVAL',))
        product=self.candidate_product_assessment(identity)
        return boundary.envelope(envelope_ref,strategy,product.risk_policy_json)

    def accepted_paper_start_evidence(self,identity):
        from .models import EvidenceGateError
        from .product_assessment import digest
        strategy=self._require_strategy(identity)
        record=self._store.accepted_paper_start_evidence(identity)
        if (record is None or record.kind!='PAPER_START' or record.identity!=identity or
            record.strategy_content_hash!=strategy.content_hash or
            record.namespace!=self._store.get_research_namespace() or
            digest(record.payload_json)!=record.payload_hash or digest(record.release_json)!=record.release_hash):
            raise EvidenceGateError('Actual immutable accepted E6 PAPER start required')
        return record

    def _operational_context(self,identity,expected_revision,allowed_states):
        from .models import ConcurrencyConflict,EvidenceGateError,InvalidTransition
        from .operational_authority import ProductLifecycleComposition
        strategy=self._require_strategy(identity)
        if type(expected_revision) is not int or strategy.registry_revision!=expected_revision:
            raise ConcurrencyConflict('Stale expected registry revision')
        if strategy.current_lifecycle_state not in allowed_states: raise InvalidTransition('Forbidden named lifecycle operation')
        boundary=getattr(self._store,'_lifecycle_boundary',None)
        if not isinstance(boundary,ProductLifecycleComposition) or boundary.namespace!=self._store.get_research_namespace():
            raise EvidenceGateError('Explicit current lifecycle composition required')
        boundary.current()
        return strategy,boundary

    def _command(self,identity,kind,actor,command_id,expected_revision,arguments):
        from .models import ConcurrencyConflict
        from .operational_authority import text
        from .product_assessment import canonical
        text(command_id); text(actor)
        if type(expected_revision) is not int or expected_revision<0: raise ConcurrencyConflict('Explicit expected revision required')
        request=canonical(dict(operation=kind,identity=dict(strategy_id=identity.strategy_id,strategy_version=identity.strategy_version),
            actor=actor,command_id=command_id,expected_revision=expected_revision,arguments=arguments))
        return request,self._store.lookup_lifecycle_command(command_id,request)

    def _human_boundary(self,authenticated_human):
        from .models import EvidenceGateError
        from .operational_authority import ProductLifecycleComposition
        boundary=getattr(self._store,'_lifecycle_boundary',None)
        if not isinstance(boundary,ProductLifecycleComposition) or boundary.namespace!=self._store.get_research_namespace():
            raise EvidenceGateError('Authenticated lifecycle composition required')
        return boundary,boundary.authenticator.authorize(authenticated_human)

    def _owner_transition(self,strategy,boundary,*,kind,new_state,actor,command_id,payload_json,release,request_json,deadline=None,approval=None):
        from datetime import timedelta
        from .operational_authority import OwnerGateRecord,_OWNER_EVIDENCE_CAPABILITY,stamp,text
        from .product_assessment import canonical,digest
        text(actor); text(command_id)
        now=boundary.clock(); expires=now+timedelta(seconds=300)
        if deadline is not None: expires=min(expires,deadline)
        release_json=canonical(release.as_dict())
        key=canonical([kind,strategy.identity.strategy_id,strategy.identity.strategy_version,command_id,strategy.registry_revision,digest(payload_json),digest(release_json),actor])
        record=OwnerGateRecord('owner-'+digest(key)[7:],kind,strategy.identity,strategy.content_hash,boundary.namespace,
            release_json,digest(release_json),actor,command_id,strategy.registry_revision,payload_json,digest(payload_json),stamp(now),stamp(expires))
        def persist():
            if approval is not None: self._store._save_owner_record(approval,capability=_OWNER_EVIDENCE_CAPABILITY)
            stored=self._store._save_owner_record(record,capability=_OWNER_EVIDENCE_CAPABILITY)
            return self._transition(strategy,new_state,actor=actor,reason_codes=(kind,),primary_evidence_id=None,owner_evidence_id=stored.evidence_id)
        return self._store.run_lifecycle_once(command_id,request_json,persist)

    def start_paper(self,identity,*,evidence_ref,actor,command_id,expected_revision):
        request,cached=self._command(identity,'PAPER_START',actor,command_id,expected_revision,dict(evidence_ref=evidence_ref))
        if cached is not None: return cached
        strategy,boundary=self._operational_context(identity,expected_revision,('CANDIDATE',))
        payload,release=boundary.resolve('PAPER_START',evidence_ref,strategy)
        return self._owner_transition(strategy,boundary,kind='PAPER_START',new_state='PAPER',actor=actor,
            command_id=command_id,payload_json=payload,release=release,request_json=request)

    def mark_ready_for_approval(self,identity,*,evidence_ref,actor,command_id,expected_revision):
        request,cached=self._command(identity,'FORWARD_READY',actor,command_id,expected_revision,dict(evidence_ref=evidence_ref))
        if cached is not None: return cached
        strategy,boundary=self._operational_context(identity,expected_revision,('PAPER',))
        payload,release=boundary.resolve('FORWARD_READY',evidence_ref,strategy)
        return self._owner_transition(strategy,boundary,kind='FORWARD_READY',new_state='READY_FOR_APPROVAL',actor=actor,
            command_id=command_id,payload_json=payload,release=release,request_json=request)

    def record_approval(self,identity,*,envelope_ref,authenticated_human,decision,reason,command_id,expected_revision):
        import json
        from .models import EvidenceGateError
        from .operational_authority import HumanApprovalRecord,_OWNER_EVIDENCE_CAPABILITY,stamp,text
        from .product_assessment import canonical,digest
        boundary,actor=self._human_boundary(authenticated_human)
        request,cached=self._command(identity,'HUMAN_APPROVAL',actor,command_id,expected_revision,
            dict(envelope_ref=envelope_ref,decision=decision,reason=reason))
        if cached is not None: return cached
        strategy,boundary=self._operational_context(identity,expected_revision,('READY_FOR_APPROVAL',))
        text(reason); text(command_id)
        if decision not in ('APPROVE','REJECT'): raise EvidenceGateError('Canonical human decision required')
        product=self._store.candidate_product_assessment(identity)
        if product is None: raise EvidenceGateError('Complete candidate evidence required')
        envelope=boundary.envelope(envelope_ref,strategy,product.risk_policy_json)
        release=boundary.current(); decided_at=stamp(boundary.clock())
        approval_id='approval-'+digest(canonical([identity.strategy_id,identity.strategy_version,command_id,expected_revision,digest(envelope),actor,decision,reason]))[7:]
        payload=canonical(dict(schema_version='contracts-v0.1',approval_record_id=approval_id,approval_type='STRATEGY_DEPLOYMENT',
            subject_type='StrategyDefinition',subject_id=identity.strategy_id,subject_version=identity.strategy_version,
            actor=actor,decision=decision,decided_at=decided_at,reason=reason,strategy_content_hash=strategy.content_hash,
            namespace=boundary.namespace,envelope_hash=digest(envelope),release_hash=digest(canonical(release.as_dict()))))
        record=HumanApprovalRecord(approval_id,identity,boundary.namespace,actor,command_id,expected_revision,
            envelope,digest(envelope),payload,digest(payload),decided_at)
        if decision=='REJECT':
            def persist_rejection():
                self._store._save_owner_record(record,capability=_OWNER_EVIDENCE_CAPABILITY)
                return self._transition(strategy,'REJECTED',actor=actor,reason_codes=('HUMAN_REJECTED',reason),primary_evidence_id=None)
            return self._store.run_lifecycle_once(command_id,request,persist_rejection)
        return self._owner_transition(strategy,boundary,kind='APPROVAL',new_state='APPROVED',actor=actor,command_id=command_id,
            payload_json=canonical(dict(approval_record_id=approval_id,envelope_hash=digest(envelope))),release=release,
            deadline=boundary.authenticator.deadline(authenticated_human),request_json=request,approval=record)

    def _activate(self,identity,*,evidence_ref,authenticated_human,command_id,expected_revision,resume):
        import json
        from .operational_authority import require_current_approval
        from .product_assessment import canonical
        boundary,actor=self._human_boundary(authenticated_human)
        kind='RESUMPTION' if resume else 'ACTIVATION'
        request,cached=self._command(identity,kind,actor,command_id,expected_revision,dict(evidence_ref=evidence_ref))
        if cached is not None: return cached
        strategy,boundary=self._operational_context(identity,expected_revision,('DEGRADED',) if resume else ('APPROVED',))
        approval=require_current_approval(self._store,strategy,boundary)
        payload,release=boundary.resolve(kind,evidence_ref,strategy)
        body=json.loads(payload); body['approval_record_id']=approval.approval_record_id
        return self._owner_transition(strategy,boundary,kind=kind,new_state='LIVE',actor=actor,command_id=command_id,
            payload_json=canonical(body),release=release,deadline=boundary.authenticator.deadline(authenticated_human),request_json=request)

    def activate_deployment(self,identity,*,evidence_ref,authenticated_human,command_id,expected_revision):
        return self._activate(identity,evidence_ref=evidence_ref,authenticated_human=authenticated_human,
            command_id=command_id,expected_revision=expected_revision,resume=False)

    def resume_authorized(self,identity,*,evidence_ref,authenticated_human,command_id,expected_revision):
        return self._activate(identity,evidence_ref=evidence_ref,authenticated_human=authenticated_human,
            command_id=command_id,expected_revision=expected_revision,resume=True)

    def revoke_approval(self,identity,*,authenticated_human,reason,command_id):
        from .models import EvidenceGateError
        from .operational_authority import ProductLifecycleComposition,_OWNER_EVIDENCE_CAPABILITY,stamp,text
        self._require_strategy(identity)
        boundary=getattr(self._store,'_lifecycle_boundary',None)
        if not isinstance(boundary,ProductLifecycleComposition): raise EvidenceGateError('Authenticated approval composition required')
        actor=boundary.authenticator.authorize(authenticated_human); text(reason); text(command_id)
        approval=self._store.latest_human_approval(identity)
        if approval is None: raise EvidenceGateError('Existing immutable approval required')
        return self._store._revoke_approval(approval.approval_record_id,actor=actor,reason=reason,command_id=command_id,
            recorded_at=stamp(boundary.clock()),capability=_OWNER_EVIDENCE_CAPABILITY)

    def reject(self,identity,*,actor,reason_codes,command_id,expected_revision):
        return self._fail_closed_operation(identity,actor=actor,reason_codes=reason_codes,command_id=command_id,
            expected_revision=expected_revision,new_state='REJECTED',allowed_states=('CANDIDATE','PAPER','READY_FOR_APPROVAL'))

    def degrade(self,identity,*,actor,reason_codes,command_id,expected_revision):
        """Disable new entries; do not cancel protection or erase residual exposure."""
        return self._fail_closed_operation(identity,actor=actor,reason_codes=reason_codes,command_id=command_id,
            expected_revision=expected_revision,new_state='DEGRADED',allowed_states=('LIVE',))

    def _fail_closed_operation(self,identity,*,actor,reason_codes,command_id,expected_revision,new_state,allowed_states):
        from .models import ConcurrencyConflict,EvidenceGateError,InvalidTransition
        from .operational_authority import text
        request,cached=self._command(identity,new_state,actor,command_id,expected_revision,dict(reason_codes=reason_codes))
        if cached is not None: return cached
        strategy=self._require_strategy(identity); text(actor); text(command_id)
        if type(expected_revision) is not int or expected_revision!=strategy.registry_revision: raise ConcurrencyConflict('Stale expected registry revision')
        if strategy.current_lifecycle_state not in allowed_states: raise InvalidTransition('Forbidden fail-closed lifecycle operation')
        if not isinstance(reason_codes,(tuple,list)) or not reason_codes or any(not isinstance(reason,str) or not reason.strip() for reason in reason_codes):
            raise EvidenceGateError('Explicit auditable fail-closed reasons required')
        return self._store.run_lifecycle_once(command_id,request,
            lambda:self._transition(strategy,new_state,actor=actor,reason_codes=tuple(reason_codes),primary_evidence_id=None))

    def product_assessment(self,run_id):
        return self._store.get_product_assessment(run_id)

    def candidate_product_assessment(self,identity):
        """Immutable qualified product/risk selection for actual local consumers."""
        from .product_assessment import require_product_record
        strategy=self._require_strategy(identity)
        record=self._store.candidate_product_assessment(identity)
        require_product_record(self._store,strategy,record,status='PASS')
        return record

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
