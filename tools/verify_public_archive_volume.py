"""Local storage-volume FIXTURE, never source health or Paper/elapsed proof.

Acceleration changes ONLY producer IO frequency: complete normal-format frames,
reservations, counters, budgets and seals are emitted, but head/fsync commit at
pack boundaries instead of each request. The unmodified production constructor
then verifies every original payload, reference, COMMIT index, counter and seal.
Per-request durability is covered separately by normal API/fault tests. No API.
"""
import argparse
import ctypes
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import time
import uuid
import zlib

from application.datasets.catalog import canonical,decode,digest,read_local
from application.paper import capture_archive as storage
from application.platform.private_files import create_private_directory,require_private,_filesystem_path


class VolumeProducer(storage.PublicCaptureArchive):
    """Test-only altered IO cadence; never imported by the product."""
    def __init__(self,root):
        self.accelerated=False;self.volume_stream=None
        super().__init__(root)
        self.accelerated=True

    def _reload(self):
        if not self.accelerated:super()._reload()

    def _save(self):
        if not self.accelerated:super()._save()

    def flush_volume(self):
        if self.volume_stream is not None:
            self.volume_stream.flush();os.fsync(self.volume_stream.fileno())
            self.volume_stream.close();self.volume_stream=None
        super()._save()

    def _seal(self):
        self.flush_volume();super()._seal();super()._save()

    def _append(self,kind,token,path,raw):
        state=self.state
        if kind=='RESERVE' and state['active_request_budget_upper']+decode(raw)['maximum_requests']>storage.MAX_ACTIVE_REQUESTS:
            self._seal()
        reference=state['cache'].get(digest(raw)) if kind=='FILE' and path.endswith('-response.bin') else None
        metadata=dict(sequence=state['sequence']+1,previous=state['tip'],kind=kind,capture_id=token,
            path=path,bytes=len(raw),raw_hash=digest(raw),reference=reference)
        header=canonical(metadata).encode();compressed=b'' if reference is not None else zlib.compress(raw,1)
        frame=struct.pack('!II',len(header),len(compressed))+header+compressed
        if len(header)>storage.MAX_HEADER_BYTES or len(frame)>storage.MAX_PACK_BYTES:raise ValueError('FIXTURE_FRAME_LIMIT')
        if state['offset']+len(frame)>storage.MAX_PACK_BYTES or state['pack_frames']>=storage.MAX_FRAMES:self._seal()
        pointer=dict(pack=storage._pack(state['pack']),offset=state['offset'],size=len(frame),sha256=digest(frame))
        if self.volume_stream is None:
            target=self.root/pointer['pack'];require_private(target)
            self.volume_stream=_filesystem_path(target).open('ab',buffering=1024*1024)
        if self.volume_stream.write(frame)!=len(frame):raise OSError('FIXTURE_SHORT_WRITE')
        self._apply(metadata,raw,pointer)
        return pointer


def peak_memory():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(name,ctypes.c_size_t) for name in
            ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
             'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    value=Counters();value.cb=ctypes.sizeof(value)
    current=ctypes.windll.kernel32.GetCurrentProcess
    current.restype=ctypes.c_void_p
    get=ctypes.windll.psapi.GetProcessMemoryInfo
    get.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
    if not get(current(),ctypes.byref(value),value.cb):raise ctypes.WinError()
    return dict(peak_working_set_bytes=value.PeakWorkingSetSize,working_set_bytes=value.WorkingSetSize,
        peak_pagefile_bytes=value.PeakPagefileUsage)


def run(output,probe,ticks):
    if ticks<1 or ticks>518400:raise ValueError('Bounded 30day storage protocol required')
    if output.exists():raise ValueError('Fresh isolated volume fixture directory required')
    create_private_directory(output)
    quote=read_local(probe,'ticker/requests/001-response.bin',2*1024**2)
    funding=read_local(probe,'funding/requests/001-response.bin',2*1024**2)
    source_hashes={p:digest((Path(__file__).parents[1]/p).read_bytes()) for p in
        ('tools/verify_public_archive_volume.py','src/application/paper/capture_archive.py')}
    started=time.perf_counter();cpu=time.process_time();archive=VolumeProducer(output/'archive')
    earliest=last=None;logical=0;extra=0
    base=datetime(2026,10,21,tzinfo=timezone.utc)
    def capture(kind,number,raw,at,maximum):
        nonlocal earliest,last,logical
        token=str(uuid.uuid4())
        archive.reserve(token,kind=kind,maximum_requests=maximum,
            maximum_bytes=(400 if kind=='market' else 16)*1024**2,maximum_files=670 if kind=='market' else 64)
        receipt=dict(protocol='ACCELERATED_STORAGE_FIXTURE',sequence=number,observed_at=at,
            method='GET',provider='CONTROLLED_NO_NETWORK',response_hash=digest(raw),response_bytes=len(raw))
        files={'request.json':canonical(dict(kind=kind,at=at,protocol='CONTROLLED_VOLUME')).encode(),
            'requests/001-attempt.json':canonical(dict(receipt,state='ATTEMPTED')).encode(),
            'requests/001-response.bin':raw,'requests/001-result.json':canonical(dict(receipt,status=200)).encode(),
            'acquisition.json':canonical(dict(requests=1,responses=1,accounting='COMPLETE',protocol='FIXTURE')).encode()}
        index={name:archive._append('FILE',token,name,payload) for name,payload in sorted(files.items())}
        last=archive._append('COMMIT',token,'',canonical(dict(files=index,requests=1,responses=1,complete=True)).encode())
        if earliest is None:earliest=last
        logical+=1
    try:
        # The human authorized only a process-lifetime keep-awake request.
        if not ctypes.windll.kernel32.SetThreadExecutionState(0x80000001):raise ctypes.WinError()
        with archive._locked():
            for index in range(ticks):
                at=(base+timedelta(seconds=index*5)).isoformat().replace('+00:00','Z')
                value=decode(quote);value['data'][0]['ts']=str(int((base+timedelta(seconds=index*5)).timestamp()*1000))
                capture('market',index,canonical(value).encode(),at,165)
                # Static funding payload is a declared controlled assumption,
                # not evidence of an unchanged live public response.
                capture('funding',index,funding,at,16)
                if index%2880==0:
                    capture('market',index,b'CONTROLLED_NEW_4H_CANDLE_'+str(index).encode(),at,165);extra+=1
                if index%17280==0:
                    capture('preflight',index,funding,at,16);extra+=1
                if index%16384==0:
                    print(json.dumps(dict(ticks_completed=index,logical_requests=logical,pack=archive.state['pack'],
                        wall_seconds=time.perf_counter()-started,**peak_memory())),flush=True)
            archive.flush_volume()
        produced=archive.summary();generation_wall=time.perf_counter()-started
        verify_start=time.perf_counter()
        restored=storage.PublicCaptureArchive(archive.root)
        assert restored.summary()==produced
        assert restored.summary()['provider_requests']==logical
        restored.read_capture(earliest);restored.read_capture(last)
        files=sorted(archive.root.iterdir());physical=sum(path.stat().st_size for path in files)
        result=dict(status='CONTROLLED_STORAGE_VOLUME_VERIFIED_NOT_ORDINARY_QUALIFICATION',
            protocol='ACCELERATED_PRODUCER_PACK_FSYNC;UNMODIFIED_COMPLETE_PRODUCTION_READER',
            ticks=ticks,logical_seconds=ticks*5,logical_requests=logical,extra_candle_preflight_requests=extra,
            actual_provider_requests=0,actual_provider_responses=0,source_hashes=source_hashes,
            raw_template_hashes=dict(ticker=digest(quote),funding=digest(funding)),
            static_funding_payload_assumption=True,archive=produced,actual_files=len(files),
            actual_physical_bytes_including_head=physical,generation_wall_seconds=generation_wall,
            verification_wall_seconds=time.perf_counter()-verify_start,
            total_wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time()-cpu,**peak_memory(),
            limitations=['Accelerated producer does not establish normal per-request durability or steady runtime IO cost',
                'No financial admission, strategy evaluation, DB growth, native isolation or elapsed observation credit',
                'Protocol worst-case variable/maximal response payloads must refuse before capacity, not promise30days'])
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result),flush=True)
    finally:
        archive.flush_volume()
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--probe',type=Path,required=True);parser.add_argument('--ticks',type=int,default=518400)
    args=parser.parse_args();run(args.output.absolute(),args.probe.absolute(),args.ticks)
