"""Fixed native FIXTURE market/recovery slice; never a complete PQR-05 PASS.

All effects come from installed public commands and authenticated loopback API.
Only readback is used for journals. Forced cleanup is recorded as a crash.
"""
from contextlib import closing
from datetime import datetime,timezone
from decimal import Decimal
import json,secrets,socket,sqlite3,subprocess,time

from application.config import load_config
from application.fixtures.faults import CASES,PROTECTION_CASES
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.supervision import process_health
from application.qualification import _sanitize
from brokers.paper import PaperBroker
from brokers.paper_state import decode_fact
from execution.models import OrderRequest,OrderStatus
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from native_console import enroll
from verify_paper_product import NativeExpiryFlow,ROOT,sha


class NativeFixtureCleanupError(RuntimeError):
    pass


def require_scope_denial(raw):
    if not isinstance(raw,bytes) or len(raw)>4096:raise ValueError('Bounded actual owner-scope diagnostic required')
    lines=raw.decode('utf-8').splitlines()
    if len(lines)!=2 or lines[0]!='R7: local configuration or startup validation failed':
        raise ValueError('Actual CLI diagnostic banner required')
    diagnostic=json.loads(lines[1])
    if (not isinstance(diagnostic,dict) or set(diagnostic)!={'schema_version','error_kind','reason_code',
            'os_error','windows_error','source_location'} or diagnostic['schema_version']!='r7-startup-diagnostic-v0.2'
            or diagnostic['error_kind']!='OWNER_SCOPE_BUSY' or diagnostic['reason_code']!='LOCAL_STARTUP_VALIDATION_FAILED'):
        raise ValueError('Actual owner exclusivity diagnostic required')


class NativeFixtureFaultFlow(NativeExpiryFlow):
    PAPER_CASES=CASES[1:]

    def __init__(self,package,output,case,*,expected_identity=None):
        if case not in self.PAPER_CASES:raise ValueError('Fixed sealed native fixture case required')
        # Reuse the existing authenticated public API implementation only.
        super().__init__(package,output,'intake-faults',expected_identity=expected_identity)
        self.native_case=case;self.runtime_child=None;self.runtime_stream=None
        self.observation.update(case=case,scope='SEALED_FIXTURE_MARKET_RECOVERY_SLICE',full_pqr05='NOT_QUALIFIED')

    def setup(self):
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        self.command('init',['init-profile','--config',self.config,'--data-root',self.data,'--cloud-root',self.cloud,
            '--instance-id','fixture-fault-'+self.native_case,'--port',port,'--execution-mode','FIXTURE'])
        self.generated=self.command('prepare',['prepare-fixture','--config',self.config,'--scenario','positive',
            '--paper-case',self.native_case])
        if self.generated['execution_evidence']!='NOT_RUN':raise ValueError('Unexecuted sealed author inputs required')
        self.command('research-selection',['configure-research','--config',self.config,
            '--selection-profile',self.data/'fixture-inputs/selection.json'])
        self.observation['enrollment']=enroll(self.executable,self.config,self.password,env=self.env)
        self.start_control('control-research');self.login();self.scan();_,_,job=self.enqueue();self.research()
        strategy=self.view('strategies')['items'][0]
        if strategy['current_lifecycle_state']!='CANDIDATE' or self.view('research/runs/'+job)['payload']['evidence']['sealed_oos']!='PASS':
            raise ValueError('Actual sealed native candidate required')
        self.stop_control();self.csrf=None
        self.command('paper-selection',['configure-paper','--config',self.config,
            '--selection-profile',self.data/'fixture-inputs/paper-selection.json'])
        self.start_control('control-paper');self.login()
        self.strategy=strategy

    def paper_start(self):
        policies=[row for row in self.view('policies')['items'] if row['kind']=='PAPER']
        if len(policies)!=1:raise ValueError('One actual selected fixture policy required')
        identity=self.strategy['identity']
        receipt=self.request('POST','/api/v1/paper/runs',dict(command_id='start-'+secrets.token_hex(12),
            expected_revision=self.strategy['registry_revision'],strategy_id=identity['strategy_id'],
            strategy_version=identity['strategy_version'],policy_id=policies[0]['policy_id']))
        self.paper_run=receipt['effect_ref'].removeprefix('paper:')
        self.observation['paper_run_id']=self.paper_run
        return self.paper_run

    def start_runtime(self,label):
        if self.runtime_child is not None:raise ValueError('Previous owned runtime must be reaped')
        self.runtime_log=self.output/(label+'.log');self.runtime_stream=self.runtime_log.open('xb')
        self.runtime_child=spawn_owned([str(self.executable),'paper-worker','--config',str(self.config),
            '--maximum-ticks','100'],cwd=self.output,limits=ResourceLimits(180),env=self.env,
            stdout=self.runtime_stream,stderr=subprocess.STDOUT)
        end=time.monotonic()+25
        while time.monotonic()<end:
            if self.runtime_child.process.poll() is not None:raise ValueError('Native runtime exited before readiness')
            try:
                result=self.health('runtime',self.runtime_child)
                self.observation.setdefault('runtime_identities',[]).append(result);self.persist()
                return result
            except ValueError:time.sleep(.05)
        raise ValueError('Native runtime readiness deadline')

    def finish_runtime(self,*,crash):
        if self.runtime_child is None:return
        owned=self.runtime_child;managed=False;code=None
        try:
            if not crash:
                self.command('stop-'+self.runtime_log.stem,['stop-product','--config',self.config,'--role','runtime'],timeout=30)
                code=owned.wait(timeout=10)
                managed=code==0 and process_health(load_config(self.config),'runtime')['state']=='STOPPED'
                if not managed:raise ValueError('Actual graceful native runtime stop unconfirmed')
        finally:
            cleanup=None;cleanup_error=None
            try:cleanup=terminate_owned(owned,deadline_seconds=5)
            except Exception as error:cleanup_error=type(error).__name__
            finally:
                if self.runtime_stream is not None:
                    try:self.runtime_stream.close()
                    finally:self.runtime_stream=None
            reaped=cleanup is not None and cleanup.reaped
            if reaped:self.runtime_child=None
            if code is None:code=owned.process.returncode
            raw=self.runtime_log.read_text(encoding='utf-8',errors='replace')
            raw=_sanitize(raw,ROOT).replace(self.password,'<SYNTHETIC_TEST_INPUT>').replace(str(self.output),'<PRIVATE_FIXTURE_ROOT>')
            self.runtime_log.write_text(raw,encoding='utf-8',newline='\n')
            health=process_health(load_config(self.config),'runtime')
            self.commands.append(dict(command=self.runtime_log.stem,exit_code=code,tree_reaped=reaped,cleanup_error_type=cleanup_error,
                managed_stop=managed,forced_crash=crash,forced_cleanup=not managed,
                supervisor_state_after=health.get('state'),supervisor_status_after=health['status'],
                log=self.runtime_log.name,log_hash=sha(self.runtime_log.read_bytes())))
            self.persist()
            if not reaped:raise NativeFixtureCleanupError('NATIVE_RUNTIME_CLEANUP_UNCONFIRMED')

    def wait_position(self,state,*,generation=None,entries_paused=False):
        end=time.monotonic()+25
        while time.monotonic()<end:
            if self.runtime_child.process.poll() is not None:raise ValueError('Native runtime died before position observation')
            current=self.journal(self.paper_run);position=current.state['runtime']['position']
            if (position is not None and position['lifecycle_state']==state
                    and (generation is None or current.process_generation==generation)
                    and (not entries_paused or not current.state['runtime']['paper_entries_allowed'])):return current
            time.sleep(.05)
        raise ValueError('Actual native position deadline: '+state)

    def worker(self,label,ticks):
        result=self.command(label,['paper-worker','--config',self.config,'--maximum-ticks',ticks],timeout=100)
        if (result['status']!='STOPPED' or result['ticks']!=ticks or result['run_failures']
                or result['namespace']!='FIXTURE' or result['real_forward_qualification']!='NOT_ISSUED'
                or process_health(load_config(self.config),'runtime')['state']!='STOPPED'):
            raise ValueError('Actual managed finite fixture worker failed')
        return result

    def market_count(self):
        with closing(sqlite3.connect(load_config(self.config).database_path.as_uri()+'?mode=ro',uri=True)) as db:
            return db.execute("SELECT COUNT(*) FROM paper_process_operations WHERE run_id=? AND operation_id LIKE 'market_%'",(self.paper_run,)).fetchone()[0]

    @staticmethod
    def utc(value):return datetime.fromisoformat(value.replace('Z','+00:00'))

    def require_original(self,before,after,*,protected=True):
        old,new=before.state['runtime'],after.state['runtime']
        if (after.binding!=before.binding or new['exit_anchor']!=old['exit_anchor']
                or new['position']['position_id']!=old['position']['position_id']
                or new['position']['opened_at']!=old['position']['opened_at']
                or protected and new['protection_request']!=old['protection_request']):
            raise ValueError('Original native binding/first-fill/protection changed')

    def backup_restore(self,before):
        self.stop_control();self.csrf=None
        backup=self.output/'private-backup';target=self.output/'restored'
        self.command('backup',['backup-product-data','--config',self.config,'--destination',backup])
        self.command('backup-verify',['verify-product-backup','--config',self.config,'--destination',backup])
        self.command('restore',['restore-product-data','--config',self.config,'--backup',backup,'--destination',target])
        restored=load_config(target/'restored-product.json')
        if restored.cloud_root is not None or not restored.diagnostic_only or restored.paper_runtime_enabled:
            raise ValueError('Restored product inhibition missing')
        with open_paper_process_journal(restored.database_path,require_existing=True) as process:
            original=process.recover(self.paper_run)
        if (original.state!=before.state or original.binding!=before.binding or original.revision!=before.revision
                or original.process_generation!=before.process_generation+1):
            raise ValueError('Restored original owner truth not preserved')
        self.command('restored-worker-denied',['paper-worker','--config',target/'restored-product.json','--maximum-ticks','2'],expected=2)
        with open_paper_process_journal(restored.database_path,require_existing=True) as process:
            if process.recover(self.paper_run)!=original:raise ValueError('Denied restored worker changed owner truth')
        if self.journal(self.paper_run)!=before:raise ValueError('Private backup changed source truth')
        self.observation['backup_restore']=dict(verified=True,restored='RESTORED_INHIBITED',cloud='DISCONNECTED',
            original_state_hash=sha(before.state_json.encode()),restored_state_hash=sha(original.state_json.encode()),
            restored_generation=original.process_generation,restored_worker_denied=True,source_unchanged=True)
        self.start_control('control-after-backup');self.login()

    def pause(self):
        view=self.view('paper/runs/'+self.paper_run)
        self.request('POST','/api/v1/paper/runs/'+self.paper_run+'/pause',dict(command_id='pause-'+secrets.token_hex(12),expected_revision=view['revision']))

    def finish_trade(self,before,*,ticks=35):
        self.worker('paper-successor-exit',ticks)
        after=self.journal(self.paper_run);runtime=after.state['runtime']
        self.require_original(before,after,protected=before.state['runtime']['protection_request'] is not None)
        if (runtime['position']['lifecycle_state']!='CLOSED' or Decimal(runtime['position']['actual_quantity'])!=0
                or len(runtime['closed_trades'])!=1 or runtime['forward']['real_elapsed_ns']!=0
                or after.pending_operations):raise ValueError('Actual canonical flat trade missing')
        with open_paper_runtime_journal(load_config(self.config).database_path,require_existing=True) as journal:
            graph=journal.recover(position_id=runtime['position']['position_id'])
        if graph.status!='READY' or len(graph.fills)!=2 or graph.trade_result.payload!=runtime['closed_trades'][0]:
            raise ValueError('Canonical fill/TradeResult graph incorrect')
        self.observation.update(canonical_fills=2,canonical_trades=1,final_quantity='0',native_direction=runtime['position']['side'],
            original_binding_preserved=True,original_first_fill_anchor_preserved=True,
            real_elapsed_ns=0,simulated_elapsed_seconds=runtime['forward']['simulated_elapsed_seconds'])

    def standing_protection_case(self):
        """Actual sealed E4 observations, interpreted and persisted by E5/E6."""
        self.paper_start();self.worker('paper-first',2);before=self.journal(self.paper_run)
        if before.state['runtime']['position']['lifecycle_state']!='OPEN_PROTECTED':
            raise ValueError('Actual original protected position required')
        self.pause()
        mode=PROTECTION_CASES[self.native_case]
        self.worker('paper-protection-fault',1 if mode=='CANCELED' else 3)
        fault=self.journal(self.paper_run);runtime=fault.state['runtime']
        self.require_original(before,fault)
        if runtime['paper_entries_allowed']:raise ValueError('Actual operator pause was not consumed')
        broker=PaperBroker.from_state(fault.state['broker']);request=decode_fact(OrderRequest,runtime['protection_request'])
        with open_paper_runtime_journal(load_config(self.config).database_path,require_existing=True) as journal:
            graph=journal.recover(position_id=runtime['position']['position_id'])
        if mode=='CANCELED':
            if (broker.query_order(request.client_order_id).order_status!=OrderStatus.CANCELED
                    or runtime['position']['lifecycle_state']!='EXIT_REQUESTED'
                    or Decimal(runtime['position']['actual_quantity'])<=0
                    or not any(row.payload['lifecycle_event']=='PROTECTION_LOST' and row.payload['lifecycle_state']=='EMERGENCY'
                               for row in graph.lifecycle_history)):
                raise ValueError('Actual E4 cancellation/E5 emergency graph missing')
            self.observation['actual_stop_cancellation']=True
        else:
            if (runtime['position']['lifecycle_state']!='RECONCILIATION_REQUIRED'
                    or broker.query_order(request.client_order_id).order_status!=OrderStatus.OPEN):
                raise ValueError('Unavailable read must preserve actual stop and E5 uncertainty')
            self.worker('paper-protection-recovery',1);recovered=self.journal(self.paper_run)
            self.require_original(before,recovered)
            position=recovered.state['runtime']['position']
            if (position['lifecycle_state']!='OPEN_PROTECTED' or position['lifecycle_event']!='RECONCILED_OPEN_PROTECTED'
                    or recovered.process_generation<=fault.process_generation
                    or recovered.state['runtime']['paper_entries_allowed']):
                raise ValueError('Actual successor did not reconcile original stop while preserving pause')
            self.observation.update(canonical_recovery_event=position['lifecycle_event'],paused_recovery_preserved=True)
        self.observation.update(protection_fault_mode=mode,query_fault_state=runtime['position']['lifecycle_state'],
            positive_quantity_during_fault=runtime['position']['actual_quantity'])
        self.finish_trade(before,ticks=6 if mode=='CANCELED' else 32)

    def run(self):
        try:
            self.setup()
            if self.native_case in PROTECTION_CASES:
                self.standing_protection_case();self.observation['passed']=True
                return self.observation
            if self.native_case=='hold-for-recovery':
                self.start_runtime('idle-crash')
                if self.view('paper/runs')['items']:raise ValueError('Idle native worker created a run')
                self.finish_runtime(crash=True);self.observation['actual_idle_flat_crash']=True
            self.paper_start()
            if self.native_case in ('hold-for-recovery','protection-rejected-hold'):
                identity=self.start_runtime('owning-worker-crash')
                pending=self.wait_position('EMERGENCY' if self.native_case=='protection-rejected-hold' else 'OPEN_PROTECTED',generation=1)
                if self.native_case=='hold-for-recovery':
                    self.command('contender-denied',['paper-worker','--config',self.config,'--maximum-ticks','2'],expected=2)
                    require_scope_denial((self.output/'contender-denied.log').read_bytes())
                    if self.health('runtime',self.runtime_child)['process_generation_id']!=identity['process_generation_id']:
                        raise ValueError('Contender replaced actual runtime')
                    self.pause()
                self.finish_runtime(crash=True)
                before=self.journal(self.paper_run)
                if before.state['runtime']['position']['lifecycle_state']!=pending.state['runtime']['position']['lifecycle_state']:
                    raise ValueError('Crash missed the observed lifecycle state')
                if self.native_case=='protection-rejected-hold':
                    runtime=before.state['runtime'];broker=PaperBroker.from_state(before.state['broker'])
                    protection=decode_fact(OrderRequest,runtime['protection_request'])
                    if (broker.query_order(protection.client_order_id).order_status!=OrderStatus.REJECTED
                            or Decimal(runtime['position']['actual_quantity'])<=0):
                        raise ValueError('Expected actual nonzero position with definitively rejected protection')
                    self.observation['actual_crash_state']='EMERGENCY_NONZERO_PROTECTION_REJECTED'
                    self.finish_trade(before,ticks=4)
                else:
                    self.observation['actual_crash_state']='OPEN_PROTECTED'
                    self.start_runtime('managed-successor')
                    successor=self.wait_position('OPEN_PROTECTED',generation=before.process_generation+1,entries_paused=True)
                    self.require_original(before,successor)
                    if successor.process_generation!=before.process_generation+1 or successor.state['runtime']['paper_entries_allowed']:
                        raise ValueError('Successor fencing/pause not retained')
                    self.finish_runtime(crash=False);before=self.journal(self.paper_run)
                    stale=self.command('stale-generation-operation',['_paper-native-stale-check','--config',self.config,'--run-id',self.paper_run])
                    if (stale['status']!='STALE_OPERATION_DENIED' or not stale['original_checkpoint_unchanged']
                            or stale['actual_generation']!=before.process_generation):
                        raise ValueError('Actual prior E6 generation was not denied')
                    self.observation['stale_generation_operation_denied']=True
                    self.backup_restore(before);self.finish_trade(before)
            else:
                self.worker('paper-first',2);before=self.journal(self.paper_run)
                if before.state['runtime']['position']['lifecycle_state']!='OPEN_PROTECTED':raise ValueError('Actual initial protection missing')
                self.observation['initial_quantity']=before.state['runtime']['position']['actual_quantity']
                if self.native_case=='partial-fill-hold':
                    runtime=before.state['runtime'];broker=PaperBroker.from_state(before.state['broker'])
                    entry=decode_fact(OrderRequest,runtime['entry_request']);protection=decode_fact(OrderRequest,runtime['protection_request'])
                    result=broker.query_order(entry.client_order_id)
                    if (Decimal(runtime['position']['actual_quantity'])!=Decimal('0.0005') or protection.quantity!=Decimal('0.0005')
                            or result.order_status!=OrderStatus.CANCELED or result.filled_quantity!=Decimal('0.0005')):
                        raise ValueError('Actual partial quantity/protection/remainder cancellation missing')
                    self.observation['entry_remainder_canceled']=True;self.backup_restore(before)
                else:
                    count=self.market_count();ticks=7 if self.native_case=='missing-market-hold' else 1
                    self.worker('paper-fault-window',ticks);observed=self.journal(self.paper_run)
                    self.require_original(before,observed)
                    runtime=observed.state['runtime']
                    if runtime['position']['lifecycle_state']!='OPEN_PROTECTED':raise ValueError('Market fault abandoned original protection')
                    if self.native_case=='duplicate-market-hold':
                        if self.market_count()!=count or runtime['last_market']!=before.state['runtime']['last_market']:
                            raise ValueError('Duplicate market created a new market operation')
                    elif self.native_case=='missing-market-hold':
                        if (self.market_count()!=count or runtime['last_market']!=before.state['runtime']['last_market']
                                or runtime['forward']['last_healthy'] or (self.utc(runtime['forward']['observed_at'])-
                                self.utc(runtime['last_market']['observed_at'])).total_seconds()<=5):
                            raise ValueError('Actual missing fresh market window not observed')
                    elif runtime['market_status']!='STALE' or runtime['forward']['last_healthy'] or runtime['last_market']['freshness_ms']!=10000:
                        raise ValueError('Actual stale market observation missing')
                    if runtime['position']['broker_state_observed_at']<=before.state['runtime']['position']['broker_state_observed_at']:
                        raise ValueError('Protective management did not progress during market fault')
                    self.observation['market_fault']=dict(case=self.native_case,market_operation_increment=self.market_count()-count,
                        protected=True,healthy=runtime['forward']['last_healthy'],actual_observed_at=runtime['forward']['observed_at'],
                        last_market_observed_at=runtime['last_market']['observed_at'])
                self.pause();self.finish_trade(before)
            self.observation['passed']=True
        finally:
            try:self.finish_runtime(crash=True)
            finally:self.stop_control();self.persist();self.guard()
        return self.observation


def verify_slice(package,output,identity):
    observations=[]
    for case in NativeFixtureFaultFlow.PAPER_CASES:
        flow=NativeFixtureFaultFlow(package,output/case,case,expected_identity=identity)
        try:observations.append(flow.run())
        except Exception as error:
            flow.observation.update(passed=False,error_type=type(error).__name__,reason='NATIVE_FIXTURE_CASE_FAILED')
            flow.persist();observations.append(dict(flow.observation))
            if isinstance(error,NativeFixtureCleanupError) or getattr(flow,'runtime_child',None) is not None:break
    return observations
