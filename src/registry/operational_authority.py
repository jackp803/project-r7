"""Typed E6 owner ports, transient human authority and exact release envelopes.

Composition is trusted local code, never a request body or a cloud artifact.
Fixture evidence is restricted to its immutable FIXTURE registry. Real owner
producers and authenticated server sessions must be configured explicitly.
"""
from dataclasses import dataclass,asdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import json,re,secrets
from typing import Callable

from .models import EvidenceGateError,StrategyIdentity
from .product_assessment import canonical,digest

_OWNER_EVIDENCE_CAPABILITY=object()
_HASH=re.compile(r'^sha256:[0-9a-f]{64}$')


def utc(value):
    try: parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError,AttributeError,TypeError) as exc: raise EvidenceGateError('Aware UTC required') from exc
    if parsed.utcoffset()!=timedelta(0): raise EvidenceGateError('Aware UTC required')
    return parsed


def stamp(value):
    return value.isoformat(timespec='microseconds').replace('+00:00','Z')


def text(value):
    if not isinstance(value,str) or not value.strip() or len(value)>256:
        raise EvidenceGateError('Bounded nonempty identity required')
    return value


@dataclass(frozen=True)
class ReleaseBinding:
    namespace: str
    implementation_hash: str
    executable_revision: str
    build_hash: str
    config_hash: str
    config_generation: int
    capability_hash: str
    provider_profile_hash: str
    provider_ref: str
    account_ref: str
    risk_policy_hash: str
    risk_generation: int
    runtime_generation: int
    release_kind: str

    def __post_init__(self):
        if self.namespace not in ('FIXTURE','LOCAL_RESEARCH'):
            raise EvidenceGateError('Release namespace required')
        for field in ('implementation_hash','build_hash','config_hash','capability_hash','provider_profile_hash','risk_policy_hash'):
            if not isinstance(getattr(self,field),str) or not _HASH.fullmatch(getattr(self,field)):
                raise EvidenceGateError('Exact release hashes required')
        if not isinstance(self.executable_revision,str) or not re.fullmatch('[0-9a-f]{40}',self.executable_revision):
            raise EvidenceGateError('Exact executable revision required')
        for field in ('config_generation','risk_generation','runtime_generation'):
            if type(getattr(self,field)) is not int or not 1<=getattr(self,field)<=2147483647:
                raise EvidenceGateError('Explicit positive generation required')
        text(self.provider_ref); text(self.account_ref)
        if self.release_kind not in ('FIXTURE','SOURCE_QUALIFIED','NATIVE_QUALIFIED') or (self.release_kind=='FIXTURE')!=(self.namespace=='FIXTURE'):
            raise EvidenceGateError('Fixture and real release identities cannot mix')

    def as_dict(self): return asdict(self)


@dataclass(frozen=True)
class CurrentRuntimeAuthority:
    permission: object
    risk_policy_json: str
    envelope_json: str


@dataclass(frozen=True)
class DeploymentApprovalPreview:
    identity: StrategyIdentity
    namespace: str
    strategy_content_hash: str
    registry_revision: int
    envelope_ref: str
    envelope_json: str
    envelope_hash: str
    risk_policy_json: str
    risk_policy_hash: str
    product_assessment_json: str
    product_assessment_hash: str
    evidence_ref: str
    observed_at: str


@dataclass(frozen=True)
class DeploymentControlSubject:
    deployment_id: str
    identity: StrategyIdentity
    namespace: str
    strategy_content_hash: str
    registry_revision: int
    lifecycle_state: str
    approval_record_id: str
    envelope_json: str
    envelope_hash: str
    activation_evidence_id: str | None
    observed_at: str


@dataclass(frozen=True)
class LifecycleCommandAudit:
    command_id: str
    request_json: str
    request_hash: str
    output_json: str
    output_hash: str
    transition_id: str
    recorded_at: str


@dataclass(frozen=True)
class HumanIdentity:
    actor: str
    roles: tuple[str,...]


class _AuthenticatedHuman:
    __slots__=('_issuer','_nonce')
    def __init__(self,issuer,nonce): self._issuer=issuer; self._nonce=nonce
    def __repr__(self): return '<authenticated human capability>'


class HumanAuthenticator:
    """Server-owned verified reauthentication; actor/role JSON is not a proof.

    The verifier is installed by trusted application composition, not an HTTP
    parameter. Tickets are opaque, short-lived and issuer-local. S10 supplies
    the actual local session/reauthentication verifier; no verifier is defaulted.
    """
    def __init__(self,*,namespace: str,verifier: Callable[[object],HumanIdentity | None],reauth_seconds: int,clock: Callable[[],datetime],current_verifier=None):
        if namespace not in ('FIXTURE','LOCAL_RESEARCH') or not callable(verifier) or not callable(clock):
            raise EvidenceGateError('Configured human authentication required')
        if type(reauth_seconds) is not int or not 1<=reauth_seconds<=300:
            raise EvidenceGateError('Bounded explicit reauthentication duration required')
        if current_verifier is not None and not callable(current_verifier): raise EvidenceGateError('Configured current session verifier required')
        self.namespace=namespace; self._verifier=verifier; self._current_verifier=current_verifier; self._duration=reauth_seconds; self._clock=clock; self._tickets={}

    def authenticate(self,proof):
        identity=self._verifier(proof)
        if not isinstance(identity,HumanIdentity) or not isinstance(identity.roles,tuple) or 'ProductOwner' not in identity.roles:
            raise EvidenceGateError('Verified ProductOwner reauthentication required')
        text(identity.actor)
        now=self._clock(); utc(stamp(now)); nonce=secrets.token_bytes(32)
        self._tickets={key:value for key,value in self._tickets.items() if value[1]>now}
        self._tickets[nonce]=(identity,now+timedelta(seconds=self._duration),proof)
        return _AuthenticatedHuman(self,nonce)

    def authorize(self,human):
        if not isinstance(human,_AuthenticatedHuman) or human._issuer is not self:
            raise EvidenceGateError('Human capability not issued by this authenticated server')
        ticket=self._tickets.get(human._nonce)
        if ticket is None or ticket[1]<=self._clock(): raise EvidenceGateError('Human reauthentication expired/revoked')
        if self._current_verifier is not None and self._current_verifier(ticket[2])!=ticket[0]:
            self._tickets.pop(human._nonce,None)
            raise EvidenceGateError('Current server session expired/revoked')
        return ticket[0].actor

    def revoke(self,human):
        self.authorize(human); self._tickets.pop(human._nonce)

    def deadline(self,human):
        self.authorize(human); return self._tickets[human._nonce][1]


@dataclass(frozen=True)
class OwnerEvidence:
    kind: str
    identity: StrategyIdentity
    strategy_content_hash: str
    release: ReleaseBinding
    payload_json: str


@dataclass(frozen=True)
class OwnerGateRecord:
    evidence_id: str
    kind: str
    identity: StrategyIdentity
    strategy_content_hash: str
    namespace: str
    release_json: str
    release_hash: str
    actor: str
    command_id: str
    expected_revision: int
    payload_json: str
    payload_hash: str
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class HumanApprovalRecord:
    approval_record_id: str
    identity: StrategyIdentity
    namespace: str
    actor: str
    command_id: str
    expected_revision: int
    envelope_json: str
    envelope_hash: str
    payload_json: str
    payload_hash: str
    recorded_at: str


@dataclass(frozen=True)
class CurrentRuntimePermission:
    """Readonly exact owner interpretation; never a transport/process capability."""
    identity: StrategyIdentity
    strategy_content_hash: str
    registry_revision: int
    permission: str
    namespace: str
    release: ReleaseBinding
    approval_record_id: str
    approval_envelope_hash: str
    activation_evidence_id: str
    activation_payload_hash: str
    observed_at: str
    execution: str


class ProductLifecycleComposition:
    """Configured owner evidence resolvers; all request-facing methods take refs.

    current_release must be a bounded local snapshot reader. Evidence production
    occurs before SQLite locks. Real admission additionally invokes the current
    E7/E5/E4 owner verifier; absent owner integration is denied, never inferred.
    """
    def __init__(self,*,namespace: str,current_release: Callable[[],ReleaseBinding],
                 resolve_evidence: Callable[[str,str,StrategyIdentity],OwnerEvidence],
                 authenticator: HumanAuthenticator,clock: Callable[[],datetime],
                 verify_runtime_admission: Callable[[OwnerEvidence,ReleaseBinding],None] | None=None):
        if namespace not in ('FIXTURE','LOCAL_RESEARCH') or not callable(current_release) or not callable(resolve_evidence) or not callable(clock):
            raise EvidenceGateError('Explicit lifecycle owner composition required')
        if not isinstance(authenticator,HumanAuthenticator) or authenticator.namespace!=namespace:
            raise EvidenceGateError('Same-namespace authenticated human authority required')
        self.namespace=namespace; self.authenticator=authenticator; self.clock=clock
        self._current=current_release; self._resolve=resolve_evidence; self._admission=verify_runtime_admission; self._envelopes={}
        self._paper_policies={}; self._selected_paper_policy=None

    def current(self):
        from strategy.v02.capabilities import _revision
        value=self._current()
        if not isinstance(value,ReleaseBinding) or value.namespace!=self.namespace or value.implementation_hash!=_revision():
            raise EvidenceGateError('Current exact release source/namespace mismatch')
        utc(stamp(self.clock()))
        return value

    def register_envelope(self,reference,envelope):
        """Trusted local commissioning registration; not an author/cloud command."""
        text(reference); raw=canonical(envelope)
        if len(raw.encode())>65536: raise EvidenceGateError('Envelope size limit')
        old=self._envelopes.get(reference)
        if old is not None and old!=raw: raise EvidenceGateError('Immutable envelope reference conflict')
        self._envelopes[reference]=raw

    def envelope(self,reference,strategy,risk_policy_json):
        raw=self._envelopes.get(text(reference))
        if raw is None: raise EvidenceGateError('Selected local deployment envelope required')
        return validate_envelope(raw,strategy,self.current(),risk_policy_json,self.clock())

    def select_paper_policy(self,reference,value):
        """Trusted local policy selection, never a strategy-package threshold."""
        from validation.paper_policy import parse_paper_promotion_policy
        reference=text(reference); policy=parse_paper_promotion_policy(value,namespace=self.namespace)
        old=self._paper_policies.get(reference)
        if old is not None and old.canonical_json!=policy.canonical_json: raise EvidenceGateError('Immutable PAPER policy reference conflict')
        self._paper_policies[reference]=policy; self._selected_paper_policy=reference

    def validate_paper_selection(self,body):
        reference=body.get('paper_policy_ref'); policy=self._paper_policies.get(reference) if isinstance(reference,str) else None
        if policy is None or reference!=self._selected_paper_policy or body.get('policy_hash')!=policy.policy_hash:
            raise EvidenceGateError('Current selected local PAPER policy required')
        return policy

    def validate_real_forward(self,body,policy):
        from indicators.v02.common import finite_decimal
        p=policy.as_dict(); thresholds=policy.validation_policy
        try:
            for field in ('actual_elapsed_seconds','actual_healthy_seconds','closed_trades','losses','max_consecutive_losses','max_observed_gap_seconds'):
                if type(body[field]) is not int or body[field]<0: raise EvidenceGateError('Actual bounded forward counts required')
            elapsed=body['actual_elapsed_seconds']; healthy=body['actual_healthy_seconds']; gap=body['max_observed_gap_seconds']
            observed=utc(body['observed_at']); started=utc(body['started_at']); now=self.clock()
            if body['forward_mode']!='REAL_TIME' or body['execution']!='ACTUAL_OWNER' or body['status']!='PASS' or not started<=observed<=now:
                raise EvidenceGateError('Actual chronological real-time forward assessment required')
            if elapsed>int((observed-started).total_seconds()) or elapsed<p['min_elapsed_seconds'] or healthy>elapsed or healthy<p['required_healthy_seconds'] or gap>p['maximum_observation_gap_seconds'] or (now-observed).total_seconds()>p['maximum_observation_gap_seconds']:
                raise EvidenceGateError('Forward duration/health/freshness threshold not satisfied')
            if body['closed_trades']<thresholds.min_total_trades or body['losses']>body['closed_trades']:
                raise EvidenceGateError('Sufficient actual forward closed trades required')
            if body['max_consecutive_losses']>body['losses'] or finite_decimal(body['max_drawdown_usdt'])<0:
                raise EvidenceGateError('Impossible forward financial metrics')
            if finite_decimal(body['net_pnl_usdt'])<thresholds.min_net_pnl or finite_decimal(body['expectancy_usdt_per_trade'])<finite_decimal(p['min_expectancy_usdt_per_trade']) or finite_decimal(body['max_drawdown_usdt'])>thresholds.max_drawdown or body['max_consecutive_losses']>thresholds.max_consecutive_losses:
                raise EvidenceGateError('Forward financial threshold failed')
            profit_factor=body['profit_factor']
            if profit_factor is None:
                if p['profit_factor_null_handling']=='BLOCK' or body['losses']>0: raise EvidenceGateError('Undefined forward profit factor')
            elif finite_decimal(profit_factor)<finite_decimal(p['min_profit_factor']): raise EvidenceGateError('Forward profit factor failed')
        except (KeyError,TypeError,ValueError) as exc:
            raise EvidenceGateError('Actual complete forward evidence required') from exc

    def resolve(self,kind,reference,strategy):
        release=self.current(); proof=self._resolve(kind,text(reference),strategy.identity)
        if not isinstance(proof,OwnerEvidence) or proof.kind!=kind or proof.identity!=strategy.identity or proof.strategy_content_hash!=strategy.content_hash or proof.release!=release:
            raise EvidenceGateError('Exact current owner evidence required')
        if len(proof.payload_json.encode())>262144: raise EvidenceGateError('Owner evidence size limit')
        try: body=json.loads(proof.payload_json)
        except (ValueError,TypeError) as exc: raise EvidenceGateError('Owner evidence JSON required') from exc
        if not isinstance(body,dict) or body.get('evidence_ref')!=reference:
            raise EvidenceGateError('Resolved owner evidence reference mismatch')
        if release.namespace=='FIXTURE':
            if body.get('execution')!='SIMULATED_MECHANICS' or release.release_kind!='FIXTURE' or body.get('entries_enabled') is not False:
                raise EvidenceGateError('Explicit isolated fixture mechanics required')
        elif body.get('execution')!='ACTUAL_OWNER':
            raise EvidenceGateError('Actual owning producer execution required')
        if kind=='PAPER_START' and body.get('broker_kind')!='PAPER_ONLY':
            raise EvidenceGateError('No provider mutation path may enter PAPER')
        if kind in ('PAPER_START','FORWARD_READY'): policy=self.validate_paper_selection(body)
        if kind=='FORWARD_READY' and release.namespace!='FIXTURE':
            self.validate_real_forward(body,policy)
        if kind in ('ACTIVATION','RESUMPTION') and release.namespace!='FIXTURE':
            if not callable(self._admission): raise EvidenceGateError('Current E7/E5/E4 admission producer is not configured')
            self._admission(proof,release)
        return canonical(body),release


def validate_envelope(raw,strategy,release,risk_policy_json,now):
    from risk.product_policy import parse_product_risk_policy
    try: value=json.loads(raw)
    except (ValueError,TypeError) as exc: raise EvidenceGateError('Envelope JSON required') from exc
    fields={'schema_version','envelope_id','namespace','strategy_id','strategy_version','strategy_content_hash','release','symbol',
        'capital_ceiling_usdt','risk_per_trade_usdt','max_positions','daily_loss_limit_usdt','aggregate_loss_limit_usdt',
        'permissions','generation','valid_from','expires_at'}
    if not isinstance(value,dict) or set(value)!=fields or value['schema_version']!='r7-deployment-envelope-v0.2':
        raise EvidenceGateError('Strict versioned deployment envelope required')
    if (value['strategy_id'],value['strategy_version'],value['strategy_content_hash'],value['symbol'])!=(strategy.identity.strategy_id,strategy.identity.strategy_version,strategy.content_hash,strategy.symbol):
        raise EvidenceGateError('Envelope bound to another exact strategy')
    if value['namespace']!=release.namespace or value['release']!=release.as_dict(): raise EvidenceGateError('Envelope release/policy/config/generation changed')
    text(value['envelope_id'])
    for field in ('generation','max_positions'):
        if type(value[field]) is not int or not 1<=value[field]<=2147483647: raise EvidenceGateError('Explicit envelope generation/position limit required')
    if not isinstance(value['permissions'],list) or sorted(set(value['permissions']))!=value['permissions'] or not set(value['permissions'])<= {'NEW_EXPOSURE','MANAGE_EXISTING'} or not value['permissions']:
        raise EvidenceGateError('Explicit bounded deployment permissions required')
    if not utc(value['valid_from'])<=now<utc(value['expires_at']): raise EvidenceGateError('Envelope not current or expired')
    if risk_policy_json is None or digest(risk_policy_json)!=release.risk_policy_hash: raise EvidenceGateError('Selected E5 risk policy mismatch')
    selected=parse_product_risk_policy(json.loads(risk_policy_json),namespace=release.namespace)
    if json.loads(selected.canonical_json)['generation']!=release.risk_generation: raise EvidenceGateError('Risk generation changed')
    amounts={}
    for field in ('capital_ceiling_usdt','risk_per_trade_usdt','daily_loss_limit_usdt','aggregate_loss_limit_usdt'):
        amount=value[field]
        if not isinstance(amount,str) or len(amount)>128: raise EvidenceGateError('Explicit USDT decimal amounts required')
        try: amounts[field]=Decimal(amount)
        except Exception as exc: raise EvidenceGateError('Finite positive envelope amounts required') from exc
        if not amounts[field].is_finite() or amounts[field]<=0: raise EvidenceGateError('Finite positive envelope amounts required')
    risk=selected.risk_policy
    if risk.max_margin>amounts['capital_ceiling_usdt'] or value['max_positions']>risk.max_open_positions or amounts['risk_per_trade_usdt']>amounts['daily_loss_limit_usdt'] or amounts['daily_loss_limit_usdt']>amounts['aggregate_loss_limit_usdt'] or amounts['aggregate_loss_limit_usdt']>risk.max_drawdown:
        raise EvidenceGateError('Deployment envelope exceeds selected E5 limits')
    return canonical(value)


def require_current_approval(store,strategy,boundary,approval_id=None):
    approval=store.get_human_approval(approval_id) if approval_id is not None else store.latest_human_approval(strategy.identity)
    if approval is None or approval.identity!=strategy.identity or approval.namespace!=boundary.namespace:
        raise EvidenceGateError('Immutable exact-subject human approval required')
    if digest(approval.payload_json)!=approval.payload_hash or digest(approval.envelope_json)!=approval.envelope_hash:
        raise EvidenceGateError('Approval content commitment mismatch')
    payload=json.loads(approval.payload_json)
    if payload['decision']!='APPROVE' or payload['actor']!=approval.actor or payload['subject_id']!=strategy.identity.strategy_id or payload['subject_version']!=strategy.identity.strategy_version:
        raise EvidenceGateError('Canonical human approval subject/decision mismatch')
    if store.approval_is_revoked(approval.approval_record_id): raise EvidenceGateError('Approval revoked')
    forward=store.ready_forward_evidence(strategy.identity)
    if forward is None or forward.kind!='FORWARD_READY' or forward.identity!=strategy.identity or forward.namespace!=boundary.namespace or forward.strategy_content_hash!=strategy.content_hash or digest(forward.payload_json)!=forward.payload_hash:
        raise EvidenceGateError('Executed forward readiness lineage required')
    boundary.validate_paper_selection(json.loads(forward.payload_json))
    product=store.candidate_product_assessment(strategy.identity)
    if product is None: raise EvidenceGateError('Candidate product lineage missing')
    validate_envelope(approval.envelope_json,strategy,boundary.current(),product.risk_policy_json,boundary.clock())
    return approval


def require_owner_transition(store,strategy,transition):
    from .product_assessment import require_product_candidate
    kinds={('CANDIDATE','PAPER'):'PAPER_START',('PAPER','READY_FOR_APPROVAL'):'FORWARD_READY',
        ('READY_FOR_APPROVAL','APPROVED'):'APPROVAL',('APPROVED','LIVE'):'ACTIVATION',('DEGRADED','LIVE'):'RESUMPTION'}
    kind=kinds.get((transition.previous_state,transition.new_state))
    boundary=getattr(store,'_lifecycle_boundary',None)
    if not isinstance(boundary,ProductLifecycleComposition) or kind is None:
        raise EvidenceGateError('Configured current lifecycle owner authority required')
    gate=store.get_owner_evidence(transition.owner_evidence_id)
    if gate is None or gate.kind!=kind or gate.identity!=strategy.identity or gate.strategy_content_hash!=strategy.content_hash:
        raise EvidenceGateError('Exact stored owner evidence required')
    if gate.namespace!=boundary.namespace or gate.namespace!=store.get_research_namespace() or gate.actor!=transition.changed_by or gate.expected_revision!=strategy.registry_revision:
        raise EvidenceGateError('Owner evidence actor/namespace/revision mismatch')
    release=boundary.current()
    if canonical(release.as_dict())!=gate.release_json or digest(gate.release_json)!=gate.release_hash or digest(gate.payload_json)!=gate.payload_hash:
        raise EvidenceGateError('Owner evidence release/config/source commitment mismatch')
    now=boundary.clock()
    if not utc(gate.issued_at)<=now<utc(gate.expires_at): raise EvidenceGateError('Owner evidence expired or from the future')
    product=store.candidate_product_assessment(strategy.identity)
    if product is None: raise EvidenceGateError('Complete candidate lineage required')
    require_product_candidate(store,strategy,product.validation_evidence_id)
    if product.risk_policy_hash!=release.risk_policy_hash:
        raise EvidenceGateError('Selected risk generation changed since research')
    if kind in ('PAPER_START','FORWARD_READY'):
        body=json.loads(gate.payload_json); policy=boundary.validate_paper_selection(body)
        if kind=='FORWARD_READY' and boundary.namespace!='FIXTURE': boundary.validate_real_forward(body,policy)
    if kind in ('APPROVAL','ACTIVATION','RESUMPTION'):
        body=json.loads(gate.payload_json)
        approval=require_current_approval(store,strategy,boundary,body['approval_record_id'])
        if kind in ('ACTIVATION','RESUMPTION') and 'NEW_EXPOSURE' not in json.loads(approval.envelope_json)['permissions']:
            raise EvidenceGateError('Deployment envelope does not permit new exposure')
