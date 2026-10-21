"""Independent settled-public acquisition and bounded actual-owner health.

Financial admission consumes a private native-owner projection. E4 allocation
consumes the separately verified original bytes, not that projection or a PASS.
"""
from datetime import datetime, timedelta, timezone
import os
import re
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

from application.config import load_config
from application.datasets.catalog import canonical,decode,digest,read_local,utc,z
from application.platform.private_files import require_private,write_private_atomic
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.runtime_identity import read_runtime_identity
from application.platform.supervision import config_hash
from execution.funding import public_recorded_funding_model
from execution.public_recorded_funding import FUNDING_MODEL,STEP,_floor
from storage.paper_selection import open_paper_selections
from .funding_capture import validate_request,capture_public_funding,observe_funding_capture
from .public_feed import _guard,_private_directory,_uuid,_archive_for
from .release_observation import owner_projection

ROOT='public-funding-observations'
REFRESH_SECONDS=5
DEADLINE=125
HEALTH_SCHEMA='r7-public-paper-funding-health-v0.1'
_unreaped=[]


class FundingAttemptIncomplete(ValueError):
    def __init__(self,reaped):
        self.reaped=reaped; super().__init__('Public funding accounting incomplete')


def _funding_guard(config_path,request):
    request,_=validate_request(request); subject=request['subject']
    config,_=_guard(config_path,subject['runtime_token'],subject['config_hash'])
    with open_paper_selections(config.database_path) as reader: selection=reader.current()
    if selection is None or digest(selection.canonical_json.encode())!=subject['selection_hash']:
        raise ValueError('Actual unchanged ordinary Paper selection required')
    record=selection.as_dict(); simulation=record['owner']['simulation_policy']
    if (simulation['schema_version']!='r7-paper-simulation-policy-v0.5'
            or simulation['funding_model']!=FUNDING_MODEL
            or record['envelope']['product_config_hash']!=config_hash(config)):
        raise ValueError('Actual selected registered funding model required')
    return config,selection


def funding_request(config,selection,runtime_token,*,coverage_start=None,now=None):
    simulation=selection.as_dict()['owner']['simulation_policy']
    if simulation.get('schema_version')!='r7-paper-simulation-policy-v0.5' or simulation.get('funding_model')!=FUNDING_MODEL:
        raise ValueError('Explicit selected recorded funding simulation required')
    now=datetime.now(timezone.utc) if now is None else now
    request=dict(schema_version='r7-public-paper-funding-request-v0.1',subject=dict(namespace='LOCAL_RESEARCH',
        runtime_token=_uuid(runtime_token),config_hash=config_hash(config),
        selection_hash=digest(selection.canonical_json.encode()),funding_model=FUNDING_MODEL),
        coverage_start=z(_floor(now)-STEP if coverage_start is None else coverage_start))
    return validate_request(request)[0]


def run_funding_acquire(config_path,token,attempt_id,request_hash,expected_config_hash,selection_hash):
    from .capture_activity import capture_lease
    config=load_config(config_path)
    with capture_lease(config,'funding'):
        return _run_funding_acquire(config_path,token,attempt_id,request_hash,expected_config_hash,selection_hash)


def _run_funding_acquire(config_path,token,attempt_id,request_hash,expected_config_hash,selection_hash):
    _uuid(token); _uuid(attempt_id)
    config=load_config(config_path); root=config.local_data_root/ROOT/token/attempt_id
    require_private(root,directory=True); raw=read_local(root,'request.json',4096)
    request,_=validate_request(decode(raw))
    if (digest(raw)!=request_hash or request['subject']['runtime_token']!=token
            or request['subject']['config_hash']!=expected_config_hash or request['subject']['selection_hash']!=selection_hash):
        raise ValueError('Exact owning public funding request required')
    _funding_guard(config_path,request)
    result=capture_public_funding(root/'capture',request)
    _funding_guard(config_path,request)
    return dict(request_hash=request_hash,attempt_id=attempt_id,runtime_token=token,result=result)


def check_funding_once(config_path,request,cancel):
    from .capture_activity import capture_activity
    config=load_config(config_path)
    with capture_activity(config.local_data_root):
        return _check_funding_once(config_path,request,cancel)


def _check_funding_once(config_path,request,cancel):
    """One reaped child; shared pre-I/O archive reservation and byte readback."""
    request,_=validate_request(request); config,selection=_funding_guard(config_path,request)
    subject=request['subject']; token=subject['runtime_token']; config_path=Path(config_path)
    archive=_archive_for(config); attempt_id=str(uuid.uuid4())
    archive.reserve(attempt_id,kind='funding',maximum_requests=16,maximum_bytes=16*1024**2,maximum_files=64)
    base=config.local_data_root/ROOT; _private_directory(base)
    owner=base/token; _private_directory(owner); root=owner/attempt_id; _private_directory(root)
    raw=canonical(request).encode(); write_private_atomic(root/'request.json',raw); request_hash=digest(raw)
    prefix=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-m','application']
    argv=prefix+['_paper-funding-acquire','--config',str(config_path),'--runtime-token',token,
        '--attempt-id',attempt_id,'--request-hash',request_hash,'--expected-config-hash',subject['config_hash'],
        '--selection-hash',subject['selection_hash']]
    owned=None; result=None; error=None; started=time.monotonic()
    try:
        if cancel.is_set():raise ValueError('Public funding canceled before dispatch')
        owned=spawn_owned(argv,cwd=config_path.parent,limits=ResourceLimits(DEADLINE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        descriptor=owned.process.stdout.fileno(); os.set_blocking(descriptor,False); chunks=[]; size=0
        while True:
            if cancel.is_set() or time.monotonic()-started>=DEADLINE:raise FundingAttemptIncomplete(True)
            try: chunk=os.read(descriptor,min(65536,65537-size))
            except BlockingIOError: cancel.wait(.02); continue
            if not chunk:break
            chunks.append(chunk); size+=len(chunk)
            if size>65536:raise FundingAttemptIncomplete(True)
        code=owned.wait(timeout=2)
        if code!=0 or not owned.termination_report.reaped:raise FundingAttemptIncomplete(owned.termination_report.reaped)
        envelope=decode(b''.join(chunks))
        if (type(envelope) is not dict or set(envelope)!={'request_hash','attempt_id','runtime_token','result'}
                or envelope['request_hash']!=request_hash or envelope['attempt_id']!=attempt_id or envelope['runtime_token']!=token):
            raise FundingAttemptIncomplete(True)
        result=envelope['result']; _funding_guard(config_path,request)
    except (ValueError,RuntimeError,OSError,TypeError,KeyError,subprocess.SubprocessError) as caught:
        error=caught
    finally:
        if owned is not None:
            reaped=False
            try: reaped=terminate_owned(owned,deadline_seconds=2).reaped
            except (OSError,RuntimeError,subprocess.SubprocessError):pass
            finally: owned.process.stdout.close()
            if not reaped:
                _unreaped.append(owned); raise FundingAttemptIncomplete(False)
    files=archive.directory_files(root)
    complete=(error is None and type(result) is dict and result.get('request_accounting')=='COMPLETE'
        and type(result.get('provider_requests')) is int and type(result.get('provider_responses')) is int
        and 0<=result['provider_responses']<=result['provider_requests']<=16
        and decode(files.get('capture/acquisition.json',b'null'))==result)
    pointer=archive.commit(attempt_id,files,requests=result['provider_requests'] if complete else 0,
        responses=result['provider_responses'] if complete else 0,complete=complete)
    archive.release_directory(pointer,root,staging_root=base)
    if not complete:raise FundingAttemptIncomplete(True) from None
    return result,pointer,{key.removeprefix('capture/'):raw for key,raw in files.items() if key.startswith('capture/')}


def publish_health(config_path,request,result,observed,pointer,*,state,reason):
    config,selection=_funding_guard(config_path,request)
    identity=owner_projection(read_runtime_identity(config).identity)
    body=decode(observed.canonical_json) if observed is not None else None
    value=dict(schema_version=HEALTH_SCHEMA,subject=request['subject'],runtime=identity,
        selection_generation=selection.generation,state=state,reason_code=reason,
        snapshot_hash=None if observed is None else observed.snapshot_hash,
        observed_at=None if observed is None else observed.observed_at,
        complete_through=None if observed is None else observed.complete_through,
        coverage_start=None if observed is None else observed.coverage_start,
        event_count=0 if body is None else len(body['events']),archive_capture=pointer,
        provider_requests=None if result is None else result['provider_requests'],
        provider_responses=None if result is None else result['provider_responses'])
    base=config.local_data_root/ROOT; _private_directory(base)
    owner=base/request['subject']['runtime_token']; _private_directory(owner)
    _funding_guard(config_path,request)
    write_private_atomic(owner/'current.json',canonical(value).encode())


def current_funding_health(config,selection,runtime_identity,*,now):
    """Bounded private native-owner projection; never a financial allocation."""
    before=owner_projection(read_runtime_identity(config).identity)
    expected=funding_request(config,selection,before['process_generation_id'],now=now)['subject']
    folder=config.local_data_root/ROOT/before['process_generation_id']
    require_private(folder,directory=True); require_private(folder/'current.json')
    value=decode(read_local(folder,'current.json',16384))
    after=owner_projection(read_runtime_identity(config).identity)
    fields={'schema_version','subject','runtime','selection_generation','state','reason_code','snapshot_hash',
        'observed_at','complete_through','coverage_start','event_count','archive_capture','provider_requests','provider_responses'}
    if (before!=after or after!=owner_projection(runtime_identity) or type(value) is not dict or set(value)!=fields
            or value['schema_version']!=HEALTH_SCHEMA or value['subject']!=expected or value['runtime']!=after
            or type(value['selection_generation']) is not int or value['selection_generation']!=selection.generation
            or before['config_hash']!=config_hash(config) or before['product_instance_id']!=config.product_instance_id):
        raise ValueError('Current owning funding observation required')
    healthy=False
    if value['state']=='PUBLIC_FUNDING_ACQUIRED' and value['observed_at'] is not None:
        observed=utc(value['observed_at']); through=utc(value['complete_through']); start=utc(value['coverage_start'])
        pointer=value['archive_capture']
        valid_pointer=(type(pointer) is dict and set(pointer)=={'pack','offset','size','sha256'}
            and type(pointer['pack']) is str and re.fullmatch(r'[0-9]{6}\.pack',pointer['pack']) is not None
            and type(pointer['offset']) is int and pointer['offset']>=0
            and type(pointer['size']) is int and 8<=pointer['size']<=16*1024**2
            and type(pointer['sha256']) is str and re.fullmatch(r'sha256:[0-9a-f]{64}',pointer['sha256']) is not None)
        healthy=(0<=(now-observed).total_seconds()<=60 and through==_floor(now) and start<=through-STEP
            and start==_floor(start) and (through-start)<=timedelta(days=89)
            and type(value['event_count']) is int and 2<=value['event_count']<=1000
            and value['event_count']==(through-start)//STEP+1 and valid_pointer
            and type(value['snapshot_hash']) is str and re.fullmatch(r'[0-9a-f]{64}',value['snapshot_hash']) is not None
            and type(value['provider_requests']) is int and 1<=value['provider_requests']<=16
            and type(value['provider_responses']) is int and value['provider_responses']==value['provider_requests']
            and value['reason_code'] is None)
    return {**value,'healthy':healthy}


class PublicFundingFeed:
    def __init__(self,config,config_path,request,*,_clock=None):
        request,_=validate_request(request)
        if request['subject']['config_hash']!=config_hash(config):
            raise ValueError('Actual owning funding configuration required')
        self.config=config; self.path=Path(config_path); self.request=request
        self.clock=_clock or (lambda:datetime.now(timezone.utc)); self.model=public_recorded_funding_model()
        self.stop=threading.Event(); self.lock=threading.Lock(); self.thread=None; self.used=False
        self.pending=None; self.latest=None; self.state='WAITING_FOR_PUBLIC_SOURCE'; self.reason=None
        self.requests=self.responses=self.completed=self.incomplete=0; self.pointer=None

    def __enter__(self):
        if self.used:raise ValueError('Fresh public funding feed scope required')
        self.used=True; self.thread=threading.Thread(target=self._run,name='paper-public-funding',daemon=True)
        self.thread.start(); return self

    def update(self,coverage_start):
        with self.lock:
            request={**self.request,'coverage_start':z(coverage_start)}
            self.request=validate_request(request)[0]

    def take(self):
        with self.lock: result,self.pending=self.pending,None
        return result

    def current(self):
        with self.lock:return self.latest

    def summary(self):
        with self.lock:
            healthy=(self.state=='PUBLIC_FUNDING_ACQUIRED' and self.latest is not None
                and self.model.health(self.latest,now=self.clock()))
            return dict(funding_source='OKX_PUBLIC_REALIZED_RATE',funding_model=FUNDING_MODEL,
                acquisition_status=self.state,reason_code=self.reason,healthy=healthy,
                observed_at=None if self.latest is None else self.latest.observed_at,
                complete_through=None if self.latest is None else self.latest.complete_through,
                completed_batches=self.completed,incomplete_batches=self.incomplete,
                provider_requests=None if self.incomplete else self.requests,provider_responses=None if self.incomplete else self.responses,
                completed_batch_requests=self.requests,completed_batch_responses=self.responses,
                request_accounting='INCOMPLETE' if self.incomplete else 'COMPLETE',credentials='NONE',provider_mutation=0)

    def _run(self):
        while not self.stop.is_set():
            with self.lock:request=self.request
            result=None; observed=None; pointer=None; reaped=True
            try:
                result,pointer,files=check_funding_once(self.path,request,self.stop)
                with self.lock:
                    self.requests+=result['provider_requests']; self.responses+=result['provider_responses']; self.completed+=1
                if result['status'] in ('PUBLIC_FUNDING_ACQUIRED','PUBLIC_FUNDING_PENDING'):
                    observed=observe_funding_capture(None,model=self.model,subject=request['subject'],now=self.clock(),
                        _read=lambda name,limit:files[name])
                with self.lock:
                    self.state=result['status']; self.reason=result['reason_code']; self.pointer=pointer
                    self.latest=observed; self.pending=observed
            except FundingAttemptIncomplete as error:
                reaped=error.reaped
                with self.lock:self.incomplete+=1; self.state='PUBLIC_ACCOUNTING_INCOMPLETE'; self.reason='PUBLIC_FUNDING_ACCOUNTING_INCOMPLETE'; self.pending=None
            except (ValueError,RuntimeError,OSError,TypeError,KeyError):
                with self.lock:self.state='PUBLIC_FUNDING_DENIED'; self.reason='PUBLIC_FUNDING_CAPTURE_OR_OWNER_UNAVAILABLE'; self.pending=None
            try:publish_health(self.path,request,result,observed,pointer,state=self.state,reason=self.reason)
            except (ValueError,RuntimeError,OSError,TypeError,KeyError):
                with self.lock:self.state='PUBLIC_FUNDING_DENIED'; self.reason='PUBLIC_FUNDING_HEALTH_PUBLICATION_UNAVAILABLE'
            if not reaped:break
            self.stop.wait(REFRESH_SECONDS)

    def __exit__(self,*args):
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=4)
            if self.thread.is_alive():raise RuntimeError('Public funding stop/reap unconfirmed')
        with self.lock:self.pending=None; self.state='STOPPED'
