"""Actual E6/PAPER control without runtime attachment in the API process."""
from application.control_api.auth import _stamp
from application.control_api.errors import APIError
from application.paper.service import PaperService
from application.paper.assessment import published_paper_metrics
from registry import StrategyIdentity
from storage.paper_process import PaperProcessJournal
from storage.runtime import PaperRuntimeJournal
from registry import StrategyPlatformService
import json


class PaperStartControlPort:
    def __init__(self,*,namespace,service_factory):
        if namespace not in ('FIXTURE','LOCAL_RESEARCH') or not callable(service_factory):
            raise ValueError('Explicit owner-composed Paper factory required')
        self.namespace,self.factory=namespace,service_factory

    def policy_views(self):
        with self.factory() as service:
            if not isinstance(service,PaperService) or service.namespace!=self.namespace:
                raise APIError('NOT_CONFIGURED','ACTUAL_PAPER_OWNER_REQUIRED',503)
            return [dict(policy_id=service.policy_ref,kind='PAPER',status='SELECTED_LOCAL',
                mode=service.simulation.as_dict()['mode'],workflow_authorized=service.authorized,
                policy_hash=service.promotion.policy_hash,simulation_policy_hash=service.simulation.policy_hash)]

    def start(self,arguments,*,actor,command_id,expected_revision):
        with self.factory() as service:
            if not isinstance(service,PaperService) or service.namespace!=self.namespace:
                raise APIError('NOT_CONFIGURED','ACTUAL_PAPER_OWNER_REQUIRED',503)
            identity=StrategyIdentity(arguments['strategy_id'],arguments['strategy_version'])
            result=service.start(identity,arguments['policy_id'],expected_revision,command_id)
            # start persists the accepted initial run/E6 transition only. The
            # native independent worker later attaches; no generation is stolen.
            return dict(command_id=command_id,actor=actor,resource='strategy:'+identity.strategy_id+':'+identity.strategy_version,
                expected_revision=expected_revision,resource_revision=result.registry_revision,status='COMPLETE',
                effect_ref='paper:'+result.run_id,reason_codes=['PAPER_RUNTIME_ATTACHMENT_REQUIRED'],observed_at=_stamp(service.clock()))


class PaperReadControlPort:
    def __init__(self,*,namespace,process_factory,canonical_factory,clock):
        if namespace not in ('FIXTURE','LOCAL_RESEARCH') or not all(callable(value) for value in (process_factory,canonical_factory,clock)):
            raise ValueError('Explicit actual local Paper readers required')
        self.namespace,self.process_factory,self.canonical_factory,self.clock=namespace,process_factory,canonical_factory,clock

    def list(self,registry_factory,*,limit=50,offset=0):
        with registry_factory() as registry:
            if not isinstance(registry,StrategyPlatformService) or registry.research_namespace!=self.namespace:
                raise APIError('NOT_CONFIGURED','ACTUAL_SAME_NAMESPACE_E6_REQUIRED',503)
            records=registry.list_accepted_paper_starts(limit=limit,offset=offset)
        return [dict(self.view(json.loads(record.payload_json)['run_id'])['payload'],
                     accepted_evidence_ref=json.loads(record.payload_json)['evidence_ref']) for record in records]

    def _recover(self,process,run_id):
        if not isinstance(process,PaperProcessJournal): raise APIError('NOT_CONFIGURED','ACTUAL_PAPER_JOURNAL_REQUIRED',503)
        recovered=process.recover(run_id)
        if recovered.binding['namespace']!=self.namespace: raise APIError('AUTHORIZATION_REQUIRED','PAPER_NAMESPACE_CONFLICT',403)
        return recovered

    def revision(self,run_id):
        with self.process_factory() as process:
            self._recover(process,run_id)
            return process.control_revision(run_id)

    def pause(self,run_id,command_id,actor,expected_revision):
        with self.process_factory() as process:
            self._recover(process,run_id)
            return process.request_entry_pause(run_id,command_id,actor=actor,expected_revision=expected_revision,now=self.clock())

    def view(self,run_id):
        with self.process_factory() as process:
            recovered=self._recover(process,run_id)
            revision=process.control_revision(run_id)
            entry_pause=process.entry_pause_requested(run_id)
        runtime=recovered.state['runtime']; position=runtime['position']; reasons=[]
        canonical_status='NO_POSITION_OBSERVED'
        metrics=None
        if runtime['closed_trades']:
            with self.canonical_factory() as canonical:
                metrics=published_paper_metrics(canonical,runtime).to_contract_fields()
        if position is not None:
            with self.canonical_factory() as canonical:
                if not isinstance(canonical,PaperRuntimeJournal): raise APIError('NOT_CONFIGURED','ACTUAL_E6_RUNTIME_JOURNAL_REQUIRED',503)
                graph=canonical.recover(position_id=position['position_id'])
            canonical_status=graph.status; reasons.extend(graph.reason_codes)
            if graph.current_position_projection is None or graph.current_position_projection.payload!=position:
                canonical_status='RECONCILIATION_REQUIRED'; reasons.append('CANONICAL_PROJECTION_MISMATCH')
        if recovered.pending_operations: reasons.append('PAPER_OPERATION_PUBLICATION_PENDING')
        submissions=recovered.state['broker']['payload']['submissions']
        orders=[]
        for row in sorted(submissions,key=lambda item:(item['request']['created_at'],item['request']['client_order_id']))[-100:]:
            request,ack,order=row['request'],row['acknowledgement'],row['order']
            current=None if order is None else order['result']
            orders.append(dict(client_order_id=request['client_order_id'],role=request['order_role'],side=request['side'],
                requested_quantity=request['quantity'],original_ack_status=ack['order_status'],original_ack_at=ack['observed_at'],
                current_status=None if current is None else current['order_status'],
                current_observed_at=None if current is None else current['observed_at'],
                actual_filled_quantity=None if current is None else current['filled_quantity'],
                average_fill_price=None if current is None else current['average_fill_price'],
                fill_count=None if order is None else len(order['fills']),fills=[] if order is None else order['fills'][-10:]))
        payload=dict(run_id=run_id,namespace=self.namespace,mode=recovered.binding['mode'],binding=recovered.binding,
            checkpoint_revision=recovered.revision,process_generation=recovered.process_generation,
            runtime_status='NOT_STARTED' if recovered.process_generation==0 else 'PROCESS_HEALTH_UNKNOWN',
            entry_admission='PAUSED' if entry_pause or not runtime['paper_entries_allowed'] else 'OWNER_REVALIDATION_REQUIRED',
            position=position,broker_observed_at=None if position is None else position['broker_state_observed_at'],
            reconciliation=canonical_status,last_signal=runtime['last_signal'],last_intent=runtime['last_intent'],risk_decision=runtime['risk_decision'],
            entry_request=runtime['entry_request'],protection_request=runtime['protection_request'],exit_request=runtime['exit_request'],
            forward_observations=runtime['forward'],closed_trades_count=len(runtime['closed_trades']),metrics=metrics,
            orders=orders,orders_total=len(submissions),orders_limit=100,fills_limit=10,
            account_scope='ISOLATED_PER_STRATEGY_RUN',cost_convention='SLIPPAGE_IN_FILL_PRICE; NO_ADDITIONAL_SUBTRACTION')
        return dict(status='LAST_KNOWN_OWNER_FACTS',revision=revision,contract='r7-paper-runtime-v0.2',payload=payload,reason_codes=sorted(set(reasons)))
