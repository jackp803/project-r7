"""Ordinary selected Paper identity; no strategy or financial default is installed."""
from pathlib import Path
import re
import sys
import json
from decimal import Decimal

from application.config import ProductConfig, product_namespace
from application.platform.distribution import verify_distribution
from application.platform.restoration import require_valid_restoration
from application.platform.runtime_identity import read_runtime_identity
from application.platform.supervision import config_hash
from registry.operational_authority import ReleaseBinding
from registry.product_assessment import canonical, digest
from risk.product_policy import parse_product_risk_policy
from storage.paper_selection import OperationalSelection,open_paper_selections
from storage.qualification import open_qualification_receipts
from strategy.v02.capabilities import _revision,build_capability_snapshot
from .owners import PaperOwnerSelection
from .policy import parse_simulation_policy
from .errors import NativePaperReleaseUnavailable


def simulator_profile(owner,*,implementation_hash=None):
    if not isinstance(owner, PaperOwnerSelection) or owner.namespace != 'LOCAL_RESEARCH':
        raise ValueError('Explicit ordinary Paper owner selection required')
    simulation = parse_simulation_policy(owner.as_dict()['simulation_policy'], namespace='LOCAL_RESEARCH')
    if implementation_hash is not None and (type(implementation_hash) is not str
            or not re.fullmatch('sha256:[0-9a-f]{64}',implementation_hash)):
        raise ValueError('Trusted measured simulator source commitment required')
    return dict(schema_version='r7-local-paper-simulator-v0.2',
        implementation_profile='r7-paper-engine-v0.2', implementation_hash=_revision() if implementation_hash is None else implementation_hash,
        simulation_policy_hash=simulation.policy_hash, account_scope='ISOLATED_PER_STRATEGY_RUN',
        funding_model='EXPLICIT_REGISTERED_PAPER_ZERO', partial_remainder_behavior='CANCEL_AFTER_FIRST_FILL',
        broker_kind='PAPER_ONLY', provider_requests=0, credentials='NONE', capital='NONE')


def operational_record(config, owner, *, account_ref,implementation_hash=None):
    if (not isinstance(config, ProductConfig) or product_namespace(config) != 'LOCAL_RESEARCH'
            or not isinstance(owner, PaperOwnerSelection) or owner.namespace != 'LOCAL_RESEARCH'):
        raise ValueError('Validated ordinary product configuration and explicit policies required')
    if not isinstance(account_ref, str) or not account_ref.strip() or len(account_ref) > 256:
        raise ValueError('Explicit bounded local simulator account reference required')
    owner = PaperOwnerSelection(**owner.as_dict())
    profile = simulator_profile(owner,implementation_hash=implementation_hash)
    envelope = dict(schema_version='r7-paper-operational-selection-v0.2',
        product_config_hash=config_hash(config), owner_selection_hash=owner.selection_hash,
        simulator_profile_hash=digest(canonical(profile)), account_ref=account_ref)
    return dict(envelope=envelope, owner=owner.as_dict(), simulator_profile=profile)


def _historical_owner(record,*,implementation_hash=None):
    """Validate the immutable selected body, retaining its original config hash.

    Only the protected ledger and original accepted release may supply this
    record. Current product configuration is checked separately for admission.
    """
    if not isinstance(record, dict) or set(record) not in (
            {'envelope','owner','simulator_profile'}, {'envelope','owner','simulator_profile','source_subject'}):
        raise ValueError('Complete canonical operational selection required')
    try:
        owner = PaperOwnerSelection(**record['owner'])
        envelope=record['envelope'];profile=simulator_profile(owner,implementation_hash=implementation_hash)
        if (set(envelope)!={'schema_version','product_config_hash','owner_selection_hash',
                'simulator_profile_hash','account_ref'}
                or envelope['schema_version']!='r7-paper-operational-selection-v0.2'
                or not isinstance(envelope['product_config_hash'],str)
                or not re.fullmatch('sha256:[0-9a-f]{64}',envelope['product_config_hash'])
                or envelope['owner_selection_hash']!=owner.selection_hash
                or envelope['simulator_profile_hash']!=digest(canonical(profile))
                or record['simulator_profile']!=profile
                or not isinstance(envelope['account_ref'],str)
                or not envelope['account_ref'].strip() or len(envelope['account_ref'])>256):
            raise ValueError()
        return owner
    except (ValueError, TypeError, KeyError):
        raise ValueError('Operational configuration/selection/simulator commitment changed') from None


def validate_operational_record(config, record,*,implementation_hash=None):
    owner=_historical_owner(record,implementation_hash=implementation_hash)
    expected=operational_record(config,owner,account_ref=record['envelope']['account_ref'],implementation_hash=implementation_hash)
    if any(record[key]!=value for key,value in expected.items()):
        raise ValueError('Current operational configuration/selection/simulator commitment changed')
    return owner


def _binding_from_current_facts(config, selection, measured, identity,*,implementation_hash=None,capability_hash=None):
    """Projection after software verification and actual read_runtime_identity.

    This private calculation accepts observations for focused tests. Production
    composition always acquires its own distribution and runtime observations.
    """
    if not isinstance(selection,OperationalSelection):
        raise ValueError('Actual protected ordinary selection required')
    expected_source=_revision() if implementation_hash is None else implementation_hash
    expected_capability=build_capability_snapshot().snapshot_hash if capability_hash is None else capability_hash
    if any(type(value) is not str or not re.fullmatch('sha256:[0-9a-f]{64}',value)
            for value in (expected_source,expected_capability)):
        raise ValueError('Trusted measured implementation/capability commitments required')
    owner=validate_operational_record(config,selection.as_dict(),implementation_hash=expected_source)
    record=selection.as_dict()
    if selection.config_hash != digest(canonical(record['envelope'])):
        raise ValueError('Protected operational envelope changed')
    if (measured.get('distribution_profile') != 'r7-native-distribution-v0.2'
            or measured.get('implementation_hash') != expected_source or identity.get('role') != 'runtime'
            or measured.get('capability_hash',expected_capability)!=expected_capability
            or identity.get('product_instance_id') != config.product_instance_id
            or identity.get('config_hash') != record['envelope']['product_config_hash']
            or any(identity.get(key) != measured.get(key) for key in
                ('executable_revision','implementation_hash','build_hash','distribution_profile'))):
        raise ValueError('Current exact independent native runtime required')
    selected=owner.as_dict()
    risk=parse_product_risk_policy(selected['risk_policy'],namespace='LOCAL_RESEARCH')
    return ReleaseBinding(namespace='LOCAL_RESEARCH',implementation_hash=measured['implementation_hash'],
        executable_revision=measured['executable_revision'],build_hash=measured['build_hash'],
        config_hash=selection.config_hash,config_generation=selection.generation,
        capability_hash=expected_capability,
        provider_profile_hash=record['envelope']['simulator_profile_hash'],provider_ref='LOCAL_PAPER_SIMULATOR_V0_2',
        account_ref=record['envelope']['account_ref'],risk_policy_hash=risk.policy_hash,
        risk_generation=selected['risk_policy']['generation'],runtime_generation=identity.get('generation'),
        release_kind='NATIVE_QUALIFIED')


class NativePaperReleaseReader:
    """Read-only native admission; never launches a process or allocates state."""
    def __init__(self,config,*,receipt_ref,selection_generation=None,observation_reader=None):
        if (not isinstance(config,ProductConfig) or product_namespace(config) != 'LOCAL_RESEARCH'
                or not isinstance(receipt_ref,str) or not re.fullmatch('qualification-[0-9a-f]{64}',receipt_ref)
                or selection_generation is not None and
                    (type(selection_generation) is not int or not 1<=selection_generation<=2147483647)):
            raise ValueError('Exact local owning receipt and ordinary product configuration required')
        self.config,self.receipt_ref,self.selection_generation=config,receipt_ref,selection_generation
        if observation_reader is not None and not callable(getattr(observation_reader,'current',None)):
            raise ValueError('Trusted bounded native observation reader required')
        self.observation_reader=observation_reader

    def _installed_facts(self):
        # Native-only initial convention. Deny source before opening any store.
        if not getattr(sys,'frozen',False):
            raise ValueError('QUALIFIED_NATIVE_PAPER_INSTALL_REQUIRED')
        from .inventory import current_target
        facts=verify_distribution(Path(sys.executable).resolve().parent)
        facts.update(platform_id=current_target(),capability_hash=build_capability_snapshot().snapshot_hash)
        if facts['implementation_hash']!=_revision():
            raise ValueError('CURRENT_NATIVE_IMPLEMENTATION_REQUIRED')
        return facts

    def software_eligible(self):
        facts=self._installed_facts()
        if require_valid_restoration(self.config)['status'] != 'NOT_RESTORED':
            raise ValueError('RESTORED_PAPER_ADMISSION_INHIBITED')
        if not self.config.database_path.is_file():
            raise NativePaperReleaseUnavailable('OWNING_SOFTWARE_QUALIFICATION_STORE_MISSING')
        from .inventory import fixed_profile
        from .qualification import validate_qualified_receipt
        with open_qualification_receipts(self.config.database_path,namespace='LOCAL_RESEARCH') as reader:
            receipt=reader.get(self.receipt_ref)
        if receipt is None:
            raise NativePaperReleaseUnavailable('OWNING_SOFTWARE_QUALIFICATION_RECEIPT_MISSING')
        validate_qualified_receipt(receipt,fixed_profile(facts['platform_id']),
            artifact_root=self.config.local_data_root/'qualification'/receipt.execution_id,measured=facts)
        return facts

    def management_eligible(self):
        """Exact installed original owner recovery, never idle/new-entry admission.

        A missing software receipt cannot erase an existing E5 obligation. The
        actual unchanged native build and accepted original E6 bindings remain
        mandatory; tampered installs or restore reauthorization are not bypassed.
        """
        facts=self._installed_facts()
        if (self.config.diagnostic_only or not self.config.paper_runtime_enabled
                or require_valid_restoration(self.config)['status']!='NOT_RESTORED'):
            raise ValueError('EXPLICIT_NON_RESTORED_ORIGINAL_OWNER_RECOVERY_REQUIRED')
        from storage import open_sqlite_platform
        from storage.paper_process import open_paper_process_journal
        recoverable=[]
        with open_sqlite_platform(self.config.database_path,research_namespace='LOCAL_RESEARCH',require_existing=True) as registry, \
                open_paper_process_journal(self.config.database_path,require_existing=True) as process, \
                open_paper_selections(self.config.database_path) as selections:
            proofs=registry.list_accepted_paper_starts(limit=200)
            if len(proofs)==200:raise ValueError('ORIGINAL_OWNER_RECOVERY_INVENTORY_LIMIT')
            for proof in proofs:
                run=json.loads(proof.payload_json)['run_id'];observed=process.recover(run)
                runtime=observed.state['runtime'];position=runtime['position']
                if not (position is not None and Decimal(position['actual_quantity'])>0 or
                        position is None and runtime['entry_request'] is not None):continue
                original=ReleaseBinding(**json.loads(proof.release_json))
                if (original.namespace!='LOCAL_RESEARCH' or original.release_kind!='NATIVE_QUALIFIED'
                        or any(getattr(original,key)!=facts[key] for key in
                            ('implementation_hash','executable_revision','build_hash','capability_hash'))):
                    raise ValueError('EXACT_ORIGINAL_NATIVE_OWNER_SUBJECT_REQUIRED')
                selection=selections.get(original.config_generation)
                if selection is None or selection.config_hash!=original.config_hash:
                    raise ValueError('ORIGINAL_PROTECTED_SELECTION_REQUIRED')
                record=selection.as_dict();owner=_historical_owner(record,implementation_hash=original.implementation_hash)
                risk=parse_product_risk_policy(owner.as_dict()['risk_policy'],namespace='LOCAL_RESEARCH')
                if (record['envelope']['simulator_profile_hash']!=original.provider_profile_hash
                        or record['envelope']['account_ref']!=original.account_ref
                        or risk.policy_hash!=original.risk_policy_hash
                        or owner.as_dict()['risk_policy']['generation']!=original.risk_generation
                        or observed.binding['risk_policy_hash']!=original.risk_policy_hash
                        or observed.binding['implementation_hash']!=original.implementation_hash):
                    raise ValueError('ORIGINAL_EXACT_E5_SIMULATOR_BINDING_REQUIRED')
                recoverable.append(run)
        if not recoverable:raise ValueError('NO_EXISTING_OWNER_RECOVERY_OBLIGATION')
        return dict(status='ENTRY_INHIBITED_EXISTING_OWNER_RECOVERY',runs=len(recoverable),
            financial_authority='NONE',new_entry='INHIBITED',restore_reauthorization='NOT_GRANTED')

    def current(self):
        if not getattr(sys,'frozen',False):raise ValueError('QUALIFIED_NATIVE_PAPER_INSTALL_REQUIRED')
        if require_valid_restoration(self.config)['status']!='NOT_RESTORED':
            raise ValueError('RESTORED_PAPER_ADMISSION_INHIBITED')
        if self.config.diagnostic_only or not self.config.paper_runtime_enabled:
            raise ValueError('EXPLICIT_ORDINARY_PAPER_RUNTIME_SELECTION_REQUIRED')
        with open_paper_selections(self.config.database_path) as reader:
            selection=reader.current()
        if selection is None or self.selection_generation is not None and selection.generation != self.selection_generation:
            raise ValueError('CURRENT_PROTECTED_PAPER_SELECTION_REQUIRED')
        from .release_observation import ControlReleaseObservation
        observer=self.observation_reader or ControlReleaseObservation(self.config,self.receipt_ref)
        facts=dict(observer.current(selection))
        snapshot=read_runtime_identity(self.config)
        return _binding_from_current_facts(self.config,selection,facts,dict(snapshot.identity),
            implementation_hash=facts['implementation_hash'],capability_hash=facts['capability_hash'])
