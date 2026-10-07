"""Actual E6-qualified local PAPER service; simulation broker only."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import uuid
from time import monotonic_ns

from brokers.paper import PaperBroker
from execution.models import require_utc
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from registry import EvidenceGateError, StrategyPlatformService
from registry.operational_authority import OwnerEvidence, ReleaseBinding
from registry.product_assessment import canonical, digest
from risk.product_policy import parse_product_risk_policy
from storage.paper_process import PaperProcessJournal
from storage.runtime import PaperRuntimeJournal
from strategy import parse_strategy_definition
from strategy.v02.capabilities import _revision
from validation.paper_policy import parse_paper_promotion_policy
from .orchestrator import PaperCoordinator
from .policy import bind_submission_validity, parse_simulation_policy


@dataclass(frozen=True)
class PaperMarketEvent:
    snapshot: MarketSnapshot
    candles: tuple[Candle, ...]
    source_kind: str
    def __post_init__(self):
        if (not isinstance(self.snapshot, MarketSnapshot) or not isinstance(self.candles, tuple) or
            len(self.candles) > 16_000 or any(not isinstance(row, Candle) for row in self.candles) or
            self.source_kind not in ('FIXTURE', 'PUBLIC_MARKET')):
            raise ValueError('Actual bounded E1 market/candle event required')


@dataclass(frozen=True)
class PaperRunRef:
    run_id: str
    namespace: str
    mode: str
    strategy_id: str
    strategy_version: str
    registry_revision: int


class PaperMarketEventError(ValueError):
    """Recognized acquisition validation failure, before an owner operation."""


class PaperService:
    def __init__(self, *, registry, process_journal, canonical_journal, namespace,
                 simulation_policy, risk_policy, promotion_policy, paper_policy_ref,
                 submission_validity, actor, workflow_authorized, current_release, clock, monotonic_clock=monotonic_ns):
        if (not isinstance(registry, StrategyPlatformService) or
            not isinstance(process_journal, PaperProcessJournal) or
            not isinstance(canonical_journal, PaperRuntimeJournal) or
            not callable(clock) or not callable(monotonic_clock) or not callable(current_release) or type(workflow_authorized) is not bool):
            raise ValueError('Actual registry/journals and explicit local workflow authority required')
        if not isinstance(actor, str) or not actor.strip() or len(actor) > 256:
            raise ValueError('Trusted configured runtime actor required')
        self.registry=registry; self.process=process_journal; self.canonical=canonical_journal
        self.namespace=namespace; self.clock=clock; self.current_release=current_release
        self.monotonic_clock=monotonic_clock
        self.actor=actor; self.authorized=workflow_authorized; self.policy_ref=paper_policy_ref
        self.simulation=parse_simulation_policy(simulation_policy, namespace=namespace)
        self.risk=parse_product_risk_policy(risk_policy, namespace=namespace)
        self.promotion=parse_paper_promotion_policy(promotion_policy, namespace=namespace)
        self.validity_json=bind_submission_validity(submission_validity, clock())
        self._runtimes={}; self._instance_id='paper-process-'+uuid.uuid4().hex

    def _binding(self, strategy):
        return dict(namespace=self.namespace, mode=self.simulation.as_dict()['mode'],
            strategy_id=strategy.identity.strategy_id, strategy_version=strategy.identity.strategy_version,
            strategy_content_hash=strategy.content_hash, implementation_hash=_revision(),
            config_hash=digest(canonical(dict(simulation=self.simulation.as_dict(),
                submission_validity=json.loads(self.validity_json)))),
            risk_policy_hash=self.risk.policy_hash, paper_policy_hash=self.promotion.policy_hash)

    def start(self, strategy_identity, policy_id, expected_revision, command_id):
        from .engine import initial_runtime_state
        if not self.authorized or policy_id != self.policy_ref:
            raise EvidenceGateError('Explicit selected local PAPER workflow authorization required')
        strategy=self.registry.get_strategy(strategy_identity)
        product=self.registry.candidate_product_assessment(strategy_identity)
        if product.namespace != self.namespace or product.risk_policy_hash != self.risk.policy_hash:
            raise EvidenceGateError('PAPER selected risk differs from actual candidate assessment')
        release=self.current_release()
        if not isinstance(release, ReleaseBinding) or release.namespace != self.namespace or release.implementation_hash != _revision():
            raise EvidenceGateError('Current exact local PAPER release required')
        parsed=parse_strategy_definition(strategy.definition_json)
        if parsed.symbol != 'BTC_USDT_PERP': raise EvidenceGateError('Current E4 canonical Paper instrument unsupported')
        if not isinstance(command_id, str) or not command_id.strip() or len(command_id)>256:
            raise ValueError('Bounded start command identity required')
        binding=self._binding(strategy)
        material=canonical(dict(binding=binding,command_id=command_id,expected_revision=expected_revision))
        run_id='paper_'+hashlib.sha256(material.encode()).hexdigest()
        self.process.create_run(run_id,binding,dict(broker=PaperBroker().export_state(),
            runtime=initial_runtime_state(self, strategy)),now=self.clock())
        transition=self.registry.start_paper(strategy_identity,evidence_ref='paper-start:'+run_id,
            actor=self.actor,command_id=command_id,expected_revision=expected_revision)
        return PaperRunRef(run_id,self.namespace,binding['mode'],strategy_identity.strategy_id,strategy_identity.strategy_version,transition.registry_revision)

    def resolve_owner_evidence(self,kind,reference,identity):
        if kind=='FORWARD_READY' and reference.startswith('paper-forward:'):
            from .assessment import assess_forward
            parts=reference.split(':')
            if len(parts)!=3 or not parts[2].isascii() or not parts[2].isdigit():
                raise EvidenceGateError('Exact durable forward run/revision reference required')
            runtime=self.runtime(parts[1])
            if runtime.engine.identity!=identity: raise EvidenceGateError('Forward strategy subject changed')
            body=assess_forward(runtime,self.promotion).as_dict()
            if body['status']!='PASS' or body['run_revision']!=int(parts[2]):
                raise EvidenceGateError('Current actual bound forward assessment must pass')
            body['evidence_ref']=reference
            strategy=self.registry.get_strategy(identity)
            return OwnerEvidence(kind,identity,strategy.content_hash,self.current_release(),canonical(body))
        if kind != 'PAPER_START' or not reference.startswith('paper-start:'):
            raise EvidenceGateError('Actual configured Paper evidence producer required')
        recovered=self.process.recover(reference[len('paper-start:'):])
        strategy=self.registry.get_strategy(identity)
        if recovered.binding != self._binding(strategy) or not self.authorized:
            raise EvidenceGateError('Exact current Paper run/source/config/policy required')
        body=dict(evidence_ref=reference,execution='SIMULATED_MECHANICS' if self.namespace=='FIXTURE' else 'ACTUAL_OWNER',
            paper_policy_ref=self.policy_ref,policy_hash=self.promotion.policy_hash,
            entries_enabled=False,broker_kind='PAPER_ONLY',forward_mode=recovered.binding['mode'],
            simulation_policy_hash=self.simulation.policy_hash,run_id=recovered.run_id)
        return OwnerEvidence(kind,identity,strategy.content_hash,self.current_release(),canonical(body))

    def runtime(self,run_id):
        if run_id not in self._runtimes:
            self._runtimes[run_id]=PaperRuntime(self,run_id)
        return self._runtimes[run_id]

    def is_quiescent(self,run_id):
        """Actual terminal/paused flat truth, never inferred from lifecycle alone."""
        from registry import StrategyIdentity
        recovered=self.process.recover(run_id)
        identity=StrategyIdentity(recovered.binding['strategy_id'],recovered.binding['strategy_version'])
        strategy=self.registry.get_strategy(identity)
        if recovered.binding!=self._binding(strategy):
            raise EvidenceGateError('Exact Paper binding required before releasing management')
        runtime=recovered.state['runtime']
        if (strategy.current_lifecycle_state=='PAPER' and runtime['paper_entries_allowed']
                and not self.process.entry_pause_requested(run_id)):
            return False
        if recovered.pending_operations: return False
        position=runtime['position']
        if position is not None:
            if position['lifecycle_state']!='CLOSED': return False
            graph=self.canonical.recover(position_id=position['position_id'])
            if (graph.status!='READY' or graph.current_position_projection is None
                    or graph.current_position_projection.payload!=position or graph.trade_result is None
                    or graph.trade_result.payload not in runtime['closed_trades']):
                return False
        broker=PaperBroker.from_state(recovered.state['broker'])
        if broker.query_position('BTC_USDT_PERP').net_quantity!=0: return False
        for row in recovered.state['broker']['payload']['submissions']:
            result=broker.query_order(row['request']['client_order_id'])
            if result is None or result.order_status.value not in ('FILLED','CANCELED','EXPIRED','REJECTED'):
                return False
        return True

    def release_quiescent_runtime(self,run_id):
        """Drop only the local cache; accepted evidence and journals are retained."""
        if not self.is_quiescent(run_id):
            raise EvidenceGateError('Actual quiescent Paper truth required')
        self._runtimes.pop(run_id,None)

    def stop_new_entries(self,run_id,command_id):
        return self.runtime(run_id).coordinator.execute('pause:'+command_id,dict(kind='PAUSE'))

    def mark_ready(self,run_id,*,expected_revision,command_id):
        from .assessment import assess_forward
        runtime=self.runtime(run_id); assessment=assess_forward(runtime,self.promotion).as_dict()
        if assessment['status']!='PASS': raise EvidenceGateError('Actual forward assessment did not qualify')
        return self.registry.mark_ready_for_approval(runtime.engine.identity,
            evidence_ref='paper-forward:'+run_id+':'+str(assessment['run_revision']),
            actor=self.actor,command_id=command_id,expected_revision=expected_revision)


class PaperRuntime:
    def __init__(self,service,run_id):
        from .engine import PaperEngine
        self.service=service; self.run_id=run_id
        recovered=service.process.recover(run_id)
        from registry import StrategyIdentity
        identity=StrategyIdentity(recovered.binding['strategy_id'],recovered.binding['strategy_version'])
        strategy=service.registry.get_strategy(identity)
        if recovered.binding != service._binding(strategy): raise EvidenceGateError('Paper recovery source/policy/config changed')
        accepted=service.registry.accepted_paper_start_evidence(identity)
        proof=json.loads(accepted.payload_json)
        if (proof.get('run_id')!=run_id or proof.get('evidence_ref')!='paper-start:'+run_id or
            proof.get('simulation_policy_hash')!=service.simulation.policy_hash):
            raise EvidenceGateError('Prepared run is not the exact accepted E6 PAPER execution')
        generation=service.process.begin_process(run_id,service._instance_id,
            expected_generation=recovered.process_generation,now=service.clock())
        self.engine=PaperEngine(service,identity,run_id)
        self.coordinator=PaperCoordinator(service.process,service.canonical,run_id,generation,
                                          self.engine.produce,clock=service.clock)
        self.coordinator.recover_pending()
        self.engine.reconcile(service.process.recover(run_id).state,service.canonical)

    def on_market_event(self,event):
        if not isinstance(event,PaperMarketEvent): raise ValueError('Actual E1 event required')
        expected_kind='FIXTURE' if self.service.namespace=='FIXTURE' else 'PUBLIC_MARKET'
        if event.source_kind != expected_kind: raise EvidenceGateError('Synthetic/public market namespace mismatch')
        now=self.service.clock(); cached=self.service.process.recover(self.run_id).state['runtime']['candles']
        for row in event.candles:
            if (row.symbol!=self.engine.strategy.symbol or row.timeframe not in self.engine.strategy.required_timeframes or
                not row.is_closed or row.close_time>now or row.received_at is None or row.received_at>now):
                raise PaperMarketEventError('Finalized available E1 candle for the exact strategy required')
            existing=next((item for item in cached.get(row.timeframe,[]) if item['open_time']==row.to_interchange_dict()['open_time']),None)
            if existing is not None and existing!=row.to_interchange_dict():
                raise PaperMarketEventError('Changed finalized candle identity')
            frame=cached.setdefault(row.timeframe,[])
            if existing is None:
                if frame and row.open_time<datetime.fromisoformat(frame[-1]['open_time'].replace('Z','+00:00')):
                    raise PaperMarketEventError('Out-of-order finalized candle')
                frame.append(row.to_interchange_dict())
        material=dict(kind='MARKET',snapshot=event.snapshot.to_interchange_dict(),
            candles=[row.to_interchange_dict() for row in event.candles],source_kind=event.source_kind)
        identities=canonical(dict(run_id=self.run_id,observed_at=material['snapshot']['observed_at'],
            candle_boundaries=[(row.symbol,row.timeframe,row.close_time.isoformat()) for row in event.candles]))
        operation_id='market_'+hashlib.sha256(identities.encode()).hexdigest()
        return self.coordinator.execute(operation_id,material)

    def on_deadline(self,deadline):
        require_utc(deadline,'deadline')
        if deadline>self.service.clock(): raise ValueError('Future management deadline cannot execute early')
        return self.coordinator.execute('deadline:'+deadline.isoformat(),dict(kind='DEADLINE',due_at=deadline.isoformat().replace('+00:00','Z')))
