"""Frozen server-selected research request from actual sealed accepted intake."""
import json
from pathlib import Path

from application.cloud.manifest import parse_manifest, validate_package, safe_component, safe_relative, byte_hash
from application.cloud.protocol import PackageSnapshot, CloudError
from application.cloud.safe_files import read_bounded
from application.datasets.catalog import read_local, canonical, digest
from application.research.queue import ResearchQueueError
from registry import StrategyIdentity
from strategy.v02.capabilities import build_capability_snapshot


def validate_research_selections(policies):
    """Validate and freeze selection shape without opening owner stores."""
    result = json.loads(canonical(policies))
    required = {'dataset_ref', 'split_policy_ref', 'cost_policy_ref', 'research_policy_ref', 'robustness_policy_ref',
                    'risk_policy_ref', 'family_id', 'seed', 'requested_dataset_profile', 'requested_validation_profile', 'requested_robustness_profile'}
    if not isinstance(result, dict) or len(result) > 128: raise ValueError('Bounded local policy selections required')
    for policy_id, selected in result.items():
        safe_component(policy_id)
        if not isinstance(selected, dict) or set(selected) != required: raise ValueError('Complete explicit local research selection required')
        for key in required:
            if key.endswith('_ref'): safe_relative(selected[key])
            elif key != 'seed': safe_component(selected[key])
        if type(selected['seed']) is not int or not 0 <= selected['seed'] < 2**64: raise ValueError('Explicit bounded seed required')
    return result


class ResearchRequestResolver:
    def __init__(self, local_root, *, snapshot_root, intake_factory, registry_factory, policies):
        self.root, self.snapshots = Path(local_root).absolute(), Path(snapshot_root).absolute()
        if not self.snapshots.is_relative_to(self.root) or not callable(intake_factory) or not callable(registry_factory):
            raise ValueError('Trusted local sealed intake composition required')
        self.intake_factory, self.registry_factory = intake_factory, registry_factory
        self.policies = validate_research_selections(policies)

    def _accepted_package(self, submission_id):
        safe_component(submission_id)
        with self.intake_factory() as intake:
            submission = intake.get_submission(submission_id)
            receipt = intake.accepted_receipt(submission_id)
        if submission is None or receipt is None: raise ResearchQueueError('VERIFIED_INTAKE_REQUIRED')
        snapshot_root = self.snapshots/(submission_id+'-'+submission.manifest_hash[7:])
        manifest = parse_manifest(read_bounded(snapshot_root, 'manifest.json', 65536))
        if manifest.manifest_hash != submission.manifest_hash: raise ResearchQueueError('SEALED_SUBMISSION_IDENTITY_CONFLICT')
        verified = validate_package(PackageSnapshot(snapshot_root, manifest.manifest_hash,
            {spec.role:snapshot_root/spec.relative_path for spec in manifest.payloads}))
        with self.registry_factory() as e6:
            record = e6.get_strategy(StrategyIdentity(manifest.strategy_id, manifest.strategy_version))
        if record.content_hash != manifest.strategy_content_hash or receipt['strategy_content_hash'] != record.content_hash:
            raise ResearchQueueError('REGISTERED_SUBJECT_IDENTITY_CONFLICT')
        return submission,verified

    def manifest_view(self,submission_id):
        # Immutable author context is readable after a code update. This is no
        # compatibility/admission verdict; executable package() checks currentness.
        _,verified=self._accepted_package(submission_id)
        return json.loads(canonical(verified.manifest.raw))

    def package(self,submission_id):
        submission,verified=self._accepted_package(submission_id)
        manifest=verified.manifest
        if manifest.schema_version.endswith('v0.2') and manifest.raw['capability_snapshot_hash'] != build_capability_snapshot().snapshot_hash:
            raise ResearchQueueError('CAPABILITY_REQUALIFICATION_REQUIRED')
        return submission, verified

    def resolve(self, submission_id, policy_id):
        safe_component(policy_id)
        selected = self.policies.get(policy_id)
        if selected is None: raise ResearchQueueError('RESEARCH_POLICY_NOT_CONFIGURED')
        submission, package = self.package(submission_id)
        for field in ('requested_dataset_profile', 'requested_validation_profile', 'requested_robustness_profile'):
            if package.manifest.raw[field] != selected[field]: raise ResearchQueueError('REQUESTED_PROFILE_SELECTION_MISMATCH')
        arguments = {key:value for key,value in selected.items() if not key.startswith('requested_')}
        arguments.update(submission_id=submission_id, definition=json.loads(package.strategy.canonical_json))
        hashes = {key:byte_hash(read_local(self.root, value, 262144 if key=='robustness_policy_ref' else 65536))
                  for key,value in selected.items() if key.endswith('_ref')}
        selection = dict(policy_id=policy_id, selected=selected, file_hashes=hashes, manifest_hash=package.manifest.manifest_hash)
        return dict(submission_revision=submission.revision, arguments=arguments, selection_hash=digest(canonical(selection).encode()))

    def policy_views(self):
        return [dict(policy_id=key, status='SELECTED_LOCAL', policy_hash=digest(canonical(value).encode()),
                     requested_dataset_profile=value['requested_dataset_profile'], requested_validation_profile=value['requested_validation_profile'],
                     requested_robustness_profile=value['requested_robustness_profile']) for key,value in sorted(self.policies.items())]

    def dataset_views(self):
        from application.datasets.catalog import DatasetCatalog
        catalog=DatasetCatalog(self.root); rows=[]; seen=set()
        for policy in self.policies.values():
            if policy['dataset_ref'] in seen: continue
            seen.add(policy['dataset_ref'])
            manifest=catalog.load(policy['dataset_ref']); data=manifest.as_dict()
            rows.append(dict(profile_id=policy['requested_dataset_profile'],dataset_id=data['dataset_id'],dataset_version=data['dataset_version'],
                namespace=data['namespace'],symbol=data['symbol'],information_cutoff=data['information_cutoff'],
                manifest_hash=manifest.manifest_hash,verification_scope='MANIFEST_ONLY',
                timeframes=[row['timeframe'] for row in data['candles']],funding_mode=data['funding']['mode']))
        return rows
