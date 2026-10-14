"""Bounded source boundary tests; synthetic facts never qualify a release."""
from contextlib import redirect_stderr,redirect_stdout
import importlib
import importlib.util
import io
import json
import os
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from application.config import ProductConfig
from application.platform import private_files
from application.platform.supervision import config_hash
from registry.product_assessment import canonical,digest
from storage.paper_selection import OperationalSelection
from tests.application import test_paper_release_selection as selections


class NativePaperObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='r7-observation-boundary-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.data=self.root/'private';private_files.create_private_directory(self.data)
        self.config=ProductConfig('r7-product-config-v0.2','observation-test',self.data,None,
            self.data/'canonical.sqlite3',diagnostic_only=False,paper_runtime_enabled=True)
        self.ref='qualification-'+'a'*64

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.release_observation'),
            'Native currentness must use a bounded owned observation outside protection')
        return importlib.import_module('application.paper.release_observation')

    def subject(self):
        from application.paper.release import operational_record
        helper=selections.PaperReleaseSelectionTests();helper.config=self.config
        record=operational_record(self.config,helper.owner(),account_ref='explicit-unit-account')
        selection=OperationalSelection(1,digest(canonical(record['envelope'])),canonical(record))
        facts=dict(executable_revision='b'*40,implementation_hash=record['simulator_profile']['implementation_hash'],
            build_hash='sha256:'+'c'*64,distribution_profile='r7-native-distribution-v0.2',
            worktree='UNAVAILABLE',financial_authority='NONE',platform_id='windows-11-x86_64',capability_hash='sha256:'+'d'*64)
        identity=dict(role='runtime',product_instance_id=self.config.product_instance_id,pid=123,generation=2,
            process_generation_id=str(uuid.uuid4()),config_hash=config_hash(self.config),
            **{key:facts[key] for key in ('executable_revision','implementation_hash','build_hash','distribution_profile')})
        return selection,facts,identity

    def document(self):
        selection,facts,identity=self.subject()
        value=dict(schema_version='r7-native-paper-observation-v0.2',state='CURRENT',attempt_token=uuid.uuid4().hex,
            receipt_ref=self.ref,runtime=identity,selection_generation=selection.generation,
            selection_hash=digest(selection.canonical_json),facts=facts,started_ns=10_000_000_000,finished_ns=11_000_000_000)
        return selection,facts,identity,value

    def test_current_observation_checks_exact_owner_selection_receipt_and_start_age(self):
        m=self.module();selection,facts,identity,value=self.document()
        measured=m.validate_observation(value,config=self.config,receipt_ref=self.ref,
            runtime_identity=identity,selection=selection,now_ns=12_000_000_000)
        self.assertEqual(dict(measured),facts)
        with self.assertRaises(TypeError):measured['build_hash']='changed'

    def test_pending_stale_future_late_wrong_owner_or_subject_cannot_establish_currentness(self):
        m=self.module();selection,_,identity,value=self.document()
        changes=({'state':'PENDING'},{'state':'DENIED'},{'started_ns':True},{'started_ns':13_000_000_000},
            {'finished_ns':26_000_000_000},{'receipt_ref':'qualification-'+'f'*64},
            {'selection_generation':2},{'selection_hash':'sha256:'+'f'*64},
            {'runtime':{**identity,'process_generation_id':str(uuid.uuid4())}},
            {'facts':{**value['facts'],'implementation_hash':'sha256:'+'e'*64}},
            {'facts':{**value['facts'],'capability_hash':'invalid'}},{'extra':'caller-PASS'})
        for change in changes:
            with self.subTest(change=change),self.assertRaises(ValueError):
                m.validate_observation({**value,**change},config=self.config,receipt_ref=self.ref,
                    runtime_identity=identity,selection=selection,now_ns=27_000_000_000)
        with self.assertRaises(ValueError):
            m.validate_observation(value,config=self.config,receipt_ref=self.ref,
                runtime_identity=identity,selection=selection,now_ns=41_000_000_000)

    def test_control_reader_uses_actual_generation_before_and_after_without_spawn_or_writes(self):
        m=self.module();selection,facts,identity,value=self.document()
        folder=self.data/'paper-release-observations';private_files.create_private_directory(folder)
        folder=folder/identity['process_generation_id'];private_files.create_private_directory(folder)
        private_files.write_private_new(folder/'current.json',canonical(value).encode())
        snapshot=SimpleNamespace(identity=identity)
        before={p.relative_to(self.data).as_posix():p.read_bytes() for p in self.data.rglob('*') if p.is_file()}
        with patch.object(m,'read_runtime_identity',return_value=snapshot) as reads,patch.object(m,'monotonic_ns',return_value=12_000_000_000),patch.object(m,'spawn_owned',side_effect=AssertionError('Read cannot launch')):
            self.assertEqual(dict(m.ControlReleaseObservation(self.config,self.ref).current(selection)),facts)
            self.assertEqual(reads.call_count,2)
        after={p.relative_to(self.data).as_posix():p.read_bytes() for p in self.data.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        with patch.object(m,'read_runtime_identity',side_effect=[snapshot,SimpleNamespace(identity={**identity,'generation':3})]),patch.object(m,'monotonic_ns',return_value=12_000_000_000),self.assertRaises(ValueError):
            m.ControlReleaseObservation(self.config,self.ref).current(selection)

    def test_atomic_private_publication_keeps_previous_document_visible_until_complete(self):
        self.assertTrue(hasattr(private_files,'write_private_atomic'),'Observation needs private atomic replacement')
        path=self.data/'current.json';private_files.write_private_new(path,b'old')
        def fault(stage):
            self.assertEqual(stage,'AFTER_PARTIAL_STAGE_WRITE')
            self.assertEqual(path.read_bytes(),b'old')
        private_files.write_private_atomic(path,b'new'*100,fault_hook=fault)
        self.assertEqual(path.read_bytes(),b'new'*100);private_files.require_private(path)
        with self.assertRaises(ValueError):private_files.write_private_atomic(path,b'x'*65537)

    def test_fixed_native_verifier_has_no_source_execution_or_caller_argv_override(self):
        m=self.module()
        with patch.object(m.sys,'frozen',False,create=True),patch.object(m,'spawn_owned') as spawn,self.assertRaises(ValueError):
            m.check_native_once(self.root/'product.json',self.ref)
        spawn.assert_not_called()
        with self.assertRaises(TypeError):m.check_native_once(self.root/'product.json',self.ref,argv=['arbitrary'])
        self.assertFalse(self.config.database_path.exists())

    def test_runner_rejects_oversize_nonzero_unreaped_timeout_and_late_result(self):
        m=self.module()
        for raw,code,reaped,elapsed in ((b'x'*65537,0,True,1),(b'{}',2,True,1),
                (b'{}',0,False,1),(b'{}',124,True,15),(b'{}',0,True,16)):
            read_fd,write_fd=os.pipe();stream=os.fdopen(read_fd,'rb',buffering=0)
            clock=[1_000_000_000]
            def write():
                try:
                    with os.fdopen(write_fd,'wb',buffering=0) as output:output.write(raw)
                except BrokenPipeError:pass
            writer=threading.Thread(target=write);writer.start()
            def wait(**kwargs):clock[0]+=int(elapsed*1_000_000_000);return code
            owned=SimpleNamespace(process=SimpleNamespace(stdout=stream),wait=wait,
                termination_report=SimpleNamespace(reaped=reaped))
            with self.subTest(code=code,reaped=reaped,elapsed=elapsed),patch.object(m.sys,'frozen',True,create=True),patch.object(m,'spawn_owned',return_value=owned),patch.object(m,'terminate_owned',return_value=owned.termination_report),patch.object(m,'monotonic_ns',side_effect=lambda:clock[0]),self.assertRaises(ValueError):
                m.check_native_once(self.root/'product.json',self.ref)
            writer.join(timeout=1);self.assertFalse(writer.is_alive());self.assertTrue(stream.closed)

    def test_real_pipe_retained_writer_failed_cleanup_cannot_block_deadline_rejection(self):
        m=self.module();read_fd,write_fd=os.pipe();stream=os.fdopen(read_fd,'rb',buffering=0)
        self.addCleanup(os.close,write_fd)
        owned=SimpleNamespace(process=SimpleNamespace(stdout=stream),wait=lambda **_:0,
            termination_report=SimpleNamespace(reaped=False))
        started=time.monotonic()
        with patch.object(m.sys,'frozen',True,create=True),patch.object(m,'DEADLINE_SECONDS',.05),patch.object(m,'spawn_owned',return_value=owned),patch.object(m,'terminate_owned',return_value=owned.termination_report),self.assertRaises(ValueError):
            m.check_native_once(self.root/'product.json',self.ref)
        self.assertLess(time.monotonic()-started,1)
        self.assertTrue(stream.closed)

    def test_runner_accepts_fixed_result_from_real_pipe_only_after_reaped_and_mode_shape(self):
        m=self.module();_,facts,identity,_=self.document()
        for runtime in (None,identity):
            value=dict(schema_version=m.CHILD_SCHEMA,mode='software',facts=facts,runtime=runtime,
                selection_generation=None,selection_hash=None)
            read_fd,write_fd=os.pipe();stream=os.fdopen(read_fd,'rb',buffering=0)
            with os.fdopen(write_fd,'wb',buffering=0) as output:output.write(canonical(value).encode())
            owned=SimpleNamespace(process=SimpleNamespace(stdout=stream),wait=lambda **_:0,
                termination_report=SimpleNamespace(reaped=True))
            with patch.object(m.sys,'frozen',True,create=True),patch.object(m,'spawn_owned',return_value=owned),patch.object(m,'terminate_owned',return_value=owned.termination_report):
                if runtime is not None:
                    with self.assertRaises(ValueError):m.check_native_once(self.root/'product.json',self.ref)
                else:
                    result,started,finished=m.check_native_once(self.root/'product.json',self.ref)
                    self.assertEqual(result,value);self.assertLessEqual(started,finished)
            self.assertTrue(stream.closed)

    def test_cli_private_observer_dispatch_has_only_fixed_bounded_arguments(self):
        m=self.module();from application import cli
        with patch.object(m,'observe_native_subject',return_value={'status':'DENIED'}) as observe,redirect_stdout(io.StringIO()) as output:
            code=cli.main(['_paper-release-observe','--config',str(self.root/'product.json'),
                '--receipt-ref',self.ref,'--mode','software'])
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue()),{'status':'DENIED'})
        observe.assert_called_once()
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            cli.main(['_paper-release-observe','--config',str(self.root/'product.json'),'--receipt-ref',self.ref,'--mode','software','--executable','anything'])

    def supervisor(self,identity):
        from application.platform.supervision import ProcessSupervisor
        supervisor=ProcessSupervisor(self.config,'runtime')
        supervisor.identity=identity
        supervisor.require_current=lambda:None
        return supervisor

    def test_owner_verification_is_background_nonoverlapping_and_pending_denies_without_io(self):
        m=self.module();selection,facts,identity,_=self.document();entered=threading.Event();release=threading.Event()
        active=[]
        def check(*args,**kwargs):
            active.append(1);entered.set();release.wait(2)
            return dict(schema_version=m.CHILD_SCHEMA,mode='runtime',facts=facts,runtime=identity,
                selection_generation=selection.generation,selection_hash=digest(selection.canonical_json)),m.monotonic_ns(),m.monotonic_ns()
        with patch.object(m,'check_native_once',side_effect=check),m.OwnerReleaseObservation(self.config,self.root/'product.json',self.ref,
                supervisor=self.supervisor(identity),selection=selection) as owner:
            self.assertTrue(entered.wait(2))
            started=time.monotonic()
            with patch.object(m,'_windows_read',side_effect=AssertionError('Memory read cannot touch artifact')),self.assertRaises(ValueError):owner.current(selection)
            self.assertLess(time.monotonic()-started,.2)
            self.assertEqual(len(active),1)
            release.set();deadline=time.monotonic()+2
            while True:
                try:measured=owner.current(selection);break
                except ValueError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.01)
            self.assertEqual(dict(measured),facts)
            before=(owner.path).read_bytes()
            with patch.object(m,'_windows_read',side_effect=AssertionError('Memory read cannot touch artifact')),patch.object(owner.supervisor,'require_current',side_effect=AssertionError('Memory read cannot touch profile/health SQLite')):
                self.assertEqual(dict(owner.current(selection)),facts)
            self.assertEqual(owner.path.read_bytes(),before)
        with self.assertRaises(ValueError):owner.current(selection)
        self.assertFalse(owner.thread.is_alive())

    def test_owner_late_child_and_lost_runtime_never_publish_current(self):
        m=self.module();selection,facts,identity,_=self.document()
        value=dict(schema_version=m.CHILD_SCHEMA,mode='runtime',facts=facts,runtime=identity,
            selection_generation=selection.generation,selection_hash=digest(selection.canonical_json))
        for late in (True,False):
            with self.subTest(late=late):
                identity={**identity,'process_generation_id':str(uuid.uuid4())};value={**value,'runtime':identity}
                supervisor=self.supervisor(identity);done=threading.Event()
                def check(*args,**kwargs):
                    if not late:supervisor.require_current=lambda:(_ for _ in ()).throw(ValueError('Lost owner'))
                    finished=m.monotonic_ns();done.set()
                    return value,finished-(16 if late else 1)*1_000_000_000,finished
                with patch.object(m,'check_native_once',side_effect=check),m.OwnerReleaseObservation(self.config,self.root/'product.json',self.ref,supervisor=supervisor,selection=selection) as owner:
                    self.assertTrue(done.wait(2));time.sleep(.05)
                    with self.assertRaises(ValueError):owner.current(selection)
                self.assertNotEqual(json.loads(owner.path.read_bytes())['state'],'CURRENT')


if __name__=='__main__':unittest.main()
