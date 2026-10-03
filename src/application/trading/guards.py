"""Trusted local effect composition; no caller PASS/JSON can create a permit."""
from decimal import Decimal
import json
from application.trading.admission import RuntimeAdmission, RuntimeAdmissionError
from brokers.okx_product import OKXProductTranslator
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from storage.product_dispatch import ProductDispatchJournal, ProductProcessLease
from storage.runtime import PaperRuntimeJournal
from storage.current_execution import CurrentExecutionSubject
from risk.engine import require_approved_trade_plan_binding
from risk.product_policy import parse_product_risk_policy
from brokers.okx_product_state import restore_product_readback


class _TradingEffectGuard:
    def __init__(self, service, permit, purpose, *, snapshot=None, preparation=None):
        if (type(service.admission) is not RuntimeAdmission or type(service.translator) is not OKXProductTranslator or
            type(service.dispatch) is not ProductDispatchJournal or type(service.canonical) is not PaperRuntimeJournal or
            type(service.lease) is not ProductProcessLease or
            (preparation is not None and type(snapshot) is not CurrentExecutionSubject)):
            raise RuntimeAdmissionError('ACTUAL_TRADING_OWNER_COMPOSITION_REQUIRED')
        self.service=service; self.permit=permit; self.purpose=purpose
        self.snapshot=snapshot; self.preparation=preparation; self.execution=service.execution

    def require(self):
        service = self.service; now = service.clock()
        current = service.admission.current_authority(self.permit, identity=service.identity,
                         permission=self.purpose, execution=self.execution)
        binding = service.admission.process_binding(self.permit, identity=service.identity,
                         permission=self.purpose, execution=self.execution)
        if service.lease.instance_id != binding[0]:
            raise RuntimeAdmissionError('CURRENT_RUNTIME_AND_DISPATCH_PROCESS_REQUIRED')
        service.dispatch.require_process(service.lease, now=now)
        service.dispatch.ensure_run(service.run_id, current.permission, now=now)
        if self.preparation is not None:
            service.canonical.require_current_execution_subject(self.snapshot)
            service.translator.require(self.preparation, now=now)
            plan, risk = self.snapshot.approved_trade_plan.payload, self.snapshot.risk_decision.payload
            selected = parse_product_risk_policy(json.loads(current.risk_policy_json), namespace=current.permission.namespace)
            if selected.policy_hash != current.permission.release.risk_policy_hash or json.loads(selected.canonical_json)['generation'] != current.permission.release.risk_generation:
                raise RuntimeAdmissionError('CURRENT_SELECTED_E5_POLICY_REQUIRED')
            require_approved_trade_plan_binding(risk, plan, selected.risk_policy)
            prepared = self.preparation
            action = None if self.snapshot.position_action is None else self.snapshot.position_action.payload
            position = None if self.snapshot.current_position_projection is None else self.snapshot.current_position_projection.payload
            sources = (prepared.source_plan_hash, prepared.source_action_hash, prepared.source_position_hash)
            exact = tuple(None if item is None else canonical_okx_close_sizing_hash(item) for item in (plan, action, position))
            if sources != exact:
                raise RuntimeAdmissionError('EXACT_CURRENT_E5_PREPARATION_SUBJECT_REQUIRED')
            envelope = json.loads(current.envelope_json)
            if prepared.role == 'ENTRY' and (Decimal(risk['approved_margin']) > Decimal(envelope['capital_ceiling_usdt']) or
                Decimal(risk['estimated_max_loss']) > Decimal(envelope['risk_per_trade_usdt'])):
                raise RuntimeAdmissionError('CURRENT_DEPLOYMENT_FINANCIAL_BOUNDS_REQUIRED')
            if prepared.role == 'ENTRY':
                for operation in service.dispatch.claimed_entries_for_account(service.run_id):
                    if (operation.run_id, operation.operation_id) == (service.run_id, prepared.canonical_request.order_request_id): continue
                    previous = restore_product_readback(operation.request)
                    recovered = service.canonical.recover(trade_plan_id=previous.canonical_request.trade_plan_id)
                    observation = None if operation.observation_json is None else json.loads(operation.observation_json)
                    rejected = (recovered.status != 'CONFLICT' and observation is not None and observation['status'] == 'ACK_REJECTED' and not recovered.fills and
                        len(recovered.current_order_results) == 1 and
                        recovered.current_order_results[0].payload['order_status'] == 'REJECTED' and
                        Decimal(recovered.current_order_results[0].payload['filled_quantity']) == 0)
                    closed = (recovered.restart_authoritative and recovered.current_position_projection is not None and
                        recovered.current_position_projection.payload['lifecycle_state'] == 'CLOSED' and recovered.trade_result is not None and
                        recovered.current_order_results and all(item.payload['order_status'] in {'FILLED','CANCELED','EXPIRED','REJECTED'}
                                                               for item in recovered.current_order_results))
                    if not rejected and not closed:
                        raise RuntimeAdmissionError('PRIOR_ACCOUNT_ENTRY_RECONCILIATION_REQUIRED')
        # Lifetime may expire while owners/SQLite are read. Use the effect clock
        # after all work, rather than the timestamp captured at guard entry.
        service.dispatch.require_process(service.lease, now=service.clock())
        if self.preparation is not None:
            service.translator.require(self.preparation, now=service.clock())
        service.admission.require_fresh(self.permit, identity=service.identity,
                                        permission=self.purpose, execution=self.execution)
        return current.permission
