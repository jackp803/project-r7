"""Normal explicit FIXTURE owner selection; current facts never issue qualification.

Ordinary release producer/mapping remains separate. The frozen selection pins a
synthetic acceptance subject and denies every financial human operation.
"""
from contextlib import ExitStack
import os
from pathlib import Path

from application.config import load_config, product_namespace
from application.datasets.catalog import canonical, decode, digest, read_local
from application.cloud.manifest import safe_component, safe_relative, validate_package
from application.cloud.protocol import CloudError
from application.cloud.safe_files import _windows_read, _posix_read, write_immutable
from application.platform.restoration import require_valid_restoration
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.platform.supervision import config_hash
from application.research.evidence import capture_provenance
from application.research.product_assessment import require_promotable_provenance
from application.research.selection import ResearchRequestResolver
from application.research.queue import ResearchQueueError
from registry import EvidenceGateError, StrategyIdentity
from registry.operational_authority import HumanAuthenticator, ReleaseBinding
from risk.product_policy import parse_product_risk_policy
from strategy.v02.capabilities import build_capability_snapshot
from .owners import PaperOwnerSelection, PaperOwnerComposition

INPUT_SCHEMA = 'r7-fixture-paper-inputs-v0.2'
SELECTION_SCHEMA = 'r7-fixture-paper-owner-v0.2'
SELECTION_FILE = 'paper-owner-selections.json'
INPUT_KEYS = {'schema_version','submission_id','simulation_policy_ref','risk_policy_ref','promotion_policy_ref','paper_policy_ref'}
RECORD_KEYS = {'schema_version','owner','release','submission_id','manifest_hash','strategy','input_refs','input_hashes'}


def _operator_profile(config, selection_profile):
    path = Path(selection_profile)
    if not path.is_absolute() or '..' in path.parts or str(path).startswith(('\\\\','//')):
        raise ValueError('Absolute local operator PAPER selection profile required')
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        raise ValueError('Local operator PAPER selection unavailable') from None
    if config.cloud_root is not None and resolved.is_relative_to(config.cloud_root):
        raise ValueError('PAPER selections must be outside cloud staging')
    try:
        raw = (_windows_read if os.name=='nt' else _posix_read)(path,65536,require_single_link=True)
    except CloudError:
        raise ValueError('Local operator PAPER selection unavailable') from None
    value = decode(raw)
    if not isinstance(value,dict) or set(value)!=INPUT_KEYS or value['schema_version']!=INPUT_SCHEMA:
        raise ValueError('Exact local FIXTURE PAPER input selection required')
    safe_component(value['submission_id'])
    safe_component(value['paper_policy_ref'])
    for name in ('simulation_policy_ref','risk_policy_ref','promotion_policy_ref'):
        safe_relative(value[name])
    return value


def _release(config, owner):
    if product_namespace(config)!='FIXTURE':
        raise EvidenceGateError('FIXTURE release cannot qualify ordinary Paper')
    facts = capture_provenance()
    # The existing producer enforces real CLEAN source or exact verified native
    # inventory. No caller PASS/status is accepted, including in FIXTURE mode.
    require_promotable_provenance(facts)
    selected = owner.as_dict()
    risk = parse_product_risk_policy(selected['risk_policy'],namespace='FIXTURE')
    return ReleaseBinding(namespace='FIXTURE',implementation_hash=facts['implementation_hash'],
        executable_revision=facts['executable_revision'],build_hash=facts.get('build_hash') or digest(canonical(facts).encode('utf-8')),
        config_hash=digest(canonical(dict(product_config_hash=config_hash(config),paper_selection_hash=owner.selection_hash)).encode('utf-8')),
        config_generation=1,capability_hash=build_capability_snapshot().snapshot_hash,
        provider_profile_hash=digest(canonical(selected['simulation_policy']).encode('utf-8')),provider_ref='FIXTURE_PAPER_SIMULATOR',
        account_ref='FIXTURE_ISOLATED_ACCOUNT',risk_policy_hash=risk.policy_hash,
        risk_generation=selected['risk_policy']['generation'],runtime_generation=1,release_kind='FIXTURE')


class FixtureReleaseReader:
    def __init__(self, config, record, raw, resolver):
        if not isinstance(record,dict) or set(record)!=RECORD_KEYS or record['schema_version']!=SELECTION_SCHEMA:
            raise ValueError('Exact isolated FIXTURE PAPER owner subject required')
        self.config, self.raw_hash = config, digest(raw)
        if not isinstance(resolver,ResearchRequestResolver):
            raise ValueError('Actual accepted intake resolver required for FIXTURE PAPER')
        self.resolver = resolver
        safe_component(record['submission_id'])
        self.submission_id,self.manifest_hash = record['submission_id'],record['manifest_hash']
        self.strategy = record['strategy']
        if not isinstance(self.strategy,dict) or set(self.strategy)!={'strategy_id','strategy_version','content_hash'}:
            raise ValueError('Exact selected strategy subject required')
        self.identity = StrategyIdentity(self.strategy['strategy_id'],self.strategy['strategy_version'])
        self.owner = PaperOwnerSelection(**record['owner'])
        self.release = ReleaseBinding(**record['release'])
        if self.owner.namespace!='FIXTURE' or self.release.namespace!='FIXTURE' or not self.owner.as_dict()['workflow_authorized']:
            raise ValueError('Explicit isolated FIXTURE PAPER owner selection required')
        if (not isinstance(record['input_refs'],dict) or set(record['input_refs'])!=
                {'simulation_policy_ref','risk_policy_ref','promotion_policy_ref'} or
                not isinstance(record['input_hashes'],dict) or set(record['input_hashes'])!=set(record['input_refs'])):
            raise ValueError('Exact selected PAPER input commitments required')
        self.input_refs, self.input_hashes = dict(record['input_refs']), dict(record['input_hashes'])
        for reference in self.input_refs.values():
            safe_relative(reference)
        try:
            _, accepted = self.resolver.package(self.submission_id)
        except (ResearchQueueError,CloudError) as error:
            raise EvidenceGateError('Actual selected sealed PAPER submission required') from error
        # Resolve the accepted intake/E6 subject before an E6 write transaction.
        # Inside current(), revalidate these sealed bytes without opening another
        # registry writer. Restart always resolves the actual accepted subject.
        self.snapshot = accepted.snapshot
        self.current()

    def current(self):
        if (product_namespace(self.config)!='FIXTURE' or
                require_valid_restoration(self.config)['status']!='NOT_RESTORED' or
                digest(read_local(self.config.local_data_root,SELECTION_FILE,65536))!=self.raw_hash):
            raise EvidenceGateError('FIXTURE PAPER owner subject changed or restored')
        selected = self.owner.as_dict()
        observed = dict(selected)
        for field, reference in self.input_refs.items():
            raw = read_local(self.config.local_data_root,reference,65536)
            if digest(raw)!=self.input_hashes[field]:
                raise EvidenceGateError('Selected FIXTURE PAPER input changed')
            observed[field.removesuffix('_ref')] = decode(raw)
        if PaperOwnerSelection(**observed).selection_hash!=self.owner.selection_hash:
            raise EvidenceGateError('PAPER owner policy differs from actual selected input')
        try:
            package = validate_package(self.snapshot)
        except CloudError as error:
            raise EvidenceGateError('Actual selected sealed PAPER submission required') from error
        manifest = package.manifest.raw
        from application.fixtures.temporal import read_temporal,policy_ref
        temporal=read_temporal(self.config,package)
        if temporal is not None and selected['paper_policy_ref']!=policy_ref(temporal):
            raise EvidenceGateError('Sealed fixture timing differs from original Paper policy binding')
        self.temporal=temporal
        from application.fixtures.faults import read_case,require_selection
        self.paper_case=read_case(self.config,package)
        require_selection(self.paper_case,selected)
        subject = dict(strategy_id=manifest['strategy_id'],strategy_version=manifest['strategy_version'],
            content_hash=manifest['strategy_content_hash'])
        if (package.manifest.manifest_hash!=self.manifest_hash or subject!=self.strategy or
                manifest.get('capability_snapshot_hash')!=build_capability_snapshot().snapshot_hash or
                selected['submission_validity']!={key:manifest[key] for key in ('intent_class','validity')}):
            raise EvidenceGateError('Selected PAPER strategy/manifest/validity changed')
        if _release(self.config,self.owner)!=self.release:
            raise EvidenceGateError('Current FIXTURE source/build/configuration changed')
        return self.release


def load_fixture_paper_owners(config, *, clock, resolver):
    if product_namespace(config)!='FIXTURE' or require_valid_restoration(config)['status']!='NOT_RESTORED':
        return None
    if not (config.local_data_root/SELECTION_FILE).exists():
        return None
    raw = read_local(config.local_data_root,SELECTION_FILE,65536)
    reader = FixtureReleaseReader(config,decode(raw),raw,resolver)
    # This authenticator always refuses approval/deployment. Local UI login
    # alone can select permitted fixture PaperStart, never financial authority.
    authenticator = HumanAuthenticator(namespace='FIXTURE',reauth_seconds=300,verifier=lambda _:None,clock=clock)
    owners = PaperOwnerComposition(config,selection=reader.owner,current_release=reader.current,
        authenticator=authenticator,clock=clock,strategy_identity=reader.identity)
    owners.fixture_temporal=reader.temporal
    owners.fixture_paper_case=reader.paper_case
    return owners


def configure_paper(config_path, selection_profile):
    config = load_config(config_path)
    if product_namespace(config)!='FIXTURE':
        from .ordinary_setup import configure_ordinary_paper
        return configure_ordinary_paper(config_path,selection_profile)
    from application.entrypoints import _outside_installation
    _outside_installation(config.local_data_root)
    with ExitStack() as stack:
        for role in ('control','research','runtime','cloud'):
            stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
        if load_config(config_path)!=config or require_valid_restoration(config)['status']!='NOT_RESTORED':
            raise ValueError('Unchanged non-restored FIXTURE profile required')
        selected = _operator_profile(config,selection_profile)
        inputs = {name:read_local(config.local_data_root,selected[name],65536)
            for name in ('simulation_policy_ref','risk_policy_ref','promotion_policy_ref')}
        from application.local_owners import LocalOwners
        local = LocalOwners(config,namespace='FIXTURE')
        if local.resolver is None:
            raise ValueError('Actual accepted strategy intake and local research selection required')
        _, package = local.resolver.package(selected['submission_id'])
        manifest = package.manifest.raw
        from application.fixtures.temporal import read_temporal,policy_ref
        temporal=read_temporal(config,package)
        if temporal is not None and selected['paper_policy_ref']!=policy_ref(temporal):
            raise ValueError('Sealed temporal case requires its exact fixture Paper policy reference')
        owner = PaperOwnerSelection(namespace='FIXTURE',simulation_policy=decode(inputs['simulation_policy_ref']),
            risk_policy=decode(inputs['risk_policy_ref']),promotion_policy=decode(inputs['promotion_policy_ref']),
            paper_policy_ref=selected['paper_policy_ref'],submission_validity={key:manifest[key] for key in ('intent_class','validity')},
            actor='r7-fixture-paper-owner',workflow_authorized=True)
        from application.fixtures.faults import read_case,require_selection
        require_selection(read_case(config,package),owner.as_dict())
        release = _release(config,owner)
        record = dict(schema_version=SELECTION_SCHEMA,owner=owner.as_dict(),release=release.as_dict(),
            submission_id=selected['submission_id'],manifest_hash=package.manifest.manifest_hash,
            strategy=dict(strategy_id=manifest['strategy_id'],strategy_version=manifest['strategy_version'],
                content_hash=manifest['strategy_content_hash']),
            input_refs={name:selected[name] for name in inputs},input_hashes={name:digest(raw) for name,raw in inputs.items()})
        raw = canonical(record).encode('utf-8')
        destination = config.local_data_root/SELECTION_FILE
        exists = destination.exists()
        if exists:
            if read_local(config.local_data_root,SELECTION_FILE,65536)!=raw:
                raise ValueError('Existing FIXTURE PAPER subject must be preserved')
        else:
            if load_config(config_path)!=config:
                raise ValueError('Product configuration changed during PAPER selection')
            write_immutable(config.local_data_root,SELECTION_FILE,raw)
    return dict(status='ALREADY_CONFIGURED' if exists else 'FIXTURE_PAPER_CONFIGURED',namespace='FIXTURE',
        selection_hash=digest(raw),release_kind='FIXTURE',qualification='NOT_ISSUED',
        financial_authority='NONE',runtime='NOT_STARTED',provider_requests=0,credentials='NONE',capital='NONE')
