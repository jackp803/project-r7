"""Read-only application restoration fence; restarting grants no authority."""
import json, re, uuid
from datetime import datetime
from application.datasets.catalog import read_local
from application.platform.private_files import require_private

KEYS = {'schema_version','restore_generation_id','restored_at','source_backup_id','source_backup_manifest_sha256',
    'product_instance_id','previous_config_hash','config_hash','database_count','scope','user_data_restore',
    'reconciliation','reauthorization','runtime_new_exposure','cloud','financial_authority','source_provenance'}


class RestorationError(ValueError):
    pass


def restoration_status(config):
    marker = config.local_data_root / 'restore-generation.json'
    profile = config.local_data_root / 'restored-product.json'
    progress = config.local_data_root / 'restore-in-progress.json'
    if not marker.exists() and not profile.exists() and not progress.exists():
        return dict(status='NOT_RESTORED', financial_authority='NONE')
    invalid = dict(status='INVALID_RESTORE_GENERATION', reconciliation='REQUIRED', reauthorization='REQUIRED',
        runtime_new_exposure='INHIBITED', financial_authority='NONE', reason_codes=['RESTORE_GENERATION_INVALID'])
    try:
        require_private(marker)
        require_private(profile)
        require_private(progress)
        from application.platform.supervision import config_hash
        from application.config import load_config, _unique_pairs
        from application.research.evidence import stamp
        value = json.loads(read_local(config.local_data_root,'restore-generation.json',65536), object_pairs_hook=_unique_pairs)
        pending = json.loads(read_local(config.local_data_root,'restore-in-progress.json',4096), object_pairs_hook=_unique_pairs)
        if (not isinstance(value,dict) or set(value) != KEYS or value['product_instance_id'] != config.product_instance_id
                or value['scope'] not in ('DATABASES_ONLY','PRODUCT_DATA')
                or value['schema_version'] != 'r7-private-'+('database' if value['scope']=='DATABASES_ONLY' else 'product-data')+'-restore-v0.2'
                or value['user_data_restore'] != ('PENDING' if value['scope']=='DATABASES_ONLY' else 'COMPLETE_SUPPORTED_LOCAL_PROFILE')
                or value['reconciliation'] != 'REQUIRED' or value['reauthorization'] != 'REQUIRED'
                or value['runtime_new_exposure'] != 'INHIBITED' or value['cloud'] != 'DISCONNECTED'
                or value['financial_authority'] != 'NONE' or not isinstance(value['source_provenance'],dict)
                or type(value['database_count']) is not int or not 1 <= value['database_count'] <= 8
                or config.cloud_root is not None or not config.diagnostic_only or config.paper_runtime_enabled):
            return invalid
        if pending != dict(schema_version='r7-private-restore-in-progress-v0.2',restore_generation_id=value['restore_generation_id'],
                product_instance_id=config.product_instance_id,previous_config_hash=value['previous_config_hash'],status='IN_PROGRESS'):
            return invalid
        for key in ('restore_generation_id','source_backup_id'):
            if str(uuid.UUID(value[key])) != value[key]:
                return invalid
        for key in ('source_backup_manifest_sha256','previous_config_hash','config_hash'):
            if not isinstance(value[key],str) or not re.fullmatch('sha256:[0-9a-f]{64}',value[key]):
                return invalid
        stamp(datetime.fromisoformat(value['restored_at'].replace('Z','+00:00')))
        if config_hash(config) != value['config_hash'] or config_hash(load_config(profile)) != value['config_hash']:
            return invalid
        return dict(status='RESTORED_INHIBITED', restore_generation_id=value['restore_generation_id'], scope=value['scope'],
            user_data_restore=value['user_data_restore'], reconciliation='REQUIRED', reauthorization='REQUIRED',
            runtime_new_exposure='INHIBITED', cloud='DISCONNECTED', financial_authority='NONE',
            reason_codes=['RESTORE_RECONCILIATION_AND_REAUTHORIZATION_REQUIRED'])
    except Exception:
        return invalid


def require_valid_restoration(config):
    status = restoration_status(config)
    if status['status'] == 'INVALID_RESTORE_GENERATION':
        raise RestorationError('RESTORE_GENERATION_INVALID')
    return status
