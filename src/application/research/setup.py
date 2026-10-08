"""Stopped-owner local research selection; no policy defaults or financial grant."""
from contextlib import ExitStack
import os
from pathlib import Path

from application.config import load_config
from application.datasets.catalog import canonical, decode, digest, read_local
from application.local_owners import validate_owner_selections
from application.platform.restoration import require_valid_restoration
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.cloud.safe_files import write_immutable, read_bounded, _windows_read, _posix_read
from application.cloud.protocol import CloudError


def configure_research(config_path, selection_profile):
    """Install one exact local selection profile, preserving existing selection.

    Only shape, local reference availability and namespaces are checked here.
    Policy compatibility, dataset/OOS execution and candidate authority remain
    actual research-owner checks. This command does not initialize a database.
    """
    config=load_config(config_path)
    profile=Path(selection_profile)
    if not profile.is_absolute() or '..' in profile.parts or str(profile).startswith(('\\\\','//')):
        raise ValueError('Absolute local operator selection profile required')
    try: canonical_profile=profile.resolve(strict=True)
    except OSError: raise ValueError('Operator selection profile unavailable') from None
    if config.cloud_root is not None and canonical_profile.is_relative_to(config.cloud_root):
        raise ValueError('Research selections require an operator local profile outside cloud staging')
    # Operator filenames may contain spaces/Unicode; package logical names have
    # a different, stricter grammar. Both paths still pin opened ancestors and
    # reject links/reparse points through the existing bounded native reader.
    try: profile_bytes=(_windows_read if os.name=='nt' else _posix_read)(profile,65536,require_single_link=True)
    except CloudError as error: raise ValueError('Operator selection profile unavailable') from error
    selected=validate_owner_selections(decode(profile_bytes))
    if selected['cloud_root_id'] is not None and config.cloud_root is None:
        raise ValueError('Explicit cloud staging root required')
    for policy in selected['research_policies'].values():
        for key, reference in policy.items():
            if not key.endswith('_ref'): continue
            value=decode(read_local(config.local_data_root,reference,262144 if key=='robustness_policy_ref' else 65536))
            if not isinstance(value,dict) or value.get('namespace')!='LOCAL_RESEARCH':
                raise ValueError('Fresh same-namespace local research inputs required')
    if selected['cloud_root_id'] is not None:
        marker=decode(read_bounded(config.cloud_root,'.r7-root.json',4096))
        if marker != {'root_id':selected['cloud_root_id']}:
            raise ValueError('Explicit local staging root identity required')
    raw=canonical(selected).encode('utf-8')
    with ExitStack() as stack:
        for role in ('control','research','runtime','cloud'):
            stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
        if require_valid_restoration(config)['status']!='NOT_RESTORED':
            raise ValueError('Restored product data requires separate reauthorization')
        destination=config.local_data_root/'owner-selections.json'
        existing=destination.exists()
        if existing:
            stored=read_local(config.local_data_root,destination.name,65536)
            if canonical(decode(stored)).encode('utf-8')!=raw:
                raise ValueError('Existing owner selection must be preserved')
        else:
            try: write_immutable(config.local_data_root,destination.name,raw)
            except CloudError as error:
                raise ValueError('Owner selection could not be published') from error
    return dict(status='ALREADY_CONFIGURED' if existing else 'RESEARCH_CONFIGURED',
        namespace='LOCAL_RESEARCH',selection_hash=digest(raw),policy_count=len(selected['research_policies']),
        validation_scope='SELECTION_SHAPE_LOCAL_REFERENCES_AND_NAMESPACE',
        cloud='NOT_CONNECTED' if selected['cloud_root_id'] is None else 'LOCAL_STAGING_SELECTED',
        research='NOT_STARTED',paper='NOT_STARTED',live='NOT_STARTED',provider_requests=0,credentials='NONE',capital='NONE')
