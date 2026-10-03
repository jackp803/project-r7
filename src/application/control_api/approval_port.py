"""Exact registered subject/envelope approval through actual authenticated E6."""
import json
from application.control_api.auth import _stamp
from application.control_api.errors import APIError
from registry import StrategyIdentity, StrategyPlatformService
from registry.operational_authority import HumanAuthenticator
from registry.product_assessment import digest
from registry.models import ConcurrencyConflict, EvidenceGateError, RegistryError


class ApprovalControlPort:
    def __init__(self,*,namespace,registry_factory):
        if namespace not in ('FIXTURE','LOCAL_RESEARCH') or not callable(registry_factory):
            raise ValueError('Explicit local approval owner composition required')
        self.namespace,self.factory,self.issuer=namespace,registry_factory,None

    def install_authenticator(self,issuer):
        if not isinstance(issuer,HumanAuthenticator) or issuer.namespace!=self.namespace:
            raise ValueError('Current same-namespace server authenticator required')
        self.issuer=issuer

    def _factory(self):
        if self.issuer is None: raise APIError('NOT_CONFIGURED','CURRENT_SERVER_AUTHENTICATION_REQUIRED',503)
        return self.factory(self.issuer)

    def revision(self,arguments):
        with self._factory() as e6:
            if not isinstance(e6,StrategyPlatformService) or e6.research_namespace!=self.namespace:
                raise APIError('NOT_CONFIGURED','ACTUAL_SAME_NAMESPACE_E6_REQUIRED',503)
            return e6.get_strategy(StrategyIdentity(arguments['strategy_id'],arguments['strategy_version'])).registry_revision

    def preview(self,identity,*,envelope_ref,expected_revision):
        try:
            with self._factory() as e6:
                if not isinstance(e6,StrategyPlatformService) or e6.research_namespace!=self.namespace:
                    raise APIError('NOT_CONFIGURED','ACTUAL_SAME_NAMESPACE_E6_REQUIRED',503)
                subject=e6.deployment_approval_preview(identity,envelope_ref=envelope_ref,expected_revision=expected_revision)
            product=json.loads(subject.product_assessment_json)
            # Only owning canonical assessment fields enter the browser. Retained
            # arbitrary provider/error/host payloads cannot become a proposal.
            keys=('schema_version','run_id','namespace','strategy_content_hash','status','independent_oos',
                  'sealed_backtest','canonical_oos_decision','robustness_hash','raw_result_hashes','reason_codes')
            assessment={key:product[key] for key in keys if key in product}
            envelope=json.loads(subject.envelope_json)
            return dict(strategy_id=identity.strategy_id,strategy_version=identity.strategy_version,
                strategy_content_hash=subject.strategy_content_hash,registry_revision=subject.registry_revision,
                namespace=subject.namespace,envelope_ref=subject.envelope_ref,envelope_hash=subject.envelope_hash,
                envelope=envelope,release=envelope['release'],risk_policy=json.loads(subject.risk_policy_json),
                risk_policy_hash=subject.risk_policy_hash,product_assessment=assessment,
                product_assessment_hash=subject.product_assessment_hash,evidence_ref=subject.evidence_ref,
                observed_at=subject.observed_at,financial_confirmation_available=self.namespace=='LOCAL_RESEARCH',
                reason_codes=['FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN'] if self.namespace=='FIXTURE' else ['PREVIEW_IS_NOT_APPROVAL'])
        except ConcurrencyConflict:
            raise APIError('CONFLICT','APPROVAL_SUBJECT_CHANGED',409) from None
        except (EvidenceGateError,RegistryError,ValueError,KeyError,TypeError):
            raise APIError('CONFLICT','CURRENT_APPROVAL_PROPOSAL_UNAVAILABLE',409) from None

    def record(self,arguments,*,actor,human,command_id,expected_revision):
        if self.namespace=='FIXTURE': raise APIError('AUTHORIZATION_REQUIRED','FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN',403)
        if self.issuer is None or self.issuer.authorize(human)!=actor:
            raise APIError('AUTHORIZATION_REQUIRED','SERVER_BOUND_ACTOR_REQUIRED',403)
        identity=StrategyIdentity(arguments['strategy_id'],arguments['strategy_version'])
        with self._factory() as e6:
            if not isinstance(e6,StrategyPlatformService) or e6.research_namespace!=self.namespace:
                raise APIError('NOT_CONFIGURED','ACTUAL_SAME_NAMESPACE_E6_REQUIRED',503)
            strategy=e6.get_strategy(identity)
            cached=e6.human_approval_for_command(command_id)
            if strategy.content_hash!=arguments['expected_strategy_hash']:
                raise APIError('CONFLICT','APPROVAL_SUBJECT_CHANGED',409)
            if cached is None:
                envelope=e6.current_deployment_envelope(identity,envelope_ref=arguments['envelope_ref'],expected_revision=expected_revision)
                envelope_hash=digest(envelope)
            else:
                # Reconcile a lost API receipt against immutable owning evidence;
                # current session authority is still required, never its audit.
                if cached.identity!=identity or cached.actor!=actor or cached.expected_revision!=expected_revision:
                    raise APIError('CONFLICT','APPROVAL_COMMAND_CONFLICT',409)
                envelope_hash=cached.envelope_hash
            if envelope_hash!=arguments['expected_envelope_hash']:
                raise APIError('CONFLICT','APPROVAL_ENVELOPE_CHANGED',409)
            result=e6.record_approval(identity,envelope_ref=arguments['envelope_ref'],authenticated_human=human,
                decision=arguments['decision'],reason=arguments['reason_code'],command_id=command_id,expected_revision=expected_revision)
            record=e6.human_approval_for_command(command_id)
            if record is None: raise APIError('UNAVAILABLE','ACTUAL_APPROVAL_RECEIPT_REQUIRED',503)
            return dict(command_id=command_id,actor=actor,resource='strategy:'+identity.strategy_id+':'+identity.strategy_version,
                expected_revision=expected_revision,resource_revision=result.registry_revision,status='COMPLETE',
                effect_ref='e6-approval:'+record.approval_record_id,reason_codes=['HUMAN_'+arguments['decision']+'_RECORDED'],observed_at=record.recorded_at)
