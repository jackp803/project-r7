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
    config=load_config(config_path)
    selected=read_operator_profile(config,selection_profile)
    if product_namespace(config)!='LOCAL_RESEARCH' or config.diagnostic_only or not config.paper_runtime_enabled:
        raise ValueError('Explicit ordinary Paper runtime profile required')
    from application.entrypoints import _outside_installation
    _outside_installation(config.local_data_root)
    with ExitStack() as stack:
        for role in ('control','research','runtime','cloud'):
            stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
        if load_config(config_path)!=config or require_valid_restoration(config)['status']!='NOT_RESTORED':
            raise ValueError('Unchanged non-restored ordinary profile required')
        # Software eligibility precedes owner initialization. No idle runtime
        # identity is required yet; its generation is observed after bootstrap.
        NativePaperReleaseReader(config,receipt_ref=selected['qualification_receipt_ref']).software_eligible()
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
        record=operational_record(config,owner,account_ref=selected['account_ref'])
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
    def __init__(self,config,selection,*,resolver,clock):
        self.config,self.selection,self.clock=config,selection,clock
        record=selection.as_dict();self.owner=validate_operational_record(config,record)
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
            selection_generation=selection.generation)
        authenticator=HumanAuthenticator(namespace='LOCAL_RESEARCH',reauth_seconds=300,verifier=lambda _:None,clock=clock)
        self.owners=PaperOwnerComposition(config,selection=self.owner,current_release=self.current,
            authenticator=authenticator,clock=clock,strategy_identity=self.identity,operational_generation=selection.generation)

    def current(self):
        try:
            selected=self.owner.as_dict();observed=dict(selected)
            for field,ref in self.source['input_refs'].items():
                raw=read_local(self.config.local_data_root,ref,65536)
                if digest(raw)!=self.source['input_hashes'][field]:raise ValueError()
                observed[field.removesuffix('_ref')]=decode(raw)
            if PaperOwnerSelection(**observed).selection_hash!=self.owner.selection_hash:raise ValueError()
            package=validate_package(self.snapshot);manifest=package.manifest.raw
            subject=dict(strategy_id=manifest['strategy_id'],strategy_version=manifest['strategy_version'],
                content_hash=manifest['strategy_content_hash'])
            validity={key:manifest[key] for key in ('intent_class','validity')}
            if (subject!=self.source['strategy'] or package.manifest.manifest_hash!=self.source['manifest_hash']
                    or manifest.get('capability_snapshot_hash')!=build_capability_snapshot().snapshot_hash
                    or selected['submission_validity']!=validity or not assess_submission_validity(validity,self.clock()).new_entry_allowed):
                raise ValueError()
            return self.native.current()
        except (ValueError,RuntimeError,OSError,KeyError,TypeError,CloudError) as error:
            raise EvidenceGateError('Current qualified native Paper selection/runtime evidence required') from error


def load_ordinary_paper_owners(config,*,clock,resolver):
    if product_namespace(config)!='LOCAL_RESEARCH' or not config.database_path.is_file():return None
    if require_valid_restoration(config)['status']!='NOT_RESTORED':return None
    with open_paper_selections(config.database_path) as reader:selection=reader.current()
    if selection is None:return None
    return OrdinarySelectedPaper(config,selection,resolver=resolver,clock=clock)


def ordinary_paper_worker(config_path,*,maximum_ticks=None):
    """Bootstrap a qualified idle independent runtime, then discover E6 starts.

    Unconfigured public acquisition remains NOT_CONNECTED. No synthetic events,
    elapsed time, real data access or workflow authorization are manufactured.
    """
    import json
    import sys
    from application.platform.shutdown import ManagedStop
    from .worker import PaperOwnerWorker
    if not getattr(sys,'frozen',False):raise ValueError('Qualified native ordinary Paper worker required')
    config=load_config(config_path)
    if product_namespace(config)!='LOCAL_RESEARCH' or config.diagnostic_only or not config.paper_runtime_enabled:
        raise ValueError('Explicit ordinary Paper runtime profile required')
    with open_paper_selections(config.database_path) as reader:selection=reader.current()
    if selection is None:raise ValueError('Explicit protected ordinary Paper selection required')
    record=selection.as_dict();validate_operational_record(config,record)
    ref=record['source_subject']['qualification_receipt_ref']
    admission=NativePaperReleaseReader(config,receipt_ref=ref)
    try:admission.software_eligible()
    except ValueError:
        # Reconciliation is for accepted original E5/E6 work only. Its current
        # release reader continues denying new starts and fills on receipt loss.
        admission.management_eligible()
    from contextlib import contextmanager
    from application.local_owners import LocalOwners
    @contextmanager
    def actual_service():
        local=LocalOwners(config,namespace='LOCAL_RESEARCH')
        selected=load_ordinary_paper_owners(config,clock=local.clock,resolver=local.resolver)
        if selected is None:raise ValueError('Actual ordinary Paper composition required')
        with selected.owners.service() as service:yield service
    with ManagedStop() as stop,PaperOwnerWorker(config,actual_service,namespace='LOCAL_RESEARCH',
            config_path=config_path,feedback_on_quiescence=True) as worker:
        from application.platform.service_stop import observe_service_stop
        tick=0
        while not stop.requested:
            if observe_service_stop(worker.supervisor,stop):break
            worker.tick();tick+=1
            if maximum_ticks is not None and tick>=maximum_ticks:break
            stop.wait(1)
        final=worker.snapshot()
    print(json.dumps(dict(status='STOPPED',namespace='LOCAL_RESEARCH',mode='REAL_TIME',
        market_source='NOT_CONNECTED',process_generation=final['process_generation'],
        run_failures=final['run_failures'],financial_authority='NONE',provider_requests=0,credentials='NONE',
        capital='NONE',real_forward_qualification='NOT_ISSUED')))
    return 0 if not final['run_failures'] else 2
