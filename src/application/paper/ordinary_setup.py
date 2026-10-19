"""Explicit normal Paper setup and original E6 owner composition; no defaults."""
from contextlib import ExitStack
from datetime import datetime,timezone
import os
from pathlib import Path
import re

from application.config import load_config,product_namespace
from application.cloud.manifest import safe_component,safe_relative,validate_package
from application.cloud.protocol import CloudError
from application.cloud.safe_files import _windows_read,_posix_read
from application.datasets.catalog import decode,read_local,digest
from application.platform.restoration import require_valid_restoration
from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from registry import EvidenceGateError,StrategyIdentity
from registry.operational_authority import HumanAuthenticator
from storage.paper_selection import open_paper_selections,_open_paper_selection_owner
from strategy.v02.capabilities import build_capability_snapshot
from strategy.v02.temporal import assess_submission_validity
from .owners import PaperOwnerSelection,PaperOwnerComposition
from .release import NativePaperReleaseReader,operational_record,validate_operational_record

INPUT_SCHEMA='r7-local-paper-inputs-v0.2'
INPUT_KEYS={'schema_version','submission_id','simulation_policy_ref','risk_policy_ref','promotion_policy_ref',
    'paper_policy_ref','actor','workflow_authorized','account_ref','qualification_receipt_ref'}
SOURCE_KEYS={'schema_version','submission_id','manifest_hash','strategy','input_refs','input_hashes','qualification_receipt_ref'}


def read_operator_profile(config,path):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts or str(path).startswith(('\\\\','//')):
        raise ValueError('Absolute local operator Paper selection required')
    try:
        resolved=path.resolve(strict=True)
        if config.cloud_root is not None and resolved.is_relative_to(config.cloud_root):
            raise ValueError('Paper selection must be outside cloud staging')
        value=decode((_windows_read if os.name=='nt' else _posix_read)(path,65536,require_single_link=True))
    except (OSError,CloudError):
        raise ValueError('Local operator Paper selection unavailable') from None
    if not isinstance(value,dict) or set(value)!=INPUT_KEYS or value['schema_version']!=INPUT_SCHEMA:
        raise ValueError('Complete explicit ordinary Paper selection required')
    for name in ('submission_id','paper_policy_ref'):safe_component(value[name])
    for name in ('simulation_policy_ref','risk_policy_ref','promotion_policy_ref'):safe_relative(value[name])
    if (type(value['workflow_authorized']) is not bool or any(not isinstance(value[name],str)
            or not value[name].strip() or len(value[name])>256 for name in ('actor','account_ref'))
            or not isinstance(value['qualification_receipt_ref'],str)
            or not re.fullmatch('qualification-[0-9a-f]{64}',value['qualification_receipt_ref'])):
        raise ValueError('Explicit local workflow/actor/account and owning receipt reference required')
    return value


def configure_ordinary_paper(config_path,selection_profile):
    config_path=Path(config_path).absolute()
    config=load_config(config_path)
    selected=read_operator_profile(config,selection_profile)
    if product_namespace(config)!='LOCAL_RESEARCH' or config.diagnostic_only or not config.paper_runtime_enabled:
        raise ValueError('Explicit ordinary Paper runtime profile required')
    from application.entrypoints import _outside_installation
    _outside_installation(config.local_data_root)
    with ExitStack() as stack:
        from application.platform.supervision import PROCESS_ROLES
        for role in PROCESS_ROLES:
            stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
        if load_config(config_path)!=config or require_valid_restoration(config)['status']!='NOT_RESTORED':
            raise ValueError('Unchanged non-restored ordinary profile required')
        # Software eligibility precedes owner initialization. No idle runtime
        # identity is required yet; its generation is observed after bootstrap.
        from .release_observation import check_native_once
        verified,_,_=check_native_once(config_path,selected['qualification_receipt_ref'])
        installed=verified['facts']
        inputs={name:read_local(config.local_data_root,selected[name],65536)
            for name in ('simulation_policy_ref','risk_policy_ref','promotion_policy_ref')}
        from application.local_owners import LocalOwners
        local=LocalOwners(config,namespace='LOCAL_RESEARCH')
        if local.resolver is None:raise ValueError('Actual accepted local research selection required')
        _,package=local.resolver.package(selected['submission_id']);manifest=package.manifest.raw
        owner=PaperOwnerSelection(namespace='LOCAL_RESEARCH',simulation_policy=decode(inputs['simulation_policy_ref']),
            risk_policy=decode(inputs['risk_policy_ref']),promotion_policy=decode(inputs['promotion_policy_ref']),
            paper_policy_ref=selected['paper_policy_ref'],actor=selected['actor'],workflow_authorized=selected['workflow_authorized'],
            submission_validity={key:manifest[key] for key in ('intent_class','validity')})
        record=operational_record(config,owner,account_ref=selected['account_ref'],implementation_hash=installed['implementation_hash'])
        record['source_subject']=dict(schema_version='r7-local-paper-source-subject-v0.2',
            submission_id=selected['submission_id'],manifest_hash=package.manifest.manifest_hash,
            strategy=dict(strategy_id=manifest['strategy_id'],strategy_version=manifest['strategy_version'],
                content_hash=manifest['strategy_content_hash']),
            input_refs={name:selected[name] for name in inputs},input_hashes={name:digest(raw) for name,raw in inputs.items()},
            qualification_receipt_ref=selected['qualification_receipt_ref'])
        if load_config(config_path)!=config:raise ValueError('Product configuration changed during Paper selection')
        with _open_paper_selection_owner(config.database_path) as writer:selection=writer.select(record)
    return dict(status='ORDINARY_PAPER_CONFIGURED',namespace='LOCAL_RESEARCH',config_hash=selection.config_hash,
        config_generation=selection.generation,workflow_authorized=selected['workflow_authorized'],
        release_kind='NATIVE_QUALIFIED',runtime='NOT_STARTED',provider_requests=0,credentials='NONE',capital='NONE',
        strategy_qualification='NOT_INFERRED',forward_qualification='NOT_ISSUED',financial_authority='NONE')


class OrdinarySelectedPaper:
    def __init__(self,config,selection,*,resolver,clock,observation_reader=None,implementation_hash=None):
        self.config,self.selection,self.clock=config,selection,clock
        record=selection.as_dict()
        # The protected selection is only a pending commitment in Control.
        # Admission must independently reconcile it to measured native facts.
        # The runtime factory injects its bounded verified installed subject.
        self.implementation_hash=record['simulator_profile']['implementation_hash'] if implementation_hash is None else implementation_hash
        self.owner=validate_operational_record(config,record,implementation_hash=self.implementation_hash)
        source=record.get('source_subject')
        if not isinstance(source,dict) or set(source)!=SOURCE_KEYS or source['schema_version']!='r7-local-paper-source-subject-v0.2':
            raise ValueError('Exact ordinary Paper source subject required')
        if resolver is None:raise ValueError('Actual accepted ordinary intake resolver required')
        self.source=source
        safe_component(source['submission_id'])
        if not isinstance(source['strategy'],dict) or set(source['strategy'])!={'strategy_id','strategy_version','content_hash'}:
            raise ValueError('Exact selected Paper strategy required')
        self.identity=StrategyIdentity(source['strategy']['strategy_id'],source['strategy']['strategy_version'])
        if (not isinstance(source['input_refs'],dict) or set(source['input_refs'])!=
                {'simulation_policy_ref','risk_policy_ref','promotion_policy_ref'}
                or not isinstance(source['input_hashes'],dict) or set(source['input_hashes'])!=set(source['input_refs'])):
            raise ValueError('Exact original selected Paper input commitments required')
        for ref in source['input_refs'].values():safe_relative(ref)
        _,package=resolver.package(source['submission_id']);self.snapshot=package.snapshot
        self.native=NativePaperReleaseReader(config,receipt_ref=source['qualification_receipt_ref'],
            selection_generation=selection.generation,observation_reader=observation_reader)
        authenticator=HumanAuthenticator(namespace='LOCAL_RESEARCH',reauth_seconds=300,verifier=lambda _:None,clock=clock)
        self.owners=PaperOwnerComposition(config,selection=self.owner,current_release=self.current,
            authenticator=authenticator,clock=clock,strategy_identity=self.identity,operational_generation=selection.generation,
            implementation_hash=self.implementation_hash)

    def current(self):
        try:
            # Full input, source, installed bytes and receipt verification runs
            # in the owned observer. This live path checks only bounded facts
            # and the original sealed temporal constraint; no full rehashing.
            if not assess_submission_validity(self.owner.as_dict()['submission_validity'],self.clock()).new_entry_allowed:raise ValueError()
            return self.native.current()
        except (ValueError,RuntimeError,OSError,KeyError,TypeError,CloudError) as error:
            raise EvidenceGateError('Current qualified native Paper selection/runtime evidence required') from error


def load_ordinary_paper_owners(config,*,clock,resolver,observation_reader=None,implementation_hash=None):
    if product_namespace(config)!='LOCAL_RESEARCH' or not config.database_path.is_file():return None
    if require_valid_restoration(config)['status']!='NOT_RESTORED':return None
    with open_paper_selections(config.database_path) as reader:selection=reader.current()
    if selection is None:return None
    return OrdinarySelectedPaper(config,selection,resolver=resolver,clock=clock,
        observation_reader=observation_reader,implementation_hash=implementation_hash)


def ordinary_paper_worker(config_path,*,maximum_ticks=None,expected_config_hash=None):
    """Bootstrap a qualified idle independent runtime, then discover E6 starts.

    Explicit keyless public reads run in an owned acquisition child. An absent
    market selection remains NOT_CONNECTED; software/financial gates still own
    every start and fill. No synthetic events or elapsed time are manufactured.
    """
    import json
    import sys
    from application.platform.shutdown import ManagedStop
    from .worker import PaperOwnerWorker
    if not getattr(sys,'frozen',False):raise ValueError('Qualified native ordinary Paper worker required')
    config_path=Path(config_path).absolute();config=load_config(config_path)
    from application.platform.supervision import config_hash
    if expected_config_hash is not None and config_hash(config)!=expected_config_hash:
        raise ValueError('Ordinary Paper child configuration changed before owner composition')
    if product_namespace(config)!='LOCAL_RESEARCH' or config.diagnostic_only or not config.paper_runtime_enabled:
        raise ValueError('Explicit ordinary Paper runtime profile required')
    with open_paper_selections(config.database_path) as reader:selection=reader.current()
    if selection is None:raise ValueError('Explicit protected ordinary Paper selection required')
    record=selection.as_dict()
    ref=record['source_subject']['qualification_receipt_ref']
    from .release_observation import check_native_once,OwnerReleaseObservation
    try:verified,_,_=check_native_once(config_path,ref)
    except ValueError:
        # Reconciliation is for accepted original E5/E6 work only. Its current
        # release reader continues denying new starts and fills on receipt loss.
        verified,_,_=check_native_once(config_path,ref,mode='management')
    installed=verified['facts']
    validate_operational_record(config,record,implementation_hash=installed['implementation_hash'])
    from contextlib import contextmanager
    from application.local_owners import LocalOwners
    @contextmanager
    def actual_service():
        local=LocalOwners(config,namespace='LOCAL_RESEARCH')
        with open_paper_selections(config.database_path) as ledger:
            if ledger.current()!=selection:raise ValueError('Paper selection changed during qualified bootstrap')
        with OwnerReleaseObservation(config,config_path,ref,supervisor=worker.supervisor,selection=selection) as observer:
            selected=load_ordinary_paper_owners(config,clock=local.clock,resolver=local.resolver,
                observation_reader=observer,implementation_hash=installed['implementation_hash'])
            if selected is None:raise ValueError('Actual ordinary Paper composition required')
            with selected.owners.service() as service:yield service
    worker=PaperOwnerWorker(config,actual_service,namespace='LOCAL_RESEARCH',config_path=config_path,feedback_on_quiescence=True)
    from contextlib import ExitStack
    from .public_market import load_market_profile
    from .public_feed import PublicMarketFeed
    from .public_acquisition import event_for
    from datetime import datetime,timezone
    market=dict(market_source='NOT_CONNECTED',provider_requests=0,provider_responses=0,request_accounting='COMPLETE',credentials='NONE',provider_mutation=0)
    with ManagedStop() as stop,worker,ExitStack() as acquisition:
        feed=None
        if load_market_profile(config) is not None:
            feed=acquisition.enter_context(PublicMarketFeed(config,config_path,worker.supervisor.identity['process_generation_id']))
        from application.platform.service_stop import observe_service_stop
        tick=0;market_rejections=0
        while not stop.requested:
            if observe_service_stop(worker.supervisor,stop):break
            worker.tick();tick+=1
            if feed is not None:
                subscriptions=worker.market_subscriptions();feed.update(subscriptions)
                result=feed.take()
                if result is not None:
                    for subscription in subscriptions:
                        try:
                            event=event_for(subscription,result,now=datetime.now(timezone.utc))
                            if event is not None:worker.submit_event(subscription.run_id,event)
                        except (ValueError,RuntimeError,TypeError,KeyError):market_rejections+=1
            if maximum_ticks is not None and tick>=maximum_ticks:break
            stop.wait(1)
        final=worker.snapshot()
    if feed is not None:market=feed.summary()
    print(json.dumps(dict(status='STOPPED',namespace='LOCAL_RESEARCH',mode='REAL_TIME',
        **market,market_event_rejections=market_rejections,process_generation=final['process_generation'],
        run_failures=final['run_failures'],financial_authority='NONE',
        capital='NONE',real_forward_qualification='NOT_ISSUED')))
    return 0 if not final['run_failures'] else 2
