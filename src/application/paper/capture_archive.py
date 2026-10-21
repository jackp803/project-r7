"""Owner-private public capture packs, shared across runtime generations.

Only verified redundant loose captures may later be released. Committed frames
and sealed packs never change. A torn/uncommitted suffix is preserved and
refuses admission; restart is not a quota reset or invented complete accounting.
No database, financial authority, background network or protection-thread work.
"""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import stat
import struct
import uuid
import zlib

from application.cloud.manifest import safe_relative
from application.datasets.catalog import canonical, decode, digest, read_local
from application.platform.private_files import (create_private_directory, require_private,
    write_private_atomic, write_private_new, _filesystem_path)
from application.platform.scope_lock import ProcessScopeLock
from application.platform.supervision import _local_path

SCHEMA = 'r7-public-capture-archive-v0.1'
ROOT = 'public-source-archive'
MAX_PACK_BYTES = 16*1024**2
MAX_FRAMES = 8192
MAX_CACHE = 128
MAX_SEGMENTS = 1536  # <=3,073 files; reserve the rest of the 4,096-file backup.
MAX_TOTAL_BYTES = 8*1024**3
DISK_RESERVE = 2*1024**3
EMERGENCY_RESERVE = 1024**3
EMERGENCY_SEGMENTS = 128
MAX_RAW = 12*1024**2
MAX_HEADER_BYTES = 16384
ZERO = 'sha256:'+'0'*64
HEAD_KEYS = {'schema_version','pack','offset','pack_frames','sequence','tip','sealed_tip',
    'physical_bytes','raw_bytes','deduplicated_payload_bytes','provider_requests','provider_responses',
    'request_accounting','captures','pending','cache'}
POINTER_KEYS = {'pack','offset','size','sha256'}


def _fail(reason):
    raise ValueError('PUBLIC_ARCHIVE_'+reason)


def _token(value):
    if type(value) is not str or len(value)!=36:
        _fail('CAPTURE_ID_INVALID')
    parsed=uuid.UUID(value)
    if parsed.version!=4 or str(parsed)!=value:
        _fail('CAPTURE_ID_INVALID')
    return value


def _initial():
    return dict(schema_version=SCHEMA,pack=1,offset=0,pack_frames=0,sequence=0,tip=ZERO,
        sealed_tip=ZERO,physical_bytes=0,raw_bytes=0,deduplicated_payload_bytes=0,
        provider_requests=0,provider_responses=0,request_accounting='COMPLETE',captures=0,pending={},cache={})


def _pack(number):
    return f'{number:06d}.pack'


def _head(raw):
    value=decode(raw)
    if type(value) is not dict or set(value)!=HEAD_KEYS or value['schema_version']!=SCHEMA:
        _fail('HEAD_INVALID')
    for key in ('pack','offset','pack_frames','sequence','physical_bytes','raw_bytes',
            'deduplicated_payload_bytes','provider_requests','provider_responses','captures'):
        if type(value[key]) is not int or value[key]<0:
            _fail('HEAD_INVALID')
    if (not 1<=value['pack']<=MAX_SEGMENTS or value['offset']>MAX_PACK_BYTES
            or value['request_accounting'] not in ('COMPLETE','INCOMPLETE')
            or type(value['pending']) is not dict or len(value['pending'])>3
            or type(value['cache']) is not dict or len(value['cache'])>MAX_CACHE):
        _fail('HEAD_INVALID')
    return value


class PublicCaptureArchive:
    """Bounded append/restore port; all mutations use a cross-process scope."""
    def __init__(self, root, *, _deadline=None):
        self.root=Path(root).absolute(); _local_path(self.root)
        self.deadline=_deadline or (lambda:None)
        self.scope='public-archive:'+hashlib.sha256(str(self.root).casefold().encode()).hexdigest()
        self.state=None
        with self._locked():
            if not self.root.exists():
                create_private_directory(self.root)
                write_private_new(self.root/_pack(1),b'')
                self.state=_initial(); self._save()
            else:
                require_private(self.root,directory=True)
                if not (self.root/'head.json').exists():
                    _fail('RECOVERY_REQUIRED')
                self.state=_head(read_local(self.root,'head.json',65536))
                self._verify_all()

    @contextmanager
    def _locked(self):
        with ProcessScopeLock(self.scope,lock_root=self.root.parent/'process-scopes'):
            yield

    def _save(self):
        write_private_atomic(self.root/'head.json',canonical(self.state).encode())

    def _reload(self):
        state=_head(read_local(self.root,'head.json',65536))
        path=self.root/_pack(state['pack']); require_private(path)
        if _filesystem_path(path).stat().st_size!=state['offset']:
            _fail('RECOVERY_REQUIRED')
        if self.state is not None and state['sequence']<self.state['sequence']:
            _fail('COUNTER_ROLLBACK')
        self.state=state

    def _read_pointer(self, pointer, *, references=True):
        if (type(pointer) is not dict or set(pointer)!=POINTER_KEYS
                or type(pointer['pack']) is not str or len(pointer['pack'])!=11
                or not pointer['pack'][:6].isdigit() or not pointer['pack'].endswith('.pack')
                or type(pointer['offset']) is not int or pointer['offset']<0
                or type(pointer['size']) is not int or not 8<=pointer['size']<=MAX_PACK_BYTES):
            _fail('POINTER_INVALID')
        from application.platform.product_backup import _opened_source
        path=self.root/pointer['pack']; require_private(path)
        with _opened_source(path) as stream:
            stream.seek(pointer['offset']); frame=stream.read(pointer['size'])
        if len(frame)!=pointer['size'] or digest(frame)!=pointer['sha256']:
            _fail('FRAME_INVALID')
        metadata,raw=self._decode_frame(frame)
        if metadata['reference'] is not None:
            if not references:
                _fail('REFERENCE_CHAIN_FORBIDDEN')
            target=metadata['reference']
            if (target['pack'],target['offset']) >= (pointer['pack'],pointer['offset']):
                _fail('REFERENCE_ORDER_INVALID')
            _,raw=self._read_pointer(target,references=False)
        if len(raw)!=metadata['bytes'] or digest(raw)!=metadata['raw_hash']:
            _fail('ORIGINAL_BYTES_INVALID')
        return metadata,raw

    def _decode_frame(self, frame):
        if len(frame)<8:
            _fail('FRAME_INVALID')
        length,size=struct.unpack('!II',frame[:8])
        if not 1<=length<=MAX_HEADER_BYTES or len(frame)!=8+length+size:
            _fail('FRAME_INVALID')
        metadata=decode(frame[8:8+length])
        if (type(metadata) is not dict or set(metadata)!={'sequence','previous','kind','capture_id','path',
                'bytes','raw_hash','reference'} or type(metadata['sequence']) is not int
                or type(metadata['bytes']) is not int or not 0<=metadata['bytes']<=MAX_RAW):
            _fail('FRAME_INVALID')
        _token(metadata['capture_id'])
        compressed=frame[8+length:]
        if metadata['reference'] is not None:
            if compressed or metadata['kind']!='FILE' or not metadata['path'].endswith('-response.bin'):
                _fail('REFERENCE_INVALID')
            return metadata,b''
        inflater=zlib.decompressobj()
        try:
            raw=inflater.decompress(compressed,metadata['bytes']+1)
        except zlib.error:
            _fail('COMPRESSED_FRAME_INVALID')
        if (len(raw)!=metadata['bytes'] or inflater.unconsumed_tail or inflater.unused_data or not inflater.eof
                or digest(raw)!=metadata['raw_hash']):
            _fail('COMPRESSED_FRAME_INVALID')
        return metadata,raw

    def _apply(self, metadata, raw, pointer):
        state=self.state
        if metadata['sequence']!=state['sequence']+1 or metadata['previous']!=state['tip']:
            _fail('FRAME_CHAIN_INVALID')
        kind=metadata['kind']; token=metadata['capture_id']
        if kind=='RESERVE':
            value=decode(raw)
            if token in state['pending'] or len(state['pending'])>=3:
                _fail('RESERVATION_INVALID')
            state['pending'][token]=value
        elif kind=='COMMIT':
            value=decode(raw); reserved=state['pending'].pop(token,None)
            if (reserved is None or value['requests']>reserved['maximum_requests']
                    or value['responses']>value['requests']):
                _fail('RESERVATION_INVALID')
            state['provider_requests']+=value['requests']; state['provider_responses']+=value['responses']
            state['captures']+=1
            if not value['complete']: state['request_accounting']='INCOMPLETE'
        elif kind!='FILE' or token not in state['pending']:
            _fail('FRAME_KIND_INVALID')
        if kind=='FILE' and metadata['path'].endswith('-response.bin'):
            if metadata['reference'] is None:
                state['cache'].pop(metadata['raw_hash'],None)
                state['cache'][metadata['raw_hash']]=pointer
                while len(state['cache'])>MAX_CACHE:
                    oldest=min(state['cache'],key=lambda key:(state['cache'][key]['pack'],state['cache'][key]['offset']))
                    state['cache'].pop(oldest)
            else: state['deduplicated_payload_bytes']+=metadata['bytes']
        state['raw_bytes']+=metadata['bytes']; state['physical_bytes']+=pointer['size']
        state['sequence']=metadata['sequence']; state['tip']=pointer['sha256']
        state['offset']+=pointer['size']; state['pack_frames']+=1

    def _verify_all(self):
        expected=self.state; self.state=_initial(); previous_seal=ZERO
        names={'head.json'}
        for number in range(1,expected['pack']+1):
            self.deadline()
            name=_pack(number); names.add(name); raw=read_local(self.root,name,MAX_PACK_BYTES)
            offset=0; self.state.update(pack=number,offset=0,pack_frames=0)
            while offset<len(raw):
                self.deadline()
                if len(raw)-offset<8: _fail('RECOVERY_REQUIRED')
                a,b=struct.unpack('!II',raw[offset:offset+8]); size=8+a+b
                if size>MAX_PACK_BYTES or offset+size>len(raw): _fail('RECOVERY_REQUIRED')
                frame=raw[offset:offset+size]; metadata,payload=self._decode_frame(frame)
                pointer=dict(pack=name,offset=offset,size=size,sha256=digest(frame))
                if metadata['reference'] is not None:
                    self._read_pointer(pointer)  # Verify retained original, never a cache assertion.
                self._apply(metadata,payload,pointer); offset+=size
            if number<expected['pack']:
                seal_name=f'{number:06d}.seal.json'; names.add(seal_name)
                seal_raw=read_local(self.root,seal_name,4096); seal=decode(seal_raw)
                if seal!=dict(schema_version=SCHEMA,pack=name,bytes=len(raw),sha256=digest(raw),
                        last_sequence=self.state['sequence'],tip=self.state['tip'],previous_seal=previous_seal):
                    _fail('SEAL_INVALID')
                previous_seal=digest(seal_raw)
                self.state['physical_bytes']+=len(seal_raw); self.state['sealed_tip']=previous_seal
        if {p.name for p in self.root.iterdir()}!=names or self.state!=expected:
            _fail('RECOVERY_REQUIRED')

    def _seal(self):
        state=self.state
        if state['pack']>=MAX_SEGMENTS: _fail('FILE_CAPACITY')
        name=_pack(state['pack']); raw=read_local(self.root,name,MAX_PACK_BYTES)
        seal=canonical(dict(schema_version=SCHEMA,pack=name,bytes=len(raw),sha256=digest(raw),
            last_sequence=state['sequence'],tip=state['tip'],previous_seal=state['sealed_tip'])).encode()
        write_private_new(self.root/f"{state['pack']:06d}.seal.json",seal)
        state['sealed_tip']=digest(seal); state['physical_bytes']+=len(seal)
        state.update(pack=state['pack']+1,offset=0,pack_frames=0)
        write_private_new(self.root/_pack(state['pack']),b''); self._save()

    def _append(self,kind,token,path,raw):
        state=self.state
        if type(raw) is not bytes or len(raw)>MAX_RAW: _fail('RAW_LIMIT')
        reference=state['cache'].get(digest(raw)) if kind=='FILE' and path.endswith('-response.bin') else None
        metadata=dict(sequence=state['sequence']+1,previous=state['tip'],kind=kind,capture_id=token,
            path=path,bytes=len(raw),raw_hash=digest(raw),reference=reference)
        header=canonical(metadata).encode(); compressed=b'' if reference is not None else zlib.compress(raw,1)
        frame=struct.pack('!II',len(header),len(compressed))+header+compressed
        if len(header)>MAX_HEADER_BYTES or len(frame)>MAX_PACK_BYTES: _fail('FRAME_LIMIT')
        if state['offset']+len(frame)>MAX_PACK_BYTES or state['pack_frames']>=MAX_FRAMES:
            self._seal()
        pointer=dict(pack=_pack(state['pack']),offset=state['offset'],size=len(frame),sha256=digest(frame))
        path=self.root/pointer['pack']; require_private(path)
        with _filesystem_path(path).open('ab') as stream:
            stream.write(frame); stream.flush(); os.fsync(stream.fileno())
        self._apply(metadata,raw,pointer)
        if kind!='FILE': self._save()
        return pointer

    def reserve(self,capture_id,*,kind,maximum_requests,maximum_bytes,maximum_files=1024,emergency=False):
        _token(capture_id)
        if (kind not in ('market','funding','preflight') or type(maximum_requests) is not int
                or not 1<=maximum_requests<=165 or type(maximum_bytes) is not int
                or not 1<=maximum_bytes<=512*1024**2 or type(maximum_files) is not int
                or not 1<=maximum_files<=1024 or type(emergency) is not bool):
            _fail('RESERVATION_INVALID')
        with self._locked():
            self._reload(); state=self.state
            if state['request_accounting']!='COMPLETE' and not emergency: _fail('ACCOUNTING_INCOMPLETE')
            if capture_id in state['pending'] or len(state['pending'])>=3: _fail('PENDING_RESERVATION_LIMIT')
            reserved=sum(item['maximum_bytes'] for item in state['pending'].values())
            if reserved+maximum_bytes>1024**3: _fail('ACTIVE_CAPACITY')
            reserved_frames=sum(item['maximum_files']+2 for item in state['pending'].values())
            limit=MAX_TOTAL_BYTES if emergency else MAX_TOTAL_BYTES-EMERGENCY_RESERVE
            if state['physical_bytes']+reserved+maximum_bytes+65536>limit: _fail('TOTAL_CAPACITY')
            # Either the byte or frame bound can seal a pack. Reserve their
            # conservative combined envelope before dispatch, including other
            # sources' outstanding captures and finite emergency file space.
            # Next-fit packing can waste almost one maximum frame per sealed
            # pack. Aggregate bytes/P is insufficient for >half-pack frames.
            largest=min(MAX_PACK_BYTES-1,MAX_RAW+MAX_HEADER_BYTES+MAX_RAW//1000+72)
            minimum_filled=MAX_PACK_BYTES-largest
            packs=(1+(state['offset']+reserved+maximum_bytes+65536)//minimum_filled
                +(state['pack_frames']+reserved_frames+maximum_files+2)//MAX_FRAMES)
            segment_limit=MAX_SEGMENTS if emergency else MAX_SEGMENTS-EMERGENCY_SEGMENTS
            if state['pack']-1+packs>segment_limit: _fail('FILE_CAPACITY')
            if shutil.disk_usage(self.root).free<DISK_RESERVE+reserved+maximum_bytes: _fail('DISK_CAPACITY')
            value=dict(kind=kind,maximum_requests=maximum_requests,maximum_bytes=maximum_bytes,maximum_files=maximum_files,emergency=emergency)
            return self._append('RESERVE',capture_id,'',canonical(value).encode())

    def commit(self,capture_id,files,*,requests,responses,complete):
        _token(capture_id)
        if (type(files) is not dict or not 1<=len(files)<=1024 or type(requests) is not int
                or type(responses) is not int or not 0<=responses<=requests<=165 or type(complete) is not bool):
            _fail('COMMIT_INVALID')
        for relative,raw in files.items():
            safe_relative(relative)
            if type(raw) is not bytes or len(raw)>MAX_RAW: _fail('RAW_LIMIT')
        with self._locked():
            self._reload(); reservation=self.state['pending'].get(capture_id)
            if (reservation is None or requests>reservation['maximum_requests'] or len(files)>reservation['maximum_files']
                    or sum(len(raw)+max(1024,len(raw)//1000+64) for raw in files.values())+4096>reservation['maximum_bytes']):
                _fail('RESERVATION_EXCEEDED')
            index={}
            for relative,raw in sorted(files.items()):
                pointer=self._append('FILE',capture_id,relative,raw)
                if self._read_pointer(pointer)[1]!=raw: _fail('READBACK_INVALID')
                index[relative]=pointer
            value=dict(files=index,requests=requests,responses=responses,complete=complete)
            pointer=self._append('COMMIT',capture_id,'',canonical(value).encode())
            if self.read_capture(pointer)!=files: _fail('CAPTURE_READBACK_INVALID')
            return pointer

    def read_capture(self,pointer):
        metadata,files=self._capture_entries(pointer)
        return {relative:self._capture_file(metadata,relative,reference)
            for relative,reference in files.items()}

    def _capture_entries(self,pointer):
        metadata,raw=self._read_pointer(pointer)
        if metadata['kind']!='COMMIT': _fail('CAPTURE_INDEX_REQUIRED')
        value=decode(raw); files=value.get('files')
        if type(files) is not dict or not 1<=len(files)<=1024: _fail('CAPTURE_INDEX_INVALID')
        return metadata,files

    def _capture_file(self,metadata,relative,reference):
        safe_relative(relative); record,payload=self._read_pointer(reference)
        if (record['kind']!='FILE' or record['path']!=relative or record['capture_id']!=metadata['capture_id']
                or record['sequence']>=metadata['sequence']): _fail('CAPTURE_INDEX_INVALID')
        return payload

    def commit_directory(self,capture_id,directory,*,requests,responses,complete):
        """Archive bounded pages individually; never load an entire market batch."""
        _token(capture_id)
        if (type(requests) is not int or type(responses) is not int
                or not 0<=responses<=requests<=165 or type(complete) is not bool): _fail('COMMIT_INVALID')
        directory=Path(directory).absolute(); facts=self.directory_files(directory,_inventory_only=True)
        with self._locked():
            self._reload(); reservation=self.state['pending'].get(capture_id)
            if (reservation is None or requests>reservation['maximum_requests'] or len(facts)>reservation['maximum_files']
                    or sum(row['bytes']+max(1024,row['bytes']//1000+64) for row in facts.values())+4096>reservation['maximum_bytes']):
                _fail('RESERVATION_EXCEEDED')
            index={}
            for relative,fact in sorted(facts.items()):
                raw=read_local(directory,relative,MAX_RAW)
                if len(raw)!=fact['bytes'] or digest(raw)!=fact['sha256']: _fail('STAGING_READBACK_INVALID')
                pointer=self._append('FILE',capture_id,relative,raw)
                if self._read_pointer(pointer)[1]!=raw: _fail('READBACK_INVALID')
                index[relative]=pointer
            value=dict(files=index,requests=requests,responses=responses,complete=complete)
            pointer=self._append('COMMIT',capture_id,'',canonical(value).encode())
            metadata,retained=self._capture_entries(pointer)
            if retained!=index: _fail('CAPTURE_READBACK_INVALID')
            return pointer

    def capture_inventory(self,pointer):
        metadata,files=self._capture_entries(pointer); result={}
        for relative,reference in files.items():
            raw=self._capture_file(metadata,relative,reference)
            result[relative]=dict(bytes=len(raw),sha256=digest(raw))
        return result

    @staticmethod
    def directory_files(root,*,_inventory_only=False):
        root=Path(root).absolute(); _local_path(root); require_private(root,directory=True)
        files={}; pending=[root]; visited=0; total=0
        while pending:
            directory=pending.pop(); _local_path(directory)
            for path in directory.iterdir():
                visited+=1
                if visited>1100: _fail('STAGING_INVENTORY_LIMIT')
                _local_path(path); relative=path.relative_to(root).as_posix(); safe_relative(relative)
                information=_filesystem_path(path).lstat()
                if stat.S_ISDIR(information.st_mode):
                    if len(path.relative_to(root).parts)>4: _fail('STAGING_INVENTORY_LIMIT')
                    pending.append(path)
                elif stat.S_ISREG(information.st_mode) and information.st_nlink==1:
                    require_private(path); raw=read_local(root,relative,MAX_RAW)
                    total+=len(raw)
                    if total>512*1024**2 or len(files)>=1024: _fail('STAGING_INVENTORY_LIMIT')
                    files[relative]=dict(bytes=len(raw),sha256=digest(raw)) if _inventory_only else raw
                else: _fail('STAGING_REGULAR_FILES_REQUIRED')
        return files

    def release_directory(self,pointer,directory,*,staging_root):
        """Release only exact redundant bytes after the child was actually reaped.

        The caller supplies its explicit staging root. Reparse/link checks and
        complete readback precede any unlink; no recursive computed-path delete.
        Interrupted cleanup leaves archive authority and remaining loose bytes.
        """
        directory=Path(directory).absolute(); staging_root=Path(staging_root).absolute()
        _local_path(staging_root); _local_path(directory)
        try:
            resolved=directory.resolve(strict=True); boundary=staging_root.resolve(strict=True)
        except OSError:
            _fail('STAGING_BOUNDARY_INVALID')
        if resolved==boundary or not resolved.is_relative_to(boundary): _fail('STAGING_BOUNDARY_INVALID')
        files=self.capture_inventory(pointer)
        if self.directory_files(directory,_inventory_only=True)!=files: _fail('STAGING_READBACK_INVALID')
        directories={directory}
        for relative in files:
            path=directory/relative
            directories.update(parent for parent in path.parents if parent==directory or parent.is_relative_to(directory))
        for relative in files:
            path=directory/relative; _local_path(path); require_private(path)
            _filesystem_path(path).unlink()
        for path in sorted(directories,key=lambda item:len(item.parts),reverse=True):
            _local_path(path); _filesystem_path(path).rmdir()

    def summary(self):
        with self._locked():
            self._reload(); state=self.state
            accounting='INCOMPLETE' if state['request_accounting']=='INCOMPLETE' else 'PENDING' if state['pending'] else 'COMPLETE'
            return {**{key:state[key] for key in ('physical_bytes','raw_bytes','deduplicated_payload_bytes',
                'captures')},'request_accounting':accounting,
                'provider_requests':state['provider_requests'] if accounting=='COMPLETE' else None,
                'provider_responses':state['provider_responses'] if accounting=='COMPLETE' else None,
                'completed_capture_requests':state['provider_requests'],'completed_capture_responses':state['provider_responses'],
                'sealed_segments':state['pack']-1,'pending_reservations':len(state['pending']),
                'reserved_bytes':sum(item['maximum_bytes'] for item in state['pending'].values())}
