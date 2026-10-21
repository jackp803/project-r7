"""Owner-private public capture packs, shared across runtime generations.

Only verified redundant loose captures may later be released. Committed frames
and sealed packs never change. A torn/uncommitted suffix is preserved and
refuses admission; restart is not a quota reset or invented complete accounting.
No database, financial authority, background network or protection-thread work.
"""
from contextlib import contextmanager
from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
import shutil
import re
import stat
import struct
import threading
import uuid
import zlib

from application.cloud.manifest import safe_relative
from application.cloud.protocol import CloudError
from application.datasets.catalog import canonical, decode, digest, read_local
from application.platform.private_files import (create_private_directory, require_private,
    write_private_atomic, write_private_new, _filesystem_path)
from application.platform.scope_lock import ProcessScopeLock
from application.platform.supervision import _local_path

SCHEMA = 'r7-public-capture-archive-v0.2'
ROOT = 'public-source-archive'
MAX_PACK_BYTES = 16*1024**2
MAX_FRAMES = 8192
MAX_ACTIVE_REQUESTS = 86400
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
    'request_accounting','captures','pending','cache','active_request_budget_upper','request_budget_upper'}
POINTER_KEYS = {'pack','offset','size','sha256'}
HASH_PATTERN=re.compile(r'sha256:[0-9a-f]{64}\Z')


def _fail(reason):
    raise ValueError('PUBLIC_ARCHIVE_'+reason)


def _token(value):
    if type(value) is not str or len(value)!=36:
        _fail('CAPTURE_ID_INVALID')
    parsed=uuid.UUID(value)
    if parsed.version!=4 or str(parsed)!=value:
        _fail('CAPTURE_ID_INVALID')
    return value


def _hash(value):
    return type(value) is str and HASH_PATTERN.fullmatch(value) is not None


def _header_pairs(items):
    value={}
    for key,item in items:
        if key in value:_fail('FRAME_INVALID')
        value[key]=item
    return value


def _pointer_shape(pointer):
    if (type(pointer) is not dict or set(pointer)!=POINTER_KEYS
            or type(pointer['pack']) is not str or len(pointer['pack'])!=11
            or not pointer['pack'][:6].isascii() or not pointer['pack'][:6].isdigit()
            or not pointer['pack'].endswith('.pack')
            or not 1<=int(pointer['pack'][:6])<=MAX_SEGMENTS
            or type(pointer['offset']) is not int or pointer['offset']<0
            or type(pointer['size']) is not int or not 8<=pointer['size']<=MAX_PACK_BYTES
            or pointer['offset']+pointer['size']>MAX_PACK_BYTES or not _hash(pointer['sha256'])):
        _fail('POINTER_INVALID')


def _initial():
    return dict(schema_version=SCHEMA,pack=1,offset=0,pack_frames=0,sequence=0,tip=ZERO,
        sealed_tip=ZERO,physical_bytes=0,raw_bytes=0,deduplicated_payload_bytes=0,
        provider_requests=0,provider_responses=0,request_accounting='COMPLETE',captures=0,pending={},cache={},
        active_request_budget_upper=0,request_budget_upper=0)


def _pack(number):
    return f'{number:06d}.pack'


def _head(raw):
    value=decode(raw)
    if type(value) is not dict or set(value)!=HEAD_KEYS or value['schema_version']!=SCHEMA:
        _fail('HEAD_INVALID')
    for key in ('pack','offset','pack_frames','sequence','physical_bytes','raw_bytes',
            'deduplicated_payload_bytes','provider_requests','provider_responses','captures',
            'active_request_budget_upper','request_budget_upper'):
        if type(value[key]) is not int or value[key]<0:
            _fail('HEAD_INVALID')
    if (not 1<=value['pack']<=MAX_SEGMENTS or value['offset']>MAX_PACK_BYTES
            or value['active_request_budget_upper']>MAX_ACTIVE_REQUESTS
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
        self._pending_skip=None
        self._io_init()
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
        with self._thread_lock:
            if self._lock_thread==threading.get_ident():
                yield;return
            with ProcessScopeLock(self.scope,lock_root=self.root.parent/'process-scopes'):
                self._lock_thread=threading.get_ident()
                try:yield
                finally:self._lock_thread=None

    def _io_init(self):
        self._thread_lock=threading.RLock();self._lock_thread=None
        self._writer=None;self._write_enabled=False;self._readers=None
        self._verified_frame_paths=set();self._last_frame_capture_id=None

    def _close_writer(self):
        if self._writer is not None:
            _,context,stream=self._writer;self._writer=None
            try:stream.flush();os.fsync(stream.fileno())
            finally:context.__exit__(None,None,None)

    @contextmanager
    def _writing(self):
        self._write_enabled=True
        try:yield
        finally:
            try:self._close_writer()
            finally:self._write_enabled=False

    @contextmanager
    def _reading(self):
        if self._readers is not None:
            yield;return
        self._readers=OrderedDict()
        try:yield
        finally:
            readers,self._readers=self._readers,None
            for context,_ in readers.values():context.__exit__(None,None,None)

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
        _pointer_shape(pointer)
        from application.platform.product_backup import _opened_source
        path=self.root/pointer['pack']
        if self._readers is not None:
            item=self._readers.pop(pointer['pack'],None)
            if item is None:
                require_private(path);context=_opened_source(path);item=(context,context.__enter__())
            self._readers[pointer['pack']]=item
            while len(self._readers)>8:
                _,(context,_)=self._readers.popitem(last=False);context.__exit__(None,None,None)
            stream=item[1];stream.seek(pointer['offset']);frame=stream.read(pointer['size'])
        else:
            require_private(path)
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
        # Header has a closed primitive/pointer shape, checked below. Parsing
        # that exact shape avoids a second generic recursive manifest walk for
        # every one of millions of tiny frames. Duplicate fields still refuse.
        try:metadata=json.loads(frame[8:8+length],object_pairs_hook=_header_pairs)
        except (ValueError,UnicodeError,RecursionError):_fail('FRAME_INVALID')
        if (type(metadata) is not dict or set(metadata)!={'sequence','previous','kind','capture_id','path',
                'bytes','raw_hash','reference'} or type(metadata['sequence']) is not int
                or type(metadata['bytes']) is not int or not 0<=metadata['bytes']<=MAX_RAW):
            _fail('FRAME_INVALID')
        if (metadata['sequence']<1 or type(metadata['kind']) is not str
                or metadata['kind'] not in ('FILE','RESERVE','COMMIT','RECOVERY')
                or type(metadata['path']) is not str or not _hash(metadata['previous'])
                or not _hash(metadata['raw_hash'])):
            _fail('FRAME_INVALID')
        if metadata['kind']=='FILE':
            path=metadata['path']
            if path not in self._verified_frame_paths:
                try:safe_relative(path)
                except CloudError:_fail('FRAME_PATH_INVALID')
                if len(self._verified_frame_paths)>=128:self._verified_frame_paths.clear()
                self._verified_frame_paths.add(path)
        elif metadata['path']!='':
            _fail('FRAME_PATH_INVALID')
        if type(metadata['capture_id']) is not str or metadata['capture_id']!=self._last_frame_capture_id:
            _token(metadata['capture_id']);self._last_frame_capture_id=metadata['capture_id']
        compressed=frame[8+length:]
        if metadata['reference'] is not None:
            _pointer_shape(metadata['reference'])
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

    def _apply(self, metadata, raw, pointer,*,_decoded=None):
        state=self.state
        expected_sequence=state['sequence']+1
        if metadata['kind']=='RECOVERY' and self._pending_skip is not None:
            expected_sequence=self._pending_skip+1
        if metadata['sequence']!=expected_sequence or metadata['previous']!=state['tip']:
            _fail('FRAME_CHAIN_INVALID')
        kind=metadata['kind']; token=metadata['capture_id']
        if kind=='RESERVE':
            value=decode(raw)
            if token in state['pending'] or len(state['pending'])>=3:
                _fail('RESERVATION_INVALID')
            if state['active_request_budget_upper']+value['maximum_requests']>MAX_ACTIVE_REQUESTS:
                _fail('ACTIVE_REQUEST_BUDGET_INVALID')
            state['pending'][token]=value
            state['active_request_budget_upper']+=value['maximum_requests']
            state['request_budget_upper']+=value['maximum_requests']
        elif kind=='COMMIT':
            value=decode(raw) if _decoded is None else _decoded; reserved=state['pending'].get(token)
            if (type(value) is not dict or set(value)!={'files','requests','responses','complete'}
                    or type(value['files']) is not dict or not 1<=len(value['files'])<=1024
                    or type(value['requests']) is not int or type(value['responses']) is not int
                    or type(value['complete']) is not bool or not 0<=value['responses']<=value['requests']
                    or reserved is None or value['requests']>reserved['maximum_requests']
                    or value['responses']>value['requests']):
                _fail('RESERVATION_INVALID')
            state['pending'].pop(token)
            state['provider_requests']+=value['requests']; state['provider_responses']+=value['responses']
            state['captures']+=1
            if not value['complete']: state['request_accounting']='INCOMPLETE'
        elif kind=='RECOVERY':
            value=decode(raw) if _decoded is None else _decoded
            if (type(value) is not dict or set(value)!={'retired','owner_generation','skipped_until','source_seal'}
                    or type(value['retired']) is not dict or len(value['retired'])>3
                    or value['skipped_until']!=self._pending_skip
                    or value['source_seal']!=(state['sealed_tip'] if self._pending_skip is not None else None)):
                _fail('RECOVERY_RECORD_INVALID')
            _token(value['owner_generation'])
            for orphan,bounds in value['retired'].items():
                if state['pending'].get(orphan)!=bounds:_fail('RECOVERY_ORPHAN_INVALID')
                state['pending'].pop(orphan)
            if value['retired'] or self._pending_skip is not None:state['request_accounting']='INCOMPLETE'
            self._pending_skip=None
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

    def _recovery_seal(self,number,raw,*,previous_seal):
        state=self.state;offset=state['offset']
        return dict(schema_version=SCHEMA,kind='RECOVERY_SEAL_V1',pack=_pack(number),bytes=len(raw),sha256=digest(raw),
            valid_bytes=offset,prefix_sha256=digest(raw[:offset]),tail_sha256=digest(raw[offset:]),
            last_sequence=state['sequence'],tip=state['tip'],previous_seal=previous_seal,
            skipped_until=max(state['sequence'],self._pending_skip or 0)+1)

    def _verify_all(self,*,_committed_prefix_only=False):
        expected=self.state; self.state=_initial(); previous_seal=ZERO
        self._pending_skip=None
        originals={};capture_files={}
        names={'head.json'}
        for number in range(1,expected['pack']+1):
            self.deadline()
            name=_pack(number); names.add(name); raw=read_local(self.root,name,MAX_PACK_BYTES)
            seal_raw=seal=None;limit=len(raw)
            if number<expected['pack']:
                seal_name=f'{number:06d}.seal.json';names.add(seal_name)
                seal_raw=read_local(self.root,seal_name,4096);seal=decode(seal_raw)
                if type(seal) is not dict:_fail('SEAL_INVALID')
                if type(seal) is dict and seal.get('kind')=='RECOVERY_SEAL_V1':
                    limit=seal.get('valid_bytes')
                    if type(limit) is not int or not 0<=limit<len(raw):_fail('RECOVERY_SEAL_INVALID')
            elif _committed_prefix_only:
                limit=expected['offset']
                if limit>len(raw):_fail('COMMITTED_PREFIX_MISSING')
            offset=0; self.state.update(pack=number,offset=0,pack_frames=0,active_request_budget_upper=0)
            while offset<limit:
                self.deadline()
                if limit-offset<8: _fail('RECOVERY_REQUIRED')
                a,b=struct.unpack('!II',raw[offset:offset+8]); size=8+a+b
                if size>MAX_PACK_BYTES or offset+size>limit: _fail('RECOVERY_REQUIRED')
                frame=raw[offset:offset+size]; metadata,payload=self._decode_frame(frame)
                pointer=dict(pack=name,offset=offset,size=size,sha256=digest(frame))
                if metadata['reference'] is not None:
                    # This cache contains only originals whose actual payload
                    # and frame hash were verified earlier in THIS linear scan.
                    # No persisted head/cache assertion supplies this proof.
                    original=originals.get(metadata['raw_hash'])
                    if original!=(metadata['reference'],metadata['bytes']):_fail('REFERENCE_INVALID')
                token=metadata['capture_id'];kind=metadata['kind'];value=None
                if kind=='RESERVE':capture_files[token]={}
                elif kind=='FILE':
                    files=capture_files.get(token)
                    if files is None or metadata['path'] in files or len(files)>=1024:_fail('CAPTURE_INDEX_INVALID')
                    files[metadata['path']]=pointer
                elif kind=='COMMIT':
                    value=decode(payload)
                    if type(value) is not dict or type(value.get('files')) is not dict:_fail('CAPTURE_INDEX_INVALID')
                    for stored in value['files'].values():_pointer_shape(stored)
                    if value['files']!=capture_files.pop(token,None):_fail('CAPTURE_INDEX_INVALID')
                elif kind=='RECOVERY':
                    value=decode(payload)
                    if type(value) is not dict or type(value.get('retired')) is not dict:_fail('RECOVERY_RECORD_INVALID')
                    for retired in value.get('retired',{}):capture_files.pop(retired,None)
                self._apply(metadata,payload,pointer,_decoded=value); offset+=size
                if kind=='FILE' and metadata['reference'] is None and metadata['path'].endswith('-response.bin'):
                    originals[metadata['raw_hash']]=(pointer,metadata['bytes'])
                    if len(originals)>MAX_CACHE:
                        originals={key:item for key,item in originals.items() if key in self.state['cache']}
            if number<expected['pack']:
                if seal.get('kind')=='RECOVERY_SEAL_V1':
                    if seal!=self._recovery_seal(number,raw,previous_seal=previous_seal):_fail('RECOVERY_SEAL_INVALID')
                    self.state['physical_bytes']+=len(raw)-limit
                    self.state['request_accounting']='INCOMPLETE';self._pending_skip=seal['skipped_until']
                elif seal!=dict(schema_version=SCHEMA,pack=name,bytes=len(raw),sha256=digest(raw),
                        last_sequence=self.state['sequence'],tip=self.state['tip'],previous_seal=previous_seal):_fail('SEAL_INVALID')
                previous_seal=digest(seal_raw)
                self.state['physical_bytes']+=len(seal_raw); self.state['sealed_tip']=previous_seal
        if (not _committed_prefix_only and {p.name for p in self.root.iterdir()}!=names) or self.state!=expected:
            _fail('RECOVERY_REQUIRED')

    def _seal(self):
        state=self.state
        if state['pack']>=MAX_SEGMENTS: _fail('FILE_CAPACITY')
        self._close_writer()
        name=_pack(state['pack']); raw=read_local(self.root,name,MAX_PACK_BYTES)
        seal=canonical(dict(schema_version=SCHEMA,pack=name,bytes=len(raw),sha256=digest(raw),
            last_sequence=state['sequence'],tip=state['tip'],previous_seal=state['sealed_tip'])).encode()
        write_private_new(self.root/f"{state['pack']:06d}.seal.json",seal)
        state['sealed_tip']=digest(seal); state['physical_bytes']+=len(seal)
        state.update(pack=state['pack']+1,offset=0,pack_frames=0,active_request_budget_upper=0)
        write_private_new(self.root/_pack(state['pack']),b''); self._save()

    def _append(self,kind,token,path,raw):
        state=self.state
        if type(raw) is not bytes or len(raw)>MAX_RAW: _fail('RAW_LIMIT')
        if self._pending_skip is not None and kind!='RECOVERY':_fail('RECOVERY_REQUIRED')
        if kind=='RESERVE' and state['active_request_budget_upper']+decode(raw)['maximum_requests']>MAX_ACTIVE_REQUESTS:
            self._seal()
        reference=state['cache'].get(digest(raw)) if kind=='FILE' and path.endswith('-response.bin') else None
        sequence=max(state['sequence'],self._pending_skip or 0)+1 if kind=='RECOVERY' else state['sequence']+1
        metadata=dict(sequence=sequence,previous=state['tip'],kind=kind,capture_id=token,
            path=path,bytes=len(raw),raw_hash=digest(raw),reference=reference)
        header=canonical(metadata).encode(); compressed=b'' if reference is not None else zlib.compress(raw,1)
        frame=struct.pack('!II',len(header),len(compressed))+header+compressed
        if len(header)>MAX_HEADER_BYTES or len(frame)>MAX_PACK_BYTES: _fail('FRAME_LIMIT')
        if state['offset']+len(frame)>MAX_PACK_BYTES or state['pack_frames']>=MAX_FRAMES:
            self._seal()
        pointer=dict(pack=_pack(state['pack']),offset=state['offset'],size=len(frame),sha256=digest(frame))
        path=self.root/pointer['pack']
        if self._write_enabled:
            if self._writer is None or self._writer[0]!=pointer['pack']:
                self._close_writer();require_private(path)
                from application.platform.product_backup import _opened_source
                context=_opened_source(path,_archive_writer=True)
                self._writer=(pointer['pack'],context,context.__enter__())
            stream=self._writer[2];stream.seek(0,os.SEEK_END)
            if stream.tell()!=pointer['offset']:_fail('RECOVERY_REQUIRED')
            if stream.write(frame)!=len(frame):raise OSError('PUBLIC_ARCHIVE_PARTIAL_WRITE')
            stream.flush()
            if kind!='FILE':os.fsync(stream.fileno())
        else:
            require_private(path)
            with _filesystem_path(path).open('ab') as stream:
                if stream.write(frame)!=len(frame):raise OSError('PUBLIC_ARCHIVE_PARTIAL_WRITE')
                stream.flush(); os.fsync(stream.fileno())
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
                +(state['pack_frames']+reserved_frames+maximum_files+2)//MAX_FRAMES
                +(state['active_request_budget_upper']+maximum_requests-1)//MAX_ACTIVE_REQUESTS)
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
        with self._locked(),self._writing():
            self._reload(); reservation=self.state['pending'].get(capture_id)
            if (reservation is None or requests>reservation['maximum_requests'] or len(files)>reservation['maximum_files']
                    or sum(len(raw)+max(1024,len(raw)//1000+64) for raw in files.values())+4096>reservation['maximum_bytes']):
                _fail('RESERVATION_EXCEEDED')
            index={}
            for relative,raw in sorted(files.items()):
                pointer=self._append('FILE',capture_id,relative,raw)
                index[relative]=pointer
            value=dict(files=index,requests=requests,responses=responses,complete=complete)
            pointer=self._append('COMMIT',capture_id,'',canonical(value).encode())
            self._close_writer()
            if self.read_capture(pointer)!=files: _fail('CAPTURE_READBACK_INVALID')
            return pointer

    def read_capture(self,pointer):
        with self._locked(),self._reading():
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
        if not facts:_fail('EMPTY_CAPTURE_FORBIDDEN')
        with self._locked(),self._writing():
            self._reload(); reservation=self.state['pending'].get(capture_id)
            if (reservation is None or requests>reservation['maximum_requests'] or len(facts)>reservation['maximum_files']
                    or sum(row['bytes']+max(1024,row['bytes']//1000+64) for row in facts.values())+4096>reservation['maximum_bytes']):
                _fail('RESERVATION_EXCEEDED')
            index={}
            for relative,fact in sorted(facts.items()):
                raw=read_local(directory,relative,MAX_RAW)
                if len(raw)!=fact['bytes'] or digest(raw)!=fact['sha256']: _fail('STAGING_READBACK_INVALID')
                pointer=self._append('FILE',capture_id,relative,raw)
                index[relative]=pointer
            value=dict(files=index,requests=requests,responses=responses,complete=complete)
            pointer=self._append('COMMIT',capture_id,'',canonical(value).encode())
            self._close_writer()
            if self.capture_inventory(pointer)!=facts: _fail('CAPTURE_READBACK_INVALID')
            return pointer

    def capture_inventory(self,pointer):
        with self._locked(),self._reading():
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
                'captures','request_budget_upper','active_request_budget_upper')},'request_accounting':accounting,
                'provider_requests':state['provider_requests'] if accounting=='COMPLETE' else None,
                'provider_responses':state['provider_responses'] if accounting=='COMPLETE' else None,
                'completed_capture_requests':state['provider_requests'],'completed_capture_responses':state['provider_responses'],
                'sealed_segments':state['pack']-1,'pending_reservations':len(state['pending']),
                'reserved_bytes':sum(item['maximum_bytes'] for item in state['pending'].values())}
