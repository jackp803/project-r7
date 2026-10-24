"""Actual E6-qualified local PAPER service; simulation broker only."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
import uuid
from time import monotonic_ns
from time import monotonic

from brokers.paper import PaperBroker
from execution.models import require_utc
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from registry import EvidenceGateError, StrategyPlatformService, StrategyIdentity
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
    management_only: bool=False
    def __post_init__(self):
        if (not isinstance(self.snapshot, MarketSnapshot) or not isinstance(self.candles, tuple) or
            len(self.candles) > 16_000 or any(not isinstance(row, Candle) for row in self.candles) or
            self.source_kind not in ('FIXTURE', 'PUBLIC_MARKET') or type(self.management_only) is not bool
            or self.management_only and (self.source_kind!='PUBLIC_MARKET' or self.candles)):
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
                 submission_validity, actor, workflow_authorized, current_release, clock, monotonic_clock=monotonic_ns,
                 strategy_identity=None,management_selection=None,selection_current=None,entry_current=None,implementation_hash=None,
                 funding_source=None,funding_admission=None):
        if (not isinstance(registry, StrategyPlatformService) or
            not isinstance(process_journal, PaperProcessJournal) or
            not isinstance(canonical_journal, PaperRuntimeJournal) or
            not callable(clock) or not callable(monotonic_clock) or not callable(current_release) or type(workflow_authorized) is not bool):
            raise ValueError('Actual registry/journals and explicit local workflow authority required')
        if not isinstance(actor, str) or not actor.strip() or len(actor) > 256:
            raise ValueError('Trusted configured runtime actor required')
        if strategy_identity is not None and not isinstance(strategy_identity,StrategyIdentity):
            raise ValueError('Actual selected PAPER strategy identity required')
        if any(value is not None and not callable(value) for value in (management_selection,selection_current,entry_current)):
            raise ValueError('Trusted original selection/currentness readers required')
        self.management_selection,self.selection_current=management_selection,selection_current
        self.entry_current=entry_current
        if implementation_hash is not None and (type(implementation_hash) is not str
                or not re.fullmatch('sha256:[0-9a-f]{64}',implementation_hash)):
            raise ValueError('Trusted owner source commitment required')
        self.implementation_hash=implementation_hash
        self._management_services={}
        self.strategy_identity=strategy_identity
        self.registry=registry; self.process=process_journal; self.canonical=canonical_journal
        self.namespace=namespace; self.clock=clock; self.current_release=current_release
        self.monotonic_clock=monotonic_clock
        self.actor=actor; self.authorized=workflow_authorized; self.policy_ref=paper_policy_ref
        self.simulation=parse_simulation_policy(simulation_policy, namespace=namespace)
        from .funding_source import PaperFundingSource
        if funding_source is not None and type(funding_source) is not PaperFundingSource:
            raise ValueError('Trusted owner public funding source port required')
        self.funding_source=funding_source
        if funding_admission is not None and not callable(funding_admission):
            raise ValueError('Trusted actual owner funding admission reader required')
        self.funding_admission=funding_admission
        self.risk=parse_product_risk_policy(risk_policy, namespace=namespace)
        self.promotion=parse_paper_promotion_policy(promotion_policy, namespace=namespace)
        self.validity_json=bind_submission_validity(submission_validity, clock())
        self._runtimes={}; self._instance_id='paper-process-'+uuid.uuid4().hex
        self._history_failures={};self._history_retry_after={}

    def _binding(self, strategy):
        if self.strategy_identity is not None and strategy.identity!=self.strategy_identity:
            raise EvidenceGateError('PAPER policy belongs to another selected strategy')
        return dict(namespace=self.namespace, mode=self.simulation.as_dict()['mode'],
            strategy_id=strategy.identity.strategy_id, strategy_version=strategy.identity.strategy_version,
            strategy_content_hash=strategy.content_hash, implementation_hash=_revision() if self.implementation_hash is None else self.implementation_hash,
            config_hash=digest(canonical(dict(simulation=self.simulation.as_dict(),
                submission_validity=json.loads(self.validity_json)))),
            risk_policy_hash=self.risk.policy_hash, paper_policy_hash=self.promotion.policy_hash)

    def start(self, strategy_identity, policy_id, expected_revision, command_id):
        from .engine import initial_runtime_state
        if not self.authorized or policy_id != self.policy_ref:
            raise EvidenceGateError('Explicit selected local PAPER workflow authorization required')
        if self.recorded_funding and not self.funding_start_ready():
            raise EvidenceGateError('Current source-owned public settled funding required')
        strategy=self.registry.get_strategy(strategy_identity)
        product=self.registry.candidate_product_assessment(strategy_identity)
        if product.namespace != self.namespace or product.risk_policy_hash != self.risk.policy_hash:
            raise EvidenceGateError('PAPER selected risk differs from actual candidate assessment')
        release=self.current_release()
        source=_revision() if self.implementation_hash is None else self.implementation_hash
        if not isinstance(release, ReleaseBinding) or release.namespace != self.namespace or release.implementation_hash != source:
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
        recovered=self.process.management_snapshot(reference[len('paper-start:'):])
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
            management=self._management_service(run_id)
            runtime=PaperRuntime(management,run_id)
            self._runtimes[run_id]=management._runtimes[run_id]=runtime
        return self._runtimes[run_id]

    def entry_release_is_current(self,run_id):
        # New entry/first-fill boundary only. Protective management never
        # evaluates qualification or waits for this read-only admission check.
        if self.entry_current is None:return self.namespace=='FIXTURE'
        try:
            result=self.entry_current(run_id)
            return type(result) is bool and result
        except (ValueError,OSError,RuntimeError):return False

    def history_ready(self,run_id):
        return not self.process.requires_history_audit(run_id) or self.process.history_audit_ready(run_id)

    def history_audit_after_protection(self,run_ids):
        """One actual owned audit at a time, after all current management work.

        No full audit, stdout wait, result file import or process reap occurs in
        this callback. A retained failed handle denies successors; shutdown owns
        bounded reap retries. Failures never interrupt protective management.
        """
        if type(run_ids) is not tuple or len(run_ids)>200:raise ValueError('Bounded owning run inventory required')
        worker=self.process._background_history
        if worker is not None and worker.active_run() is not None:
            run=worker.active_run()
            try:worker.poll(run)
            except (ValueError,OSError,RuntimeError):self._history_failures[run]='HISTORY_WORKER_RECONCILIATION_REQUIRED'
            return
        for run in run_ids:
            if not self.process.requires_history_audit(run) or self.history_ready(run):continue
            progress=self.process.history_audit_progress(run)
            if progress.status=='HISTORY_AUDIT_FAILED':
                self._history_failures[run]='HISTORY_AUDIT_FAILED';continue
            if monotonic()<self._history_retry_after.get(run,0):continue
            try:
                if worker is None:
                    from storage.paper_history_worker import OwnedPaperHistoryAudit
                    worker=OwnedPaperHistoryAudit(self.process,implementation_hash=self.implementation_hash)
                worker.start(run)
            except (ValueError,OSError,RuntimeError):
                self._history_failures[run]='HISTORY_AUDIT_RETRY_REQUIRED';self._history_retry_after[run]=monotonic()+5
            else:self._history_failures.pop(run,None)
            break

    @property
    def recorded_funding(self):
        return self.simulation.as_dict()['funding_model']=='OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1'

    def funding_observation(self):
        return None if self.funding_source is None else self.funding_source.current(self.clock())

    def funding_start_ready(self):
        # Control never attaches an E4/runtime or imports financial truth.
        # Runtime allocation always requires its own actual E4 source port.
        if self.funding_source is not None:return self.funding_observation() is not None
        if self.funding_admission is None:return False
        try:return self.funding_admission() is True
        except (ValueError,TypeError,KeyError,RuntimeError,OSError):return False

    def requires_entry_pause(self,run_id):
        if self.selection_current is None:return False
        current=self.selection_current(run_id)
        if type(current) is not bool:raise EvidenceGateError('Actual selection currentness required')
        return not current

    def _management_service(self,run_id):
        if self.management_selection is None:return self
        if run_id not in self._management_services:
            from .owners import PaperOwnerSelection
            original=self.management_selection(run_id)
            if original is None:return self
            if not isinstance(original,PaperOwnerSelection) or original.namespace!=self.namespace:
                raise EvidenceGateError('Exact same-namespace original Paper selection required')
            selected=original.as_dict();selected.pop('namespace')
            # This historical composition can manage its accepted run, never
            # start another one or inherit replacement workflow permission.
            selected['workflow_authorized']=False
            recovered=self.process.management_snapshot(run_id)
            identity=StrategyIdentity(recovered.binding['strategy_id'],recovered.binding['strategy_version'])
            self._management_services[run_id]=PaperService(registry=self.registry,process_journal=self.process,
                canonical_journal=self.canonical,namespace=self.namespace,current_release=self.current_release,
                clock=self.clock,monotonic_clock=self.monotonic_clock,strategy_identity=identity,
                implementation_hash=self.implementation_hash,funding_source=self.funding_source,
                funding_admission=self.funding_admission,**selected)
        return self._management_services[run_id]

    def is_quiescent(self,run_id):
        """Actual terminal/paused flat truth, never inferred from lifecycle alone."""
        management=self._management_service(run_id)
        if management is not self:return management.is_quiescent(run_id)
        from registry import StrategyIdentity
        recovered=self.process.management_snapshot(run_id)
        identity=StrategyIdentity(recovered.binding['strategy_id'],recovered.binding['strategy_version'])
        strategy=self.registry.get_strategy(identity)
        if recovered.binding!=self._binding(strategy):
            raise EvidenceGateError('Exact Paper binding required before releasing management')
        runtime=recovered.state['runtime']
        if runtime.get('pending_funding') is not None:return False
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
        self._management_services.pop(run_id,None)
        self.process.forget_history_audit(run_id)
        self._history_failures.pop(run_id,None);self._history_retry_after.pop(run_id,None)

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
        recovered=service.process.management_snapshot(run_id)
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
        self.engine.reconcile(service.process.management_snapshot(run_id).state,service.canonical)

    def on_market_event(self,event):
        if not isinstance(event,PaperMarketEvent): raise ValueError('Actual E1 event required')
        expected_kind='FIXTURE' if self.service.namespace=='FIXTURE' else 'PUBLIC_MARKET'
        if event.source_kind != expected_kind: raise EvidenceGateError('Synthetic/public market namespace mismatch')
        now=self.service.clock(); cached=self.service.process.management_snapshot(self.run_id).state['runtime']['candles']
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
        if event.management_only:material['management_only']=True
        identities=canonical(dict(run_id=self.run_id,observed_at=material['snapshot']['observed_at'],
            candle_boundaries=[(row.symbol,row.timeframe,row.close_time.isoformat()) for row in event.candles],
            **(dict(management_only=True) if event.management_only else {})))
        operation_id='market_'+hashlib.sha256(identities.encode()).hexdigest()
        return self.coordinator.execute(operation_id,material)

    def on_deadline(self,deadline):
        require_utc(deadline,'deadline')
        if deadline>self.service.clock(): raise ValueError('Future management deadline cannot execute early')
        return self.coordinator.execute('deadline:'+deadline.isoformat(),dict(kind='DEADLINE',due_at=deadline.isoformat().replace('+00:00','Z')))
