"""Owned native verification outside protection; reads never start an owner.

The fixed time bounds are admission caps, not a qualification result. Finite
between-scan detection and same-user private storage are explicit limits.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from time import monotonic_ns
from time import sleep
from types import MappingProxyType
import uuid

from application.config import load_config,ProductConfig,product_namespace
from application.cloud.safe_files import _windows_read,_posix_read
from application.datasets.catalog import decode,read_local,digest as byte_digest
from application.platform.private_files import require_private,create_private_directory,write_private_atomic
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.runtime_identity import read_runtime_identity
from application.platform.supervision import config_hash,ProcessSupervisor
from registry.product_assessment import canonical,digest
from storage.paper_selection import OperationalSelection,open_paper_selections

DEADLINE_SECONDS=15
MAX_AGE_SECONDS=30
REFRESH_SECONDS=5
MAX_OUTPUT_BYTES=65536
SCHEMA='r7-native-paper-observation-v0.2'
CHILD_SCHEMA='r7-native-paper-observer-child-v0.2'
FACT_KEYS={'executable_revision','implementation_hash','build_hash','worktree','financial_authority',
    'distribution_profile','platform_id','capability_hash'}
OWNER_KEYS={'role','product_instance_id','pid','generation','process_generation_id','config_hash',
    'executable_revision','implementation_hash','build_hash','distribution_profile'}
OBS_KEYS={'schema_version','state','attempt_token','receipt_ref','runtime','selection_generation',
    'selection_hash','facts','started_ns','finished_ns'}
CHILD_KEYS={'schema_version','mode','facts','selection_generation','selection_hash','runtime'}
HASH=re.compile(r'sha256:[0-9a-f]{64}\Z')
RECEIPT=re.compile(r'qualification-[0-9a-f]{64}\Z')


def _facts(value):
    from .inventory import TARGETS
    if (not isinstance(value,dict) or set(value)!=FACT_KEYS
            or any(type(v) is not str for v in value.values())
            or not re.fullmatch('[0-9a-f]{40}',value['executable_revision'])
            or any(not HASH.fullmatch(value[key]) for key in ('implementation_hash','build_hash','capability_hash'))
            or value['worktree']!='UNAVAILABLE' or value['financial_authority']!='NONE'
            or value['distribution_profile']!='r7-native-distribution-v0.2' or value['platform_id'] not in TARGETS):
        raise ValueError('Exact measured native observation facts required')
    return dict(value)


def owner_projection(identity):
    value={key:identity.get(key) for key in OWNER_KEYS}
    try:token=uuid.UUID(value['process_generation_id'])
    except (ValueError,TypeError,AttributeError):raise ValueError('Actual runtime token required') from None
    if (value['role']!='runtime' or any(type(value[key]) is not int or not 1<=value[key]<2**63 for key in ('pid','generation'))
            or token.version!=4 or str(token)!=value['process_generation_id']
            or type(value['product_instance_id']) is not str or not value['product_instance_id']
            or type(value['config_hash']) is not str or not HASH.fullmatch(value['config_hash'])
            or type(value['executable_revision']) is not str or not re.fullmatch('[0-9a-f]{40}',value['executable_revision'])
            or any(type(value[key]) is not str or not HASH.fullmatch(value[key]) for key in ('implementation_hash','build_hash'))
            or value['distribution_profile']!='r7-native-distribution-v0.2'):
        raise ValueError('Exact independent native owner identity required')
    return value


def validate_observation(value,*,config,receipt_ref,runtime_identity,selection,now_ns):
    if (not isinstance(config,ProductConfig) or product_namespace(config)!='LOCAL_RESEARCH'
            or not isinstance(selection,OperationalSelection) or not isinstance(value,dict) or set(value)!=OBS_KEYS
            or value['schema_version']!=SCHEMA or value['state']!='CURRENT'
            or type(value['attempt_token']) is not str or not re.fullmatch('[0-9a-f]{32}',value['attempt_token'])
            or value['receipt_ref']!=receipt_ref or not RECEIPT.fullmatch(receipt_ref)
            or type(value['selection_generation']) is not int or value['selection_generation']!=selection.generation
            or value['selection_hash']!=digest(selection.canonical_json)
            or any(type(v) is not int or v<0 for v in (value['started_ns'],value['finished_ns'],now_ns))
            or not value['started_ns']<=value['finished_ns']<=now_ns
            or value['finished_ns']-value['started_ns']>DEADLINE_SECONDS*1_000_000_000
            or now_ns-value['started_ns']>MAX_AGE_SECONDS*1_000_000_000):
        raise ValueError('Current bounded exact owner observation required')
    actual=owner_projection(runtime_identity)
    if (not isinstance(value['runtime'],dict) or set(value['runtime'])!=OWNER_KEYS or value['runtime']!=actual
            or actual['config_hash']!=config_hash(config) or actual['product_instance_id']!=config.product_instance_id):
        raise ValueError('Observation belongs to another actual runtime/configuration')
    facts=_facts(value['facts'])
    if (any(actual[key]!=facts[key] for key in ('executable_revision','implementation_hash','build_hash','distribution_profile'))
            or selection.as_dict()['simulator_profile']['implementation_hash']!=facts['implementation_hash']):
        raise ValueError('Native subject and selected simulator changed')
    return MappingProxyType(facts)


class ControlReleaseObservation:
    """Read the actual generation's private artifact; no latest-pointer scan."""
    def __init__(self,config,receipt_ref):
        self.config,self.receipt_ref=config,receipt_ref

    def current(self,selection):
        before=owner_projection(read_runtime_identity(self.config).identity)
        folder=self.config.local_data_root/'paper-release-observations'/before['process_generation_id']
        path=folder/'current.json'
        require_private(folder,directory=True);require_private(path)
        value=decode((_windows_read if os.name=='nt' else _posix_read)(path,MAX_OUTPUT_BYTES,require_single_link=True))
        after=owner_projection(read_runtime_identity(self.config).identity)
        if before!=after:raise ValueError('Runtime changed during bounded observation read')
        return validate_observation(value,config=self.config,receipt_ref=self.receipt_ref,
            runtime_identity=after,selection=selection,now_ns=monotonic_ns())


class OwnerReleaseObservation:
    """One background verifier per actual runtime; protection reads memory only."""
    def __init__(self,config,config_path,receipt_ref,*,supervisor,selection):
        if (not isinstance(config,ProductConfig) or product_namespace(config)!='LOCAL_RESEARCH'
                or not isinstance(supervisor,ProcessSupervisor) or supervisor.role!='runtime'
                or not isinstance(selection,OperationalSelection) or type(receipt_ref) is not str
                or not RECEIPT.fullmatch(receipt_ref)):
            raise ValueError('Actual selected independent native observation owner required')
        self.config,self.config_path,self.receipt_ref=config,Path(config_path),receipt_ref
        self.supervisor,self.selection=supervisor,selection
        self.identity=owner_projection(supervisor.identity)
        if self.identity['config_hash']!=config_hash(config):raise ValueError('Observer owner configuration changed')
        self._lock=threading.Lock();self._publish_lock=threading.Lock()
        self.stop=threading.Event();self._document=None;self._used=False;self.thread=None
        root=config.local_data_root/'paper-release-observations'
        if not root.exists():create_private_directory(root)
        require_private(root,directory=True)
        folder=root/self.identity['process_generation_id'];create_private_directory(folder)
        self.path=folder/'current.json'

    def _empty(self,state):
        now=monotonic_ns()
        return dict(schema_version=SCHEMA,state=state,attempt_token=uuid.uuid4().hex,
            receipt_ref=self.receipt_ref,runtime=self.identity,selection_generation=self.selection.generation,
            selection_hash=digest(self.selection.canonical_json),facts=None,started_ns=now,finished_ns=now)

    def _publish(self,value):
        # This lock is private to publication/stop. Protective memory readers
        # never wait on artifact IO, process launch, wait or cleanup.
        with self._publish_lock:
            self.supervisor.require_current()
            if value['state']=='CURRENT' and self.stop.is_set():raise ValueError('Stopped observer cannot publish currentness')
            write_private_atomic(self.path,canonical(value).encode('utf-8'))
            self.supervisor.require_current()
            with self._lock:
                self._document=value if value['state']=='CURRENT' and not self.stop.is_set() else None

    def _run(self):
        while not self.stop.is_set():
            cycle=monotonic_ns()
            with self._lock:self._document=None
            try:
                self._publish(self._empty('PENDING'))
                child,started,finished=check_native_once(self.config_path,self.receipt_ref,mode='runtime',
                    runtime_token=self.identity['process_generation_id'])
                value=dict(schema_version=SCHEMA,state='CURRENT',attempt_token=uuid.uuid4().hex,
                    receipt_ref=self.receipt_ref,runtime=child['runtime'],selection_generation=child['selection_generation'],
                    selection_hash=child['selection_hash'],facts=child['facts'],started_ns=started,finished_ns=finished)
                validate_observation(value,config=self.config,receipt_ref=self.receipt_ref,
                    runtime_identity=self.identity,selection=self.selection,now_ns=monotonic_ns())
                self._publish(value)
            except (ValueError,RuntimeError,OSError,KeyError,TypeError,subprocess.SubprocessError):
                with self._lock:self._document=None
                try:self._publish(self._empty('DENIED'))
                except (ValueError,RuntimeError,OSError):break  # Lost owner; actual generation reads deny.
            self.stop.wait(max(.05,REFRESH_SECONDS-(monotonic_ns()-cycle)/1_000_000_000))

    def __enter__(self):
        if self._used:raise ValueError('Fresh observer scope required')
        self._used=True;self.supervisor.require_current()
        self.thread=threading.Thread(target=self._run,name='native-paper-release-observer',daemon=True)
        self.thread.start()
        return self

    def current(self,selection):
        # Durable generation/profile checks remain in the background publisher
        # and PaperOwnerWorker operation boundaries. This observation read must
        # not repeat them or wait for filesystem/SQLite while protection ticks.
        if (self.supervisor.failed or self.supervisor.stop.is_set()
                or owner_projection(self.supervisor.identity)!=self.identity):
            raise ValueError('Native observation owner memory fence lost')
        with self._lock:value=self._document
        if self.stop.is_set() or value is None:raise ValueError('Native observation pending, denied or stopped')
        return validate_observation(value,config=self.config,receipt_ref=self.receipt_ref,
            runtime_identity=self.identity,selection=selection,now_ns=monotonic_ns())

    def __exit__(self,*args):
        self.stop.set()
        with self._lock:self._document=None
        if self.thread is not None:
            self.thread.join(timeout=DEADLINE_SECONDS+6)
            if self.thread.is_alive():raise RuntimeError('Native observer stop/reap unconfirmed')
        try:self.supervisor.require_current()
        except (ValueError,RuntimeError):return
        self._publish(self._empty('DENIED'))


def check_native_once(config_path,receipt_ref,*,mode='software',runtime_token=None):
    """Fixed verifier with bounded output/owned timeout, outside protective ticks.

    OS process creation/IO may itself block. Late or unreaped completion denies
    admission; this does not claim a hard wall bound on arbitrary OS calls.
    """
    if not getattr(sys,'frozen',False):raise ValueError('Native observer executable required')
    config_path=Path(config_path)
    if (not config_path.is_absolute() or '..' in config_path.parts or type(receipt_ref) is not str
            or not RECEIPT.fullmatch(receipt_ref) or mode not in ('software','management','runtime')
            or (mode=='runtime')!=(runtime_token is not None)):
        raise ValueError('Fixed native observation inputs required')
    argv=[sys.executable,'_paper-release-observe','--config',str(config_path),'--receipt-ref',receipt_ref,'--mode',mode]
    if runtime_token is not None:argv.extend(['--runtime-token',str(runtime_token)])
    started=monotonic_ns();owned=None
    try:
        owned=spawn_owned(argv,cwd=config_path.parent,limits=ResourceLimits(DEADLINE_SECONDS),
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        # Never depend on EOF: failed cleanup can leave an inherited writer
        # open after the parent dies. Only this thread touches the raw FD.
        descriptor=owned.process.stdout.fileno()
        os.set_blocking(descriptor,False)
        chunks=[];size=0
        while True:
            if monotonic_ns()-started>=DEADLINE_SECONDS*1_000_000_000:
                raise ValueError('Native observation output deadline exceeded')
            try:chunk=os.read(descriptor,min(4096,MAX_OUTPUT_BYTES+1-size))
            except BlockingIOError:
                sleep(.01);continue
            if not chunk:break
            chunks.append(chunk);size+=len(chunk)
            if size>MAX_OUTPUT_BYTES:raise ValueError('Native observation output limit exceeded')
        raw=b''.join(chunks)
        code=owned.wait(timeout=DEADLINE_SECONDS+5)
        finished=monotonic_ns()
        if code!=0 or not owned.termination_report.reaped or finished-started>DEADLINE_SECONDS*1_000_000_000:
            raise ValueError('Native observation late, failed or unreaped')
        value=decode(raw)
        if (not isinstance(value,dict) or set(value)!=CHILD_KEYS or value['schema_version']!=CHILD_SCHEMA
                or value['mode']!=mode):raise ValueError('Fixed native observer result required')
        _facts(value['facts'])
        if mode=='runtime':
            runtime=owner_projection(value['runtime'])
            if (runtime['process_generation_id']!=runtime_token or type(value['selection_generation']) is not int
                    or not 1<=value['selection_generation']<=2147483647
                    or type(value['selection_hash']) is not str or not HASH.fullmatch(value['selection_hash'])):
                raise ValueError('Exact runtime observer result required')
        elif any(value[key] is not None for key in ('runtime','selection_generation','selection_hash')):
            raise ValueError('Software verification cannot manufacture runtime identity')
        return value,started,finished
    finally:
        if owned is not None:
            try:
                cleanup=terminate_owned(owned,deadline_seconds=5)
                if not cleanup.reaped:raise ValueError('Native observer tree not reaped')
            finally:owned.process.stdout.close()


def validate_selected_inputs(config,selection,facts):
    """Full sealed input verification in the child; no DB authoring or runtime."""
    from application.cloud.manifest import safe_component,parse_manifest,validate_package
    from application.cloud.protocol import PackageSnapshot
    from application.cloud.safe_files import read_bounded
    from .ordinary_setup import SOURCE_KEYS
    from .release import validate_operational_record
    from .owners import PaperOwnerSelection
    record=selection.as_dict();owner=validate_operational_record(config,record,implementation_hash=facts['implementation_hash'])
    source=record.get('source_subject')
    if (not isinstance(source,dict) or set(source)!=SOURCE_KEYS
            or source['schema_version']!='r7-local-paper-source-subject-v0.2'
            or type(source['manifest_hash']) is not str or not HASH.fullmatch(source['manifest_hash'])
            or not isinstance(source['input_refs'],dict) or set(source['input_refs'])!=
                {'simulation_policy_ref','risk_policy_ref','promotion_policy_ref'}
            or not isinstance(source['input_hashes'],dict) or set(source['input_hashes'])!=set(source['input_refs'])):
        raise ValueError('Complete protected sealed source subject required')
    selected=owner.as_dict();observed=dict(selected)
    for field,ref in source['input_refs'].items():
        raw=read_local(config.local_data_root,ref,MAX_OUTPUT_BYTES)
        if byte_digest(raw)!=source['input_hashes'][field]:raise ValueError('Selected Paper input changed')
        observed[field.removesuffix('_ref')]=decode(raw)
    if PaperOwnerSelection(**observed).selection_hash!=owner.selection_hash:raise ValueError('Selected owner policy changed')
    identifier=safe_component(source['submission_id'])
    root=config.local_data_root/'snapshots'/(identifier+'-'+source['manifest_hash'][7:])
    manifest=parse_manifest(read_bounded(root,'manifest.json',MAX_OUTPUT_BYTES))
    package=validate_package(PackageSnapshot(root,source['manifest_hash'],
        {spec.role:root/spec.relative_path for spec in manifest.payloads}))
    body=package.manifest.raw
    if (package.manifest.manifest_hash!=source['manifest_hash']
            or {key:body[key] for key in ('strategy_id','strategy_version')}!=
                {key:source['strategy'][key] for key in ('strategy_id','strategy_version')}
            or body['strategy_content_hash']!=source['strategy']['content_hash']
            or body.get('capability_snapshot_hash')!=facts['capability_hash']
            or {key:body[key] for key in ('intent_class','validity')}!=selected['submission_validity']):
        raise ValueError('Sealed Paper strategy/capability/validity changed')


def observe_native_subject(config_path,receipt_ref,*,mode='software',runtime_token=None):
    """Private CLI target: actual verification facts, never caller PASS/import."""
    if not getattr(sys,'frozen',False):raise ValueError('Native observer target required')
    if mode not in ('software','management','runtime') or (mode=='runtime')!=(runtime_token is not None):
        raise ValueError('Fixed observation mode required')
    config=load_config(config_path)
    from .release import NativePaperReleaseReader
    reader=NativePaperReleaseReader(config,receipt_ref=receipt_ref)
    runtime=None;selection=None
    if mode=='runtime':
        runtime=owner_projection(read_runtime_identity(config).identity)
        if runtime['process_generation_id']!=runtime_token:raise ValueError('Actual observer runtime changed')
    if mode=='management':
        reader.management_eligible();facts=reader._installed_facts()
    else:facts=reader.software_eligible()
    if mode=='runtime':
        with open_paper_selections(config.database_path) as ledger:selection=ledger.current()
        if selection is None or selection.as_dict()['source_subject']['qualification_receipt_ref']!=receipt_ref:
            raise ValueError('Exact selected observer receipt required')
        validate_selected_inputs(config,selection,facts)
        with open_paper_selections(config.database_path) as ledger:current=ledger.current()
        if current!=selection or owner_projection(read_runtime_identity(config).identity)!=runtime:
            raise ValueError('Observer selection/runtime changed during verification')
    if load_config(config_path)!=config:raise ValueError('Observer configuration changed during verification')
    return dict(schema_version=CHILD_SCHEMA,mode=mode,facts=_facts(facts),runtime=runtime,
        selection_generation=None if selection is None else selection.generation,
        selection_hash=None if selection is None else digest(selection.canonical_json))
