"""Original E2 EXIT interpretation; retained facts never become a permit."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from threading import RLock

from application.trading.admission import RuntimeAdmissionError
from application.trading.close_owner import original_entry, _prepare_original_exit_close, require_close_preparation
from application.trading.position_observation import require_position_read
from execution.models import stable_position_action_client_order_id, stable_order_request_id
from position.entry_observation import product_entry_position_id
from position.exit_requests import anchor_exit_request, CurrentExitAuthority, interpret_exit_request
from position.exit_state import encode_exit_anchor, restore_exit_anchor
from position.lifecycle_execution_binding import validate_position_lifecycle_execution_evidence_binding
from storage.product_dispatch import _json, _stamp
from storage.product_exit_decision import ANCHOR_PROFILE, DECISION_PROFILE, encode_exit_market
from strategy.v02.exits import ExitRequest


@dataclass(frozen=True)
class ProductExitEvaluationOutcome:
    decision_id: str | None
    status: str
    reason_codes: tuple[str,...]
    anchor: object
    operation_id: str | None = None
    dispatch_outcome: object = None


def _at(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00')); _stamp(result)
    return result


class OriginalExitOwner:
    def __init__(self,service):
        from application.trading.service import TradingService
        if (type(service) is not TradingService or service.lease is None or
                service.admission.namespace!='FIXTURE' or service.execution!='FAKE_PROVIDER_VERIFICATION'):
            raise RuntimeAdmissionError('ORIGINAL_EXIT_FIRST_FIXTURE_SLICE_REQUIRED')
        self.service=service;self._lock=RLock();self._local_preparation=None

    def evaluate(self,entry_boundary,**arguments):
        with self._lock:
            return self._evaluate(entry_boundary,**arguments)

    def _original_graph(self,entry,native,metadata,read_proof,revision):
        service=self.service
        require_position_read(service,native,metadata=metadata,proof=read_proof,expected_revision=revision)
        operation,prepared,_,original=original_entry(service,entry.effects[1]['payload']['trade_plan_id'])
        if operation.operation_id!=entry.evidence['operation_id']:
            raise RuntimeAdmissionError('EXIT_ORIGINAL_ENTRY_OPERATION_REQUIRED')
        plan=entry.effects[1]['payload']
        recovered=service.canonical.recover(trade_plan_id=plan['trade_plan_id'],
            position_id=product_entry_position_id(plan['trade_plan_id']))
        if (not recovered.restart_authoritative or recovered.current_position_projection is None or
                recovered.current_lifecycle_execution_binding is None or recovered.approved_trade_plan.payload!=plan or
                recovered.risk_decision.payload!=entry.effects[0]['payload']):
            raise RuntimeAdmissionError('EXIT_ACTUAL_CANONICAL_GRAPH_REQUIRED')
        source=recovered.current_position_projection.payload
        validate_position_lifecycle_execution_evidence_binding(recovered.current_lifecycle_execution_binding.payload,source)
        fills=[row.payload for row in recovered.fills
               if row.payload['client_order_id']==prepared.canonical_request.client_order_id]
        quantity=Decimal(source['actual_quantity'])
        signed=quantity*(1 if source['side']=='LONG' else -1)
        if (quantity<=0 or source['lifecycle_state'] not in ('OPEN_UNPROTECTED','OPEN_PROTECTED') or not fills or
                native.provider_position_id!=original['provider_position_id'] or native.canonical_net_quantity!=signed or
                native.average_entry_price!=Decimal(source['average_entry_price']) or
                native.provider_updated_at<max(_at(row['filled_at']) for row in fills) or
                _at(source['opened_at'])!=min(_at(row['filled_at']) for row in fills)):
            raise RuntimeAdmissionError('EXIT_ORIGINAL_CURRENT_NATIVE_SOURCE_REQUIRED')
        return recovered,plan

    def _anchor(self,entry,recovered,plan,request):
        service=self.service
        existing=service.dispatch.exit_anchor(service.run_id,entry.decision_id)
        if existing is not None:
            # Historical initial source must still be an actual canonical row.
            value=existing.evidence
            if (not any(row.payload==value['source_position'] for row in recovered.lifecycle_history) or
                    not any(row.payload==value['source_binding'] for row in recovered.lifecycle_execution_bindings)):
                raise RuntimeAdmissionError('EXIT_ORIGINAL_CANONICAL_ANCHOR_REQUIRED')
            restore_exit_anchor(value['anchor'],request=request,
                position=recovered.current_position_projection.payload,plan=plan)
            return existing
        positives=sorted((row for row in recovered.lifecycle_history
            if row.payload['lifecycle_state'] in ('OPEN_UNPROTECTED','OPEN_PROTECTED') and
               Decimal(row.payload['actual_quantity'])>0),key=lambda row:row.payload['lifecycle_revision'])
        if not positives:raise RuntimeAdmissionError('EXIT_ORIGINAL_FIRST_POSITIVE_SOURCE_REQUIRED')
        first=positives[0].payload
        bindings=[row.payload for row in recovered.lifecycle_execution_bindings
                  if row.payload['lifecycle_projection_id']==first['lifecycle_projection_id']]
        if len(bindings)!=1:raise RuntimeAdmissionError('EXIT_ORIGINAL_FIRST_BINDING_REQUIRED')
        validate_position_lifecycle_execution_evidence_binding(bindings[0],first)
        if first['opened_at']!=recovered.current_position_projection.payload['opened_at']:
            raise RuntimeAdmissionError('EXIT_ORIGINAL_FIRST_FILL_CLOCK_REQUIRED')
        anchor=anchor_exit_request(request,first,plan)
        evidence=dict(profile=ANCHOR_PROFILE,run_id=service.run_id,entry_decision_id=entry.decision_id,
            entry_evidence_hash=entry.evidence_hash,entry_operation_id=entry.evidence['operation_id'],
            original_exit_request=request.as_dict(),original_plan=plan,source_position=first,
            source_binding=bindings[0],anchor=encode_exit_anchor(anchor))
        service.dispatch.require_process(service.lease,now=service.clock())
        return service.dispatch.stage_exit_anchor(service.run_id,entry.decision_id,_json(evidence),
            lease=service.lease,now=service.clock())

    def _evaluate(self,entry_boundary,*,native_position,metadata,read_proof,close_proof,
                  market_snapshot,market_freshness_classification,action_expires_at,expected_revision):
        service=self.service
        entry=service.dispatch.entry_decision(service.run_id,service.identity,entry_boundary)
        if entry is None or entry.evidence['status']!='APPROVE':
            raise RuntimeAdmissionError('EXIT_ORIGINAL_APPROVED_E2_ENTRY_REQUIRED')
        saved=service.dispatch.exit_decision(service.run_id,entry.decision_id)
        operation=None if saved is None else service.dispatch.operation(service.run_id,saved.evidence['operation_id'])
        if operation is not None and operation.recovery_disposition=='READBACK_REQUIRED':
            # Existing obligation first; no current market, entry expiry, new E5
            # interpretation, preparation or translation belongs before readback.
            result=service.reconcile(operation.operation_id,expected_revision=expected_revision)
            anchor=service.dispatch.exit_anchor(service.run_id,entry.decision_id).anchor
            return ProductExitEvaluationOutcome(saved.decision_id,'DISPATCHED',
                ('ORIGINAL_CLAIM_READBACK',),anchor,operation.operation_id,result)
        if operation is not None and (self._local_preparation is None or
                self._local_preparation[0]!=saved.decision_id):
            return ProductExitEvaluationOutcome(saved.decision_id,'BLOCKED',
                ('ORIGINAL_LOCAL_PREPARATION_REQUIRED',),
                service.dispatch.exit_anchor(service.run_id,entry.decision_id).anchor,operation.operation_id)
        service._guard(expected_revision,'MANAGE_EXISTING')
        service.recover_publications()
        recovered,plan=self._original_graph(entry,native_position,metadata,read_proof,expected_revision)
        request=ExitRequest(_json(entry.exit_request))
        anchor_record=self._anchor(entry,recovered,plan,request)
        anchor=restore_exit_anchor(anchor_record.evidence['anchor'],request=request,
            position=recovered.current_position_projection.payload,plan=plan)
        if saved is None:
            market=encode_exit_market(market_snapshot)
            now=service.clock();_stamp(now);_stamp(action_expires_at)
            outcome=interpret_exit_request(request,CurrentExitAuthority(
                recovered.current_position_projection.payload,plan,anchor,market_snapshot,
                market_freshness_classification,now,action_expires_at))
            if outcome.status!='AUTHORIZED':
                return ProductExitEvaluationOutcome(None,outcome.status,outcome.reason_codes,anchor)
            if outcome.position_action.get('action')!='EXIT' or outcome.lifecycle_intent!='EXIT_REQUESTED':
                return ProductExitEvaluationOutcome(None,'BLOCKED',('EXIT_ONLY_OWNER_REQUIRES_PROTECTION_OWNER',),anchor)
            action=outcome.position_action
            operation_id=stable_order_request_id(stable_position_action_client_order_id(
                action['position_action_id'],'POSITION_EXIT'))
            evidence=dict(profile=DECISION_PROFILE,run_id=service.run_id,entry_decision_id=entry.decision_id,
                entry_evidence_hash=entry.evidence_hash,entry_operation_id=entry.evidence['operation_id'],
                original_exit_request=request.as_dict(),original_plan=plan,
                source_position=recovered.current_position_projection.payload,
                source_binding=recovered.current_lifecycle_execution_binding.payload,
                anchor=anchor_record.evidence['anchor'],anchor_evidence_hash=anchor_record.evidence_hash,
                market_snapshot=market,market_freshness_classification=market_freshness_classification,
                interpreted_at=_stamp(now),action_expires_at=_stamp(action_expires_at),
                position_action=action,operation_id=operation_id)
            require_position_read(service,native_position,metadata=metadata,proof=read_proof,expected_revision=expected_revision)
            if service.canonical.recover(trade_plan_id=plan['trade_plan_id'],position_id=anchor.position_id)!=recovered:
                raise RuntimeAdmissionError('EXIT_CANONICAL_SOURCE_CHANGED_DURING_INTERPRETATION')
            saved=service.dispatch.stage_exit_decision(service.run_id,entry.decision_id,_json(evidence),
                lease=service.lease,now=service.clock())
        elif (saved.evidence['source_position']!=recovered.current_position_projection.payload or
                saved.evidence['source_binding']!=recovered.current_lifecycle_execution_binding.payload):
            raise RuntimeAdmissionError('EXIT_ORIGINAL_AUTHORIZED_SOURCE_CHANGED')
        # Canonical action commits first; a separate receipt may safely replay
        # after a real writer interruption without issuing any provider effect.
        service.recover_publications()
        if operation is None:
            prepared=_prepare_original_exit_close(service,saved,native_position,metadata=metadata,
                read_proof=read_proof,close_proof=close_proof,expected_revision=expected_revision)
            if prepared.canonical_request.order_request_id!=saved.evidence['operation_id']:
                raise RuntimeAdmissionError('EXIT_ORIGINAL_OPERATION_ID_REQUIRED')
            self._local_preparation=(saved.decision_id,prepared)
        else:
            prepared=self._local_preparation[1]
            service.translator.require(prepared,now=service.clock())
            require_close_preparation(service,prepared)
        result=service.execute(prepared,expected_revision=expected_revision)
        return ProductExitEvaluationOutcome(saved.decision_id,'DISPATCHED',
            tuple(saved.evidence['position_action']['reason_codes']),anchor,saved.evidence['operation_id'],result)
