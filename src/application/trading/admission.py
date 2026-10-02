"""Current E6 consent plus actual E7 interpreter, rechecked at every effect.

Opaque permits are transient/issuer-local. Retained JSON or a receipt cannot
renew them. Fixture permits are restricted to explicitly fake-provider tests.
No credential read, network, process launch or native health claim occurs here.
"""
from dataclasses import dataclass
from datetime import timedelta
import secrets
from integration.product_runtime_preflight import evaluate_product_runtime_preflight
from integration.runtime_preflight import RuntimePreflightValidationError
from registry import StrategyIdentity,StrategyPlatformService
from registry.models import RegistryError
from registry.operational_authority import utc,stamp


class RuntimeAdmissionError(ValueError):
    def __init__(self,*reasons):self.reason_codes=tuple(reasons);super().__init__(','.join(reasons))


@dataclass(frozen=True)
class AdmissionDecision:
    allowed:bool
    reason_codes:tuple[str,...]
    owner_permission:object=None
    preflight_id:str|None=None
    process_binding:tuple[str,str]|None=None


class _RuntimePermit:
    __slots__=('_issuer','_nonce')
    def __init__(self,issuer,nonce):self._issuer=issuer;self._nonce=nonce
    def __repr__(self):return '<transient runtime permit>'


class RuntimeAdmission:
    def __init__(self,*,namespace,registry_factory,current_preflight,clock,maximum_observation_age_seconds):
        if namespace not in ('FIXTURE','LOCAL_RESEARCH') or not all(callable(item) for item in (registry_factory,current_preflight,clock)):
            raise RuntimeAdmissionError('EXPLICIT_CURRENT_OWNER_COMPOSITION_REQUIRED')
        if type(maximum_observation_age_seconds) is not int or not 1<=maximum_observation_age_seconds<=30:
            raise RuntimeAdmissionError('BOUNDED_CURRENT_OBSERVATION_POLICY_REQUIRED')
        self.namespace=namespace;self.factory=registry_factory;self.current_preflight=current_preflight;self.clock=clock
        self.maximum_age=maximum_observation_age_seconds;self._permits={}

    def evaluate(self,identity,*,expected_revision,permission,execution):
        if not isinstance(identity,StrategyIdentity) or permission not in ('NEW_EXPOSURE','MANAGE_EXISTING') or execution not in ('PRODUCTION','FAKE_PROVIDER_VERIFICATION'):
            return AdmissionDecision(False,('EXACT_RUNTIME_SUBJECT_AND_PURPOSE_REQUIRED',))
        if self.namespace=='FIXTURE' and execution!='FAKE_PROVIDER_VERIFICATION':return AdmissionDecision(False,('FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN',))
        if self.namespace!='FIXTURE' and execution!='PRODUCTION':return AdmissionDecision(False,('FAKE_PROVIDER_NAMESPACE_REQUIRED',))
        try:
            with self.factory() as e6:
                if not isinstance(e6,StrategyPlatformService) or e6.research_namespace!=self.namespace:
                    return AdmissionDecision(False,('ACTUAL_SAME_NAMESPACE_E6_REQUIRED',))
                owner=e6.current_runtime_permission(identity,expected_revision=expected_revision,permission=permission)
            value,authority=self.current_preflight();preflight=evaluate_product_runtime_preflight(value,authority)
            if preflight['preflight_status']!='ELIGIBLE':return AdmissionDecision(False,tuple(preflight['reason_codes']))
            release=owner.release;now=self.clock();utc(stamp(now))
            clocks=[value.evaluated_at,value.heartbeat_evidence['heartbeat_observed_at'],value.reconciliation_evidence['reconciliation_observed_at']]
            if any(not 0<=(now-utc(item)).total_seconds()<=self.maximum_age for item in clocks):return AdmissionDecision(False,('CURRENT_OWNER_OBSERVATION_STALE',))
            if (value.project_revision!=release.executable_revision or value.runtime_config_hash!=release.config_hash or
                value.runtime_config_generation_id!='config-generation:'+str(release.config_generation) or
                value.process_start_generation_id!='runtime-generation:'+str(release.runtime_generation) or
                value.capability_evidence['capability_snapshot_hash']!=release.capability_hash):
                return AdmissionDecision(False,('EXACT_E6_E7_RELEASE_GENERATION_REQUIRED',))
            return AdmissionDecision(True,('CURRENT_OWNER_ADMISSION_ELIGIBLE',),owner,preflight['runtime_preflight_id'],(value.process_instance_id,value.process_start_generation_id))
        except (RegistryError,RuntimePreflightValidationError):return AdmissionDecision(False,('CURRENT_OWNER_AUTHORITY_UNAVAILABLE',))
        except (ValueError,TypeError,AttributeError,KeyError):return AdmissionDecision(False,('CURRENT_OWNER_EVIDENCE_INVALID',))

    def issue(self,identity,*,expected_revision,permission,execution):
        decision=self.evaluate(identity,expected_revision=expected_revision,permission=permission,execution=execution)
        if not decision.allowed:raise RuntimeAdmissionError(*decision.reason_codes)
        now=self.clock();self._permits={key:value for key,value in self._permits.items() if value['expires']>now}
        if len(self._permits)>=1024:raise RuntimeAdmissionError('TRANSIENT_RUNTIME_PERMIT_LIMIT')
        nonce=secrets.token_bytes(32)
        self._permits[nonce]=dict(identity=identity,revision=expected_revision,permission=permission,execution=execution,
            owner=decision.owner_permission,process_binding=decision.process_binding,expires=now+timedelta(seconds=1))
        return _RuntimePermit(self,nonce)

    def require(self,permit,*,identity,permission,execution):
        if type(permit) is not _RuntimePermit or permit._issuer is not self:raise RuntimeAdmissionError('CURRENT_ISSUER_RUNTIME_PERMIT_REQUIRED')
        saved=self._permits.get(permit._nonce)
        if saved is None or saved['expires']<=self.clock() or (saved['identity'],saved['permission'],saved['execution'])!=(identity,permission,execution):
            raise RuntimeAdmissionError('CURRENT_EXACT_RUNTIME_PERMIT_REQUIRED')
        current=self.evaluate(identity,expected_revision=saved['revision'],permission=permission,execution=execution)
        if not current.allowed:raise RuntimeAdmissionError(*current.reason_codes)
        if current.process_binding!=saved['process_binding']:raise RuntimeAdmissionError('RUNTIME_PERMIT_PROCESS_CHANGED')
        # Current observation timestamps may advance; authority identities may not.
        before= saved['owner'];after=current.owner_permission
        fields=('identity','strategy_content_hash','registry_revision','permission','namespace','release','approval_record_id','approval_envelope_hash','activation_evidence_id','activation_payload_hash','execution')
        if any(getattr(before,name)!=getattr(after,name) for name in fields):raise RuntimeAdmissionError('RUNTIME_OWNER_PERMISSION_CHANGED')
        return current.owner_permission
