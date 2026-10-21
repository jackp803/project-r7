"""Fenced replay of complete archive transactions and immutable crash tails.

This never repairs a corrupt committed prefix, deletes evidence, invents request
counts, clears unknown accounting, or grants a new financial/runtime permission.
"""
from copy import deepcopy
import hashlib
import os
import re
import struct
import uuid

from application.datasets.catalog import canonical,decode,digest,read_local
from application.platform.private_files import require_private,write_private_new,_filesystem_path
from . import capture_archive as storage
from .capture_activity import fenced_recovery


def _shape(root):
    packs=set();seals=set()
    for path in root.iterdir():
        require_private(path)
        if path.name=='head.json':continue
        match=re.fullmatch(r'([0-9]{6})\.(pack|seal.json)',path.name)
        if match is None:raise ValueError('PUBLIC_ARCHIVE_RECOVERY_INVENTORY_INVALID')
        number=int(match[1])
        if not 1<=number<=storage.MAX_SEGMENTS:raise ValueError('PUBLIC_ARCHIVE_RECOVERY_FILE_CAPACITY')
        (packs if match[2]=='pack' else seals).add(number)
    if not packs or packs!=set(range(1,max(packs)+1)) or not seals<=packs:
        raise ValueError('PUBLIC_ARCHIVE_RECOVERY_INVENTORY_INVALID')
    return packs,seals


def _scan_suffix(archive,raw,disposition):
    while archive.state['offset']<len(raw):
        archive.deadline();offset=archive.state['offset']
        if len(raw)-offset<8:break
        a,b=struct.unpack('!II',raw[offset:offset+8]);size=8+a+b
        if size>storage.MAX_PACK_BYTES or offset+size>len(raw):break
        frame=raw[offset:offset+size]
        pointer=dict(pack=storage._pack(archive.state['pack']),offset=offset,size=size,sha256=digest(frame))
        before=deepcopy(archive.state);skip=archive._pending_skip
        try:
            metadata,payload=archive._read_pointer(pointer)
            if metadata['kind']=='COMMIT':
                # Original bytes, same capture/path and preceding FILE lineage.
                archive.capture_inventory(pointer)
            archive._apply(metadata,payload,pointer)
        except (ValueError,TypeError,KeyError,OverflowError):
            archive.state=before;archive._pending_skip=skip
            break  # Never search for a later frame after an uncertain byte.
        if metadata['kind']=='COMMIT':disposition['replayed_capture_indexes'].append(pointer)


def _adopt_rotation(archive,raw,*,existing):
    state=archive.state;number=state['pack'];name=f'{number:06d}.seal.json'
    if number>=storage.MAX_SEGMENTS:raise ValueError('PUBLIC_ARCHIVE_RECOVERY_FILE_CAPACITY')
    torn=state['offset']<len(raw)
    seal=(archive._recovery_seal(number,raw,previous_seal=state['sealed_tip']) if torn else
        dict(schema_version=storage.SCHEMA,pack=storage._pack(number),bytes=len(raw),sha256=digest(raw),
            last_sequence=state['sequence'],tip=state['tip'],previous_seal=state['sealed_tip']))
    encoded=canonical(seal).encode()
    if existing:
        original=read_local(archive.root,name,4096)
        if decode(original)!=seal:raise ValueError('PUBLIC_ARCHIVE_RECOVERY_EXISTING_SEAL_CONFLICT')
        encoded=original
    additional=len(raw)-state['offset']+len(encoded)
    if state['physical_bytes']+additional+65536>storage.MAX_TOTAL_BYTES:
        raise ValueError('PUBLIC_ARCHIVE_RECOVERY_TOTAL_CAPACITY')
    if not existing:
        if not torn:raise ValueError('PUBLIC_ARCHIVE_RECOVERY_ROTATION_NOT_PREPARED')
        with _filesystem_path(archive.root/storage._pack(number)).open('r+b') as stream:os.fsync(stream.fileno())
        write_private_new(archive.root/name,encoded)
    if torn:
        state['request_accounting']='INCOMPLETE';archive._pending_skip=seal['skipped_until']
    state['physical_bytes']+=additional;state['sealed_tip']=digest(encoded)
    state.update(pack=number+1,offset=0,pack_frames=0,active_request_budget_upper=0)
    following=archive.root/storage._pack(number+1)
    if not following.exists():write_private_new(following,b'')
    else:require_private(following)


def _repair_prefix(root,fence,disposition):
    require_private(root,directory=True);packs,seals=_shape(root)
    archive=object.__new__(storage.PublicCaptureArchive)
    archive.root=root;archive.scope='public-archive:'+hashlib.sha256(str(root).casefold().encode()).hexdigest()
    archive.deadline=lambda:fence.require(root.parent);archive._pending_skip=None
    archive._io_init()
    with archive._locked():
        archive.state=storage._head(read_local(root,'head.json',65536))
        archive._verify_all(_committed_prefix_only=True)
        while True:
            archive.deadline();number=archive.state['pack']
            raw=read_local(root,storage._pack(number),storage.MAX_PACK_BYTES)
            _scan_suffix(archive,raw,disposition)
            if archive.state['offset']<len(raw) or number in seals:
                _adopt_rotation(archive,raw,existing=number in seals)
                seals.add(number);packs.add(archive.state['pack'])
                continue
            if number!=max(packs):raise ValueError('PUBLIC_ARCHIVE_RECOVERY_UNSEALED_PACK_CONFLICT')
            break
        if archive._pending_skip is not None:
            payload=dict(retired={},owner_generation=fence.generation,skipped_until=archive._pending_skip,
                source_seal=archive.state['sealed_tip'])
            archive._append('RECOVERY',str(uuid.uuid4()),'',canonical(payload).encode())
        else:archive._save()
        archive._verify_all()
    return archive


def _staging(config,token,kind):
    name='public-market-observations' if kind=='market' else 'public-funding-observations'
    base=config.local_data_root/name
    if not base.exists():return None,base
    require_private(base,directory=True);found=[]
    for index,owner in enumerate(base.iterdir()):
        if index>=256:raise ValueError('PUBLIC_ARCHIVE_RECOVERY_OWNER_INVENTORY_LIMIT')
        require_private(owner,directory=True)
        storage._token(owner.name)
        path=owner/token
        if path.exists():require_private(path,directory=True);found.append(path)
    if len(found)>1:raise ValueError('PUBLIC_ARCHIVE_RECOVERY_STAGING_CONFLICT')
    return found[0] if found else None,base


def recover_public_archive(config,owner):
    disposition=dict(status='OWNER_FENCED_ARCHIVE_CHECK',replayed_capture_indexes=[],
        retired_orphan_reservations=[],archived_orphan_indexes={})
    from . import public_feed
    root=config.local_data_root/storage.ROOT
    with fenced_recovery(config,owner) as fence:
        if not root.exists():
            # An old capture tree requires explicit bounded import; never a new
            # empty counter. Fresh configured profiles need no migration.
            archive=public_feed._archive_for(config)
        else:archive=_repair_prefix(root,fence,disposition)
        for token,bounds in list(archive.state['pending'].items()):
            fence.require(config.local_data_root)
            path,base=_staging(config,token,bounds['kind'])
            if path is not None and archive.directory_files(path,_inventory_only=True):
                pointer=archive.commit_directory(token,path,requests=0,responses=0,complete=False)
                disposition['archived_orphan_indexes'][token]=pointer
                archive.release_directory(pointer,path,staging_root=base)
            else:
                payload=dict(retired={token:bounds},owner_generation=fence.generation,skipped_until=None,source_seal=None)
                with archive._locked():
                    archive._reload();archive._append('RECOVERY',str(uuid.uuid4()),'',canonical(payload).encode())
            disposition['retired_orphan_reservations'].append(token)
        fence.require(config.local_data_root)
        verified=storage.PublicCaptureArchive(root,_deadline=lambda:fence.require(config.local_data_root))
        verified.deadline=lambda:None
        with public_feed._archives_lock:public_feed._archives[root]=verified
    return verified,disposition
