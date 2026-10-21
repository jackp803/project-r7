"""Public acquisition in a cancellable owned child, outside protection ticks."""
from dataclasses import asdict
from collections import OrderedDict
import os,subprocess,sys,threading,time,uuid
from pathlib import Path

from application.config import load_config,product_namespace
from application.cloud.safe_files import write_immutable
from application.datasets.catalog import canonical,decode,digest,read_local
from application.platform.private_files import create_private_directory,require_private
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.restoration import require_valid_restoration
from application.platform.runtime_identity import read_runtime_identity,RuntimeIdentityUnavailable
from application.platform.supervision import config_hash
from .public_market import load_market_profile
from .public_acquisition import acquire_batch,validate_subscriptions,MAX_OUTPUT

ROOT='public-market-observations'
DEADLINE=125
_unreaped=[]
_archives=OrderedDict()
_archives_lock=threading.Lock()


def _archive_for(config):
    # Verification/scans occur in acquisition threads, never protection ticks.
    from .capture_archive import PublicCaptureArchive,ROOT as archive_root
    root=config.local_data_root/archive_root
    with _archives_lock:
        result=_archives.pop(root,None)
        if result is None:result=PublicCaptureArchive(root)
        _archives[root]=result
        while len(_archives)>16:_archives.popitem(last=False)
        return result


class MarketAttemptIncomplete(ValueError):
    def __init__(self,reaped):self.reaped=reaped;super().__init__('Public request accounting incomplete')


def _uuid(value):
    if type(value) is not str or len(value)!=36:raise ValueError('Exact owning attempt token required')
    parsed=uuid.UUID(value)
    if parsed.version!=4 or str(parsed)!=value:raise ValueError('Exact owning attempt token required')
    return value


def _guard(config_path,token,expected_config_hash=None,selection_hash=None):
    _uuid(token);config=load_config(config_path)
    from application.entrypoints import _outside_installation
    _outside_installation(config.local_data_root)
    if (product_namespace(config)!='LOCAL_RESEARCH' or config.diagnostic_only or not config.paper_runtime_enabled
            or require_valid_restoration(config)['status']!='NOT_RESTORED'
            or expected_config_hash is not None and config_hash(config)!=expected_config_hash):
        raise ValueError('Current ordinary Paper public profile required')
    profile=load_market_profile(config)
    if profile is None or selection_hash is not None and digest(canonical(profile).encode())!=selection_hash:
        raise ValueError('Unchanged explicit public market selection required')
    try:identity=read_runtime_identity(config).identity
    except RuntimeIdentityUnavailable:raise ValueError('Current actual runtime owner required') from None
    if identity['process_generation_id']!=token:raise ValueError('Current actual runtime owner required')
    return config,profile


def run_market_acquire(config_path,token,attempt_id,request_hash,expected_config_hash,selection_hash):
    """Fixed private CLI target, no caller endpoint, price, code or financial verdict."""
    _uuid(attempt_id)
    config,profile=_guard(config_path,token,expected_config_hash,selection_hash)
    root=config.local_data_root/ROOT/token/attempt_id
    require_private(root,directory=True)
    raw=read_local(root,'request.json',262144)
    if digest(raw)!=request_hash:raise ValueError('Exact captured public subscription required')
    subscriptions=validate_subscriptions(decode(raw))
    if any(row.runtime_token!=token for row in subscriptions):raise ValueError('Exact owning public subscriptions required')
    result=acquire_batch(root/'capture',subscriptions)
    _guard(config_path,token,expected_config_hash,selection_hash)
    return dict(request_hash=request_hash,attempt_id=attempt_id,runtime_token=token,result=result)


def _private_directory(path):
    if path.exists():require_private(path,directory=True)
    else:create_private_directory(path)


def check_batch_once(config_path,token,subscriptions,cancel):
    config_path=Path(config_path)
    config,profile=_guard(config_path,token)
    expected=config_hash(config);selection=digest(canonical(profile).encode('utf-8'))
    subscriptions=validate_subscriptions([asdict(value) for value in subscriptions])
    if any(row.runtime_token!=token for row in subscriptions):raise ValueError('Actual owning subscriptions required')
    archive=_archive_for(config);attempt_id=str(uuid.uuid4())
    archive.reserve(attempt_id,kind='market',maximum_requests=165,maximum_bytes=400*1024**2,maximum_files=670)
    base=config.local_data_root/ROOT;_private_directory(base)
    owner=base/token;_private_directory(owner)
    root=owner/attempt_id;create_private_directory(root)
    raw=canonical([asdict(row) for row in subscriptions]).encode('utf-8');request_hash=digest(raw)
    if len(raw)>262144:raise ValueError('Bounded public subscription request required')
    write_immutable(root,'request.json',raw)
    prefix=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-m','application']
    argv=prefix+['_paper-market-acquire','--config',str(config_path),'--runtime-token',token,
        '--attempt-id',attempt_id,'--request-hash',request_hash,'--expected-config-hash',expected,'--selection-hash',selection]
    owned=None;started=time.monotonic();result=None;error=None
    try:
        if cancel.is_set():raise ValueError('Public acquisition canceled before dispatch')
        owned=spawn_owned(argv,cwd=config_path.parent,limits=ResourceLimits(DEADLINE),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        descriptor=owned.process.stdout.fileno();os.set_blocking(descriptor,False);chunks=[];size=0
        while True:
            if cancel.is_set() or time.monotonic()-started>=DEADLINE:raise MarketAttemptIncomplete(True)
            try:chunk=os.read(descriptor,min(65536,MAX_OUTPUT+1-size))
            except BlockingIOError:cancel.wait(.02);continue
            if not chunk:break
            chunks.append(chunk);size+=len(chunk)
            if size>MAX_OUTPUT:raise MarketAttemptIncomplete(True)
        code=owned.wait(timeout=2)
        if code!=0 or not owned.termination_report.reaped:raise MarketAttemptIncomplete(owned.termination_report.reaped)
        envelope=decode(b''.join(chunks))
        if (not isinstance(envelope,dict) or set(envelope)!={'request_hash','attempt_id','runtime_token','result'}
                or envelope['request_hash']!=request_hash or envelope['attempt_id']!=attempt_id or envelope['runtime_token']!=token):
            raise MarketAttemptIncomplete(True)
        _guard(config_path,token,expected,selection)
        result=envelope['result']
    except (ValueError,RuntimeError,OSError,TypeError,KeyError,subprocess.SubprocessError) as caught:
        error=caught
    finally:
        if owned is not None:
            reaped=False
            try:reaped=terminate_owned(owned,deadline_seconds=2).reaped
            except (OSError,RuntimeError,subprocess.SubprocessError):pass
            finally:owned.process.stdout.close()
            if not reaped:
                _unreaped.append(owned)
                raise MarketAttemptIncomplete(False)
    acquisition=decode(read_local(root,'capture/acquisition.json',MAX_OUTPUT)) if (root/'capture/acquisition.json').exists() else None
    complete=(error is None and isinstance(result,dict) and result.get('request_accounting')=='COMPLETE'
        and type(result.get('provider_requests')) is int and type(result.get('provider_responses')) is int
        and 0<=result['provider_responses']<=result['provider_requests']<=165
        and acquisition==result)
    pointer=archive.commit_directory(attempt_id,root,requests=result['provider_requests'] if complete else 0,
        responses=result['provider_responses'] if complete else 0,complete=complete)
    archive.release_directory(pointer,root,staging_root=base)
    if not complete:raise MarketAttemptIncomplete(True) from None
    return result


class PublicMarketFeed:
    """Only immutable descriptors/results cross threads; no owner DB connection."""
    def __init__(self,config,config_path,runtime_token):
        self.config,self.path,self.token=config,Path(config_path),_uuid(runtime_token)
        self.profile=load_market_profile(config)
        if self.profile is None:raise ValueError('Explicit public market selection required')
        self.stop=threading.Event();self.lock=threading.Lock();self.subscriptions=();self.pending=None
        self.thread=None;self.used=False;self.state='WAITING_FOR_ACCEPTED_RUN'
        self.requests=self.responses=self.completed=self.incomplete=0

    def __enter__(self):
        if self.used:raise ValueError('Fresh public feed scope required')
        self.used=True;self.thread=threading.Thread(target=self._run,name='paper-public-acquisition',daemon=True)
        self.thread.start();return self

    def update(self,subscriptions):
        # Main owner supplies actual metadata; no thread ever opens its journals.
        if subscriptions:subscriptions=validate_subscriptions([asdict(row) for row in subscriptions])
        with self.lock:self.subscriptions=tuple(subscriptions)

    def take(self):
        with self.lock:result,self.pending=self.pending,None
        return result

    def summary(self):
        with self.lock:return dict(market_source='OKX_PUBLIC_READ_ONLY',acquisition_status=self.state,
            completed_batches=self.completed,incomplete_batches=self.incomplete,
            provider_requests=None if self.incomplete else self.requests,provider_responses=None if self.incomplete else self.responses,
            completed_batch_requests=self.requests,completed_batch_responses=self.responses,
            request_accounting='INCOMPLETE' if self.incomplete else 'COMPLETE',
            credentials='NONE',provider_mutation=0)

    def _run(self):
        while not self.stop.is_set():
            with self.lock:subscriptions=self.subscriptions
            if not subscriptions:self.stop.wait(.05);continue
            try:
                result=check_batch_once(self.path,self.token,subscriptions,self.stop)
                if (not isinstance(result,dict) or result.get('request_accounting')!='COMPLETE'
                        or type(result.get('provider_requests')) is not int or type(result.get('provider_responses')) is not int
                        or not 0<=result['provider_responses']<=result['provider_requests']<=165):
                    raise MarketAttemptIncomplete(True)
                with self.lock:
                    self.requests+=result['provider_requests'];self.responses+=result['provider_responses'];self.completed+=1
                    self.state=result['status'];self.pending=result if result['status']=='PUBLIC_MARKET_ACQUIRED' else None
            except MarketAttemptIncomplete as error:
                with self.lock:self.incomplete+=1;self.state='PUBLIC_ACCOUNTING_INCOMPLETE';self.pending=None
                if not error.reaped:break
            except (ValueError,RuntimeError,OSError,TypeError,KeyError):
                with self.lock:self.state='PUBLIC_ACQUISITION_DENIED';self.pending=None
            self.stop.wait(self.profile['poll_interval_seconds'])

    def __exit__(self,*args):
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=4)
            if self.thread.is_alive():raise RuntimeError('Public acquisition stop/reap unconfirmed')
        with self.lock:self.pending=None
