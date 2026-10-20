"""first genuine H01 entry owner, controlled FIXTURE only.

No E2 exit management, policy defaults, provider discovery, or new canonical math.
An immutable decision never supplies an execution permit. Original claimed work
is reconciled before input-policy/new-exposure gates or any new translation.
"""
from dataclasses import dataclass, fields
from datetime import datetime
from decimal import Decimal
from collections.abc import Mapping
import hashlib
import json
from threading import RLock

from execution.models import stable_client_order_id, stable_order_request_id
from market_data.candle import Candle
from position.exit_requests import resolve_exit_constraints
from registry import StrategyPlatformService
from registry.product_assessment import canonical, digest
from risk.engine import (RiskContext, RiskProposal, evaluate_trade_intent,
                         build_approved_trade_plan, require_approved_trade_plan_binding)
from risk.product_policy import SelectedRiskPolicy, parse_product_risk_policy
from storage.product_dispatch import ProductDispatchError, _json, _stamp
from storage.product_entry_decision import ProductEntryObservation, PROFILE
from strategy.runtime import StrategyRuntime, parse_strategy_definition
from strategy.trade_intent import build_trade_intent
from strategy.v02.exits import build_exit_request
from strategy.v02.models import ParsedStrategyV02
from strategy.v02.temporal import AsOfBundle, build_asof_bundle


@dataclass(frozen=True)
class EntryEvaluationOutcome:
    decision_id: str
    status: str
    reason_codes: tuple[str,...]
    operation_id: str | None = None
    dispatch_outcome: object = None


def _plain(value):
    if isinstance(value,datetime): return _stamp(value)
    if isinstance(value,Decimal):
        if not value.is_finite(): raise ProductDispatchError('ENTRY_FINITE_INPUT_REQUIRED')
        return format(value,'f')
    if type(value) in (RiskContext,RiskProposal,Candle):
        return {f.name:_plain(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,Mapping):
        if any(type(key) is not str for key in value):
            raise ProductDispatchError('ENTRY_STRING_INPUT_KEYS_REQUIRED')
        return {key:_plain(item) for key,item in value.items()}
    if type(value) in (tuple,list): return [_plain(item) for item in value]
    if value is None or type(value) in (str,bool,int): return value
    raise ProductDispatchError('ENTRY_EXPLICIT_CANONICAL_INPUT_REQUIRED')


def _input_commitment(service,strategy,bundle,selected,context,proposal,binding_hash):
    # Length-framed UTF-8 tokens avoid ambiguous concatenation. One candle at a
    # time; no duplicate whole-history JSON or additional indicator-history cap.
    hasher=hashlib.sha256()
    def append(value):
        raw=canonical(_plain(value)).encode('utf-8')
        hasher.update(len(raw).to_bytes(8,'big')); hasher.update(raw)
    append(dict(profile='product-entry-input-v0.2',run_id=service.run_id,
        namespace=service.admission.namespace,strategy_id=service.identity.strategy_id,
        strategy_version=service.identity.strategy_version,strategy_content_hash=strategy.content_hash,
        owner_binding_hash=binding_hash,boundary=bundle.boundary,
        information_cutoff=bundle.information_cutoff,availability_model=bundle.availability_model,
        selected_risk_policy=json.loads(selected.canonical_json),risk_context=context,risk_proposal=proposal))
    for timeframe in sorted(bundle.candles_by_timeframe):
        rows=bundle.candles_by_timeframe[timeframe]
        append(dict(timeframe=timeframe,count=len(rows)))
        for candle in rows:
            if type(candle) is not Candle or candle.symbol != strategy.symbol or candle.timeframe != timeframe:
                raise ProductDispatchError('ENTRY_ACTUAL_CANONICAL_CANDLE_REQUIRED')
            append(candle)
    return 'sha256:'+hasher.hexdigest()


class EntryOwner:
    def __init__(self,service):
        # Local import is deliberate: service imports TradingCoordinator.
        from application.trading.service import TradingService
        if type(service) is not TradingService or service.lease is None:
            raise ProductDispatchError('ENTRY_ACTUAL_BOUND_TRADING_SERVICE_REQUIRED')
        # This first source slice has no production-provider authority expansion.
        if service.admission.namespace != 'FIXTURE' or service.execution != 'FAKE_PROVIDER_VERIFICATION':
            raise ProductDispatchError('ENTRY_FIRST_SLICE_FIXTURE_REQUIRED')
        self.service=service
        self._lock=RLock()
        # At most one original local, unclaimed preparation is retained. Losing
        # it cannot adopt a durable PREPARED request or permit another translation.
        self._local_preparation=None

    def _owner(self,expected_revision):
        service=self.service
        permit=service.admission.issue(service.identity,expected_revision=expected_revision,
            permission='NEW_EXPOSURE',execution=service.execution)
        authority=service.admission.current_authority(permit,identity=service.identity,
            permission='NEW_EXPOSURE',execution=service.execution)
        owner=authority.permission
        selected=parse_product_risk_policy(json.loads(authority.risk_policy_json),namespace=service.admission.namespace)
        if (selected.canonical_json != authority.risk_policy_json or
                selected.policy_hash != owner.release.risk_policy_hash or
                json.loads(selected.canonical_json)['generation'] != owner.release.risk_generation):
            raise ProductDispatchError('ENTRY_ACTUAL_SELECTED_OWNER_POLICY_REQUIRED')
        with service.admission.factory() as registry:
            if not isinstance(registry,StrategyPlatformService) or registry.research_namespace != service.admission.namespace:
                raise ProductDispatchError('ENTRY_ACTUAL_SAME_NAMESPACE_STRATEGY_REQUIRED')
            record=registry.get_strategy(service.identity)
        strategy=parse_strategy_definition(record.definition_json)
        if (type(strategy) is not ParsedStrategyV02 or record.identity != service.identity or
                record.content_hash != strategy.content_hash or owner.strategy_content_hash != strategy.content_hash or
                (strategy.strategy_id,strategy.strategy_version) !=
                (service.identity.strategy_id,service.identity.strategy_version)):
            raise ProductDispatchError('ENTRY_ACTUAL_IMMUTABLE_DSL02_REQUIRED')
        service.admission.require(permit,identity=service.identity,permission='NEW_EXPOSURE',execution=service.execution)
        process=service.admission.process_binding(permit,identity=service.identity,
            permission='NEW_EXPOSURE',execution=service.execution)
        if process[0] != service.lease.instance_id:
            raise ProductDispatchError('ENTRY_ACTUAL_PROCESS_BINDING_REQUIRED')
        # Existing run binding strips transient permission/clock/revision and
        # verifies all original immutable E6/E7/provider/account/source fields.
        service.dispatch.ensure_run(service.run_id,owner,now=service.clock())
        service.dispatch.require_process(service.lease,now=service.clock())
        return strategy,selected,service.dispatch._run(service.run_id)['binding_hash']

    def _claimed(self,saved,expected_revision):
        if saved is None: return None
        operation_id=saved.evidence['operation_id']
        if operation_id is None: return None
        operation=self.service.dispatch.operation(self.service.run_id,operation_id)
        if operation is None or operation.recovery_disposition != 'READBACK_REQUIRED': return None
        # No translate, NEW_EXPOSURE, original-plan expiry, fresh market/policy,
        # or caller input-equality gate belongs before original-obligation readback.
        outcome=self.service.reconcile(operation_id,expected_revision=expected_revision)
        return EntryEvaluationOutcome(saved.decision_id,'DISPATCHED',
            ('ORIGINAL_CLAIM_READBACK',),operation_id,outcome)

    def evaluate_entry(self,bundle,*,selected_risk,risk_context,risk_proposal,metadata,
                       prerequisites,capability_proof,prerequisites_proof,expected_revision):
        with self._lock:
            return self._evaluate(bundle,selected_risk=selected_risk,risk_context=risk_context,
                risk_proposal=risk_proposal,metadata=metadata,prerequisites=prerequisites,
                capability_proof=capability_proof,prerequisites_proof=prerequisites_proof,
                expected_revision=expected_revision)

    def _evaluate(self,bundle,*,selected_risk,risk_context,risk_proposal,metadata,
                  prerequisites,capability_proof,prerequisites_proof,expected_revision):
        service=self.service
        if type(bundle) is not AsOfBundle:
            raise ProductDispatchError('ENTRY_ACTUAL_OPERATIONAL_ASOF_REQUIRED')
        _stamp(bundle.boundary)
        saved=service.dispatch.entry_decision(service.run_id,service.identity,bundle.boundary)
        claimed=self._claimed(saved,expected_revision)
        if claimed is not None: return claimed
        # Every new/unclaimed path requires current actual owner E6+E7.
        strategy,selected,binding_hash=self._owner(expected_revision)
        if type(selected_risk) is not SelectedRiskPolicy:
            raise ProductDispatchError('ENTRY_EXACT_SELECTED_RISK_REQUIRED')
        caller=parse_product_risk_policy(json.loads(selected_risk.canonical_json),namespace=service.admission.namespace)
        if caller != selected_risk or caller != selected:
            raise ProductDispatchError('ENTRY_CALLER_POLICY_OWNER_MISMATCH')
        if type(risk_context) is not RiskContext or type(risk_proposal) is not RiskProposal:
            raise ProductDispatchError('ENTRY_EXPLICIT_CONTEXT_AND_SIZING_REQUIRED')
        _stamp(bundle.information_cutoff); now=service.clock(); _stamp(now)
        if (bundle.availability_model != 'recorded_received_at' or
                bundle.boundary > now or bundle.information_cutoff > now):
            raise ProductDispatchError('ENTRY_OPERATIONAL_ASOF_CLOCK_REQUIRED')
        actual=build_asof_bundle(bundle.candles_by_timeframe,bundle.boundary,bundle.information_cutoff,
                                availability_model='recorded_received_at')
        input_hash=_input_commitment(service,strategy,actual,selected,risk_context,risk_proposal,binding_hash)
        if saved is not None:
            # A claim may have appeared while validating selected market inputs.
            claimed=self._claimed(saved,expected_revision)
            if claimed is not None: return claimed
            if saved.evidence['input_hash'] != input_hash:
                raise ProductDispatchError('ENTRY_BOUNDARY_INPUT_CONFLICT')
        else:
            signal=StrategyRuntime().evaluate(strategy,actual,actual.boundary)
            exit_request=None; intent=None; operation_id=None; effects=[]
            if signal['direction'] == 'NO_TRADE':
                status='NO_TRADE'; interpreted_at=service.clock(); _stamp(interpreted_at)
            else:
                exit_request=build_exit_request(strategy,actual)
                constraints=resolve_exit_constraints(exit_request)
                if (risk_proposal.required_stop_level != constraints.stop_level or
                        risk_proposal.required_target_level != constraints.target_level):
                    raise ProductDispatchError('ENTRY_E2_GEOMETRY_PROPOSAL_MISMATCH')
                intent=build_trade_intent(signal,entry_profile_version='entry-v0.1',entry_order_type='MARKET',
                    generated_at=actual.boundary,strategy_stop_level=constraints.stop_level,
                    strategy_target_level=constraints.target_level,max_hold_seconds=constraints.max_hold_seconds)
                # Captured AFTER E1/E2 validation+hashing, immediately before E5.
                # The intent remains at its original market boundary; no renewal.
                interpreted_at=service.clock(); _stamp(interpreted_at)
                risk=evaluate_trade_intent(intent,risk_context,risk_proposal,selected.risk_policy,
                                           decided_at=interpreted_at)
                effects=[dict(kind='RISK_DECISION',payload=risk)]
                status=risk['decision']
                if status == 'APPROVE':
                    plan=build_approved_trade_plan(intent,risk,selected.risk_policy,created_at=interpreted_at)
                    effects.append(dict(kind='APPROVED_TRADE_PLAN',payload=plan))
                    operation_id=stable_order_request_id(stable_client_order_id(plan['trade_plan_id'],'entry'))
                elif status != 'REJECT':
                    raise ProductDispatchError('ENTRY_ACTUAL_E5_DECISION_REQUIRED')
            # Expensive interpretation never extends a transient permit. Acquire
            # actual owner evidence again; immutable input subject must be equal.
            current_strategy,current_selected,current_binding=self._owner(expected_revision)
            if (current_strategy.content_hash,current_selected,current_binding) != (strategy.content_hash,selected,binding_hash):
                raise ProductDispatchError('ENTRY_OWNER_CHANGED_DURING_INTERPRETATION')
            evidence=dict(profile=PROFILE,namespace=service.admission.namespace,run_id=service.run_id,
                strategy_id=service.identity.strategy_id,strategy_version=service.identity.strategy_version,
                strategy_content_hash=strategy.content_hash,owner_binding_hash=binding_hash,
                boundary=_stamp(actual.boundary),information_cutoff=_stamp(actual.information_cutoff),
                availability_model=actual.availability_model,input_hash=input_hash,
                selected_risk_policy=json.loads(selected.canonical_json),risk_context=_plain(risk_context),
                risk_proposal=_plain(risk_proposal),signal=signal,
                exit_request=None if exit_request is None else exit_request.as_dict(),trade_intent=intent,
                interpreted_at=_stamp(interpreted_at),status=status,operation_id=operation_id)
            observation=ProductEntryObservation(_json(evidence),_json(effects))
            saved=service.dispatch.stage_entry_decision(service.run_id,service.identity,actual.boundary,
                observation,lease=service.lease,now=service.clock())
        # The decision is durable before ANY canonical E5 writer or E4 prepare.
        service.recover_publications()
        value=saved.evidence
        if value['status'] == 'NO_TRADE':
            return EntryEvaluationOutcome(saved.decision_id,'NO_TRADE',tuple(value['signal']['reason_codes']))
        if value['status'] == 'REJECT':
            return EntryEvaluationOutcome(saved.decision_id,'BLOCKED',tuple(saved.effects[0]['payload']['reason_codes']))
        claimed=self._claimed(saved,expected_revision)
        if claimed is not None: return claimed
        # This recheck is for NEW/unclaimed obligations only. Original effects,
        # interpretation clock, expiry, risk bounds and IDs remain unchanged.
        _,owner_selected,owner_binding=self._owner(expected_revision)
        if owner_selected != selected or owner_binding != binding_hash:
            raise ProductDispatchError('ENTRY_ORIGINAL_POLICY_BINDING_REQUIRED')
        risk,plan=(effect['payload'] for effect in saved.effects)
        require_approved_trade_plan_binding(risk,plan,owner_selected.risk_policy)
        operation_id=value['operation_id']
        operation=service.dispatch.operation(service.run_id,operation_id)
        if operation is not None:
            claimed=self._claimed(saved,expected_revision)
            if claimed is not None: return claimed
            if self._local_preparation is None or self._local_preparation[0] != saved.decision_id:
                return EntryEvaluationOutcome(saved.decision_id,'BLOCKED',
                    ('ORIGINAL_LOCAL_PREPARATION_REQUIRED',),operation_id)
            prepared=self._local_preparation[1]
            # Its original issuer/expiry/prerequisite proof must still be current.
            service.translator.require(prepared,now=service.clock())
        else:
            # First durable request only: current genuine mechanical proofs,
            # unchanged original ApprovedTradePlan and its ORIGINAL expiry.
            prepared=service.translator.prepare_entry(plan=plan,metadata=metadata,prerequisites=prerequisites,
                proof=capability_proof,prerequisites_proof=prerequisites_proof,now=service.clock())
            if prepared.canonical_request.order_request_id != operation_id:
                raise ProductDispatchError('ENTRY_ORIGINAL_OPERATION_ID_REQUIRED')
            self._local_preparation=(saved.decision_id,prepared)
        outcome=service.execute(prepared,expected_revision=expected_revision)
        return EntryEvaluationOutcome(saved.decision_id,'DISPATCHED',('ORIGINAL_ENTRY_DECISION',),operation_id,outcome)
