"""Trusted thread-local actual PAPER owner composition; no release issuer.

The caller installs an existing owning release reader and authenticator. Policy
selection never manufactures qualified release/build/configuration generations.
There is no API/package/plugin path that installs a callback or imports PASS.
"""
from contextlib import ExitStack,contextmanager
from dataclasses import dataclass
from datetime import datetime,timezone
import json
import re
from pathlib import Path

from application.config import ProductConfig
from application.platform.restoration import require_valid_restoration
from application.platform.resources import require_local_database_volume
from application.platform.supervision import _local_path
from execution.models import require_utc
from registry import EvidenceGateError,StrategyIdentity
from registry.operational_authority import ProductLifecycleComposition,HumanAuthenticator
from registry.product_assessment import canonical,digest
from risk.product_policy import parse_product_risk_policy
from storage import open_sqlite_platform
from storage.paper_process import open_paper_process_journal
from validation.paper_policy import parse_paper_promotion_policy
from .policy import parse_simulation_policy,bind_submission_validity
from .service import PaperService


@dataclass(frozen=True,init=False)
class PaperOwnerSelection:
    namespace:str
    canonical_json:str
    selection_hash:str

    def __init__(self,*,namespace,simulation_policy,risk_policy,promotion_policy,
                 paper_policy_ref,submission_validity,actor,workflow_authorized):
        if namespace not in ('FIXTURE','LOCAL_RESEARCH') or type(workflow_authorized) is not bool:
            raise ValueError('Explicit same-namespace PAPER workflow selection required')
        if any(not isinstance(value,str) or not value.strip() or len(value)>256 for value in (actor,paper_policy_ref)):
            raise ValueError('Bounded configured PAPER actor and policy reference required')
        simulation=parse_simulation_policy(simulation_policy,namespace=namespace)
        risk=parse_product_risk_policy(risk_policy,namespace=namespace)
        promotion=parse_paper_promotion_policy(promotion_policy,namespace=namespace)
        validity=bind_submission_validity(submission_validity,datetime.now(timezone.utc))
        raw=canonical(dict(namespace=namespace,simulation_policy=simulation.as_dict(),
            risk_policy=json.loads(risk.canonical_json),promotion_policy=promotion.as_dict(),
            paper_policy_ref=paper_policy_ref,submission_validity=json.loads(validity),actor=actor,
            workflow_authorized=workflow_authorized))
        if len(raw.encode('utf-8'))>65536:raise ValueError('Bounded PAPER owner selection required')
        object.__setattr__(self,'namespace',namespace)
        object.__setattr__(self,'canonical_json',raw)
        object.__setattr__(self,'selection_hash',digest(raw))

    def as_dict(self):
        return json.loads(self.canonical_json)


class PaperOwnerComposition:
    def __init__(self,config,*,selection,current_release,authenticator,clock,strategy_identity=None,operational_generation=None,implementation_hash=None,funding_source=None,funding_admission=None):
        if (not isinstance(config,ProductConfig) or not isinstance(selection,PaperOwnerSelection)
                or not isinstance(authenticator,HumanAuthenticator) or authenticator.namespace!=selection.namespace
                or not callable(current_release) or not callable(clock)):
            raise ValueError('Trusted selected PAPER owners and current release reader required')
        if (not isinstance(config.database_path,Path) or not isinstance(config.local_data_root,Path)
                or not config.local_data_root.is_absolute() or not config.database_path.is_absolute()
                or '..' in config.local_data_root.parts or '..' in config.database_path.parts
                or config.database_path==config.local_data_root or not config.database_path.is_relative_to(config.local_data_root)):
            raise ValueError('Canonical PAPER store inside configured local root required')
        self.config=config
        if strategy_identity is not None and not isinstance(strategy_identity,StrategyIdentity):
            raise ValueError('Actual selected PAPER strategy identity required')
        self.strategy_identity=strategy_identity
        if operational_generation is not None and (type(operational_generation) is not int
                or not 1<=operational_generation<=2147483647 or selection.namespace!='LOCAL_RESEARCH'):
            raise ValueError('Actual protected ordinary selection generation required')
        self.operational_generation=operational_generation
        if implementation_hash is not None and (type(implementation_hash) is not str
                or not re.fullmatch('sha256:[0-9a-f]{64}',implementation_hash)):
            raise ValueError('Trusted selected owner source commitment required')
        self.implementation_hash=implementation_hash
        self.selection=PaperOwnerSelection(**selection.as_dict())
        self.funding_source=funding_source
        self.funding_admission=funding_admission
        self.current_release=current_release;self.authenticator=authenticator;self.clock=clock

    @contextmanager
    def service(self):
        # Validate first; every connection is opened/closed on this caller thread.
        require_utc(self.clock(),'PAPER owner composition now')
        restoration=require_valid_restoration(self.config)
        _local_path(self.config.database_path);require_local_database_volume(self.config.database_path)
        selected=PaperOwnerSelection(**self.selection.as_dict()).as_dict()
        namespace=selected.pop('namespace')
        if namespace!=self.authenticator.namespace:
            raise ValueError('Same-namespace PAPER authenticator required')
        authorized=selected['workflow_authorized'] and restoration['status']=='NOT_RESTORED'
        if namespace=='LOCAL_RESEARCH':
            authorized=authorized and not self.config.diagnostic_only and self.config.paper_runtime_enabled
        selected['workflow_authorized']=authorized
        service=None
        def resolve(kind,reference,identity):
            if service is None:raise EvidenceGateError('Actual PAPER owner is not composed')
            return service.resolve_owner_evidence(kind,reference,identity)
        boundary=ProductLifecycleComposition(namespace=namespace,current_release=self.current_release,
            resolve_evidence=resolve,authenticator=self.authenticator,clock=self.clock,implementation_hash=self.implementation_hash)
        boundary.select_paper_policy(selected['paper_policy_ref'],selected['promotion_policy'])
        with ExitStack() as stack:
            registry=stack.enter_context(open_sqlite_platform(self.config.database_path,
                research_namespace=namespace,lifecycle_boundary=boundary,require_existing=True))
            process=stack.enter_context(open_paper_process_journal(self.config.database_path,require_existing=True))
            canonical_journal=stack.enter_context(process.borrow_canonical_journal())
            management_selection=selection_current=entry_current=None
            if namespace=='LOCAL_RESEARCH' and self.operational_generation is not None:
                from storage.paper_selection import open_paper_selections,PaperSelectionError
                from registry.operational_authority import ReleaseBinding
                accepted={}
                def original_release(run_id):
                    if run_id not in accepted:
                        recovered=process.management_snapshot(run_id)
                        identity=StrategyIdentity(recovered.binding['strategy_id'],recovered.binding['strategy_version'])
                        gate=registry.accepted_paper_start_evidence(identity)
                        if json.loads(gate.payload_json).get('run_id')!=run_id:
                            raise EvidenceGateError('Exact original accepted Paper run required')
                        accepted[run_id]=ReleaseBinding(**json.loads(gate.release_json))
                    return accepted[run_id]
                def current_selection(run_id):
                    release=original_release(run_id)
                    try:
                        with open_paper_selections(self.config.database_path) as reader:current=reader.current()
                        from application.platform.supervision import config_hash
                        return (current is not None and current.generation==release.config_generation
                            and current.config_hash==release.config_hash
                            and current.as_dict()['envelope']['product_config_hash']==config_hash(self.config))
                    except PaperSelectionError:return False  # Entry denied; original protection continues.
                def original_selection(run_id):
                    release=original_release(run_id)
                    if release.config_generation==self.operational_generation:return None
                    try:
                        with open_paper_selections(self.config.database_path) as reader:original=reader.get(release.config_generation)
                        if original is None or original.config_hash!=release.config_hash:
                            raise EvidenceGateError('Original protected Paper selection missing or changed')
                        record=original.as_dict();envelope=record['envelope']
                        if (envelope['simulator_profile_hash']!=release.provider_profile_hash
                                or envelope['account_ref']!=release.account_ref):
                            raise EvidenceGateError('Original Paper simulator/account commitment changed')
                        from .release import _historical_owner
                        owner=_historical_owner(record,implementation_hash=release.implementation_hash)
                        risk=parse_product_risk_policy(owner.as_dict()['risk_policy'],namespace=namespace)
                        if (risk.policy_hash!=release.risk_policy_hash
                                or owner.as_dict()['risk_policy']['generation']!=release.risk_generation):
                            raise EvidenceGateError('Original exact E5 risk commitment changed')
                        return owner
                    except (ValueError,TypeError,KeyError) as error:
                        raise EvidenceGateError('Original Paper selection reconciliation required') from error
                management_selection,selection_current=original_selection,current_selection
                def current_entry(run_id):
                    if not current_selection(run_id):return False
                    original=original_release(run_id);current=self.current_release()
                    if not isinstance(current,ReleaseBinding) or current.release_kind!='NATIVE_QUALIFIED':return False
                    from dataclasses import asdict
                    left,right=asdict(original),asdict(current)
                    # Actual successor runtime is independently observed. Its
                    # process generation does not rewrite the original E6 run.
                    left.pop('runtime_generation');right.pop('runtime_generation')
                    return left==right
                entry_current=current_entry
            service=PaperService(registry=registry,process_journal=process,canonical_journal=canonical_journal,
                namespace=namespace,current_release=self.current_release,clock=self.clock,
                strategy_identity=self.strategy_identity,management_selection=management_selection,
                selection_current=selection_current,entry_current=entry_current,implementation_hash=self.implementation_hash,
                funding_source=self.funding_source,funding_admission=self.funding_admission,**selected)
            yield service


__all__=['PaperOwnerSelection','PaperOwnerComposition']
