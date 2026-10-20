"""Prepare UNAPPLIED closed observation projections outside the frozen checkout."""
from pathlib import Path
import ast, hashlib, json

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
OUT=BASE/'ui01-projection-unapplied-v1'
if OUT.exists():raise ValueError('Fresh unapplied patch required')
OUT.mkdir()
records=[]
def prepare(ref,transform):
    path=ROOT/ref
    original=path.read_text(encoding='utf-8')
    changed=transform(original)
    if changed==original:raise ValueError('No change: '+ref)
    ast.parse(changed)
    target=OUT/ref;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(changed,encoding='utf-8',newline='\n')
    records.append(dict(ref=ref,before_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        after_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))

DTO='''
ObservationStatus = Literal['AVAILABLE','NOT_CONFIGURED','NOT_RUN','UNAVAILABLE']
ProcessRole = Literal['control','research','runtime','cloud','coordinator']
JobState = Literal['QUEUED','RUNNING','CANCEL_REQUESTED','COMPLETE','BLOCKED','FAILED','CANCELED','EXPIRED']


class UnobservedFacts(StrictDTO):
    pass


F = TypeVar('F', bound=StrictDTO)
class DiagnosticObservation(StrictDTO, Generic[F]):
    status: ObservationStatus
    source: Annotated[str, Field(min_length=1,max_length=96)]
    as_of: str | None
    checked_at: str
    reason_codes: Annotated[list[Identifier], Field(max_length=16)]
    facts: F
    financial_authority: Literal['NONE']


class ResourceLimitFacts(StrictDTO):
    research_worker_count: Annotated[int, Field(ge=1,le=64)]


class SelectedStrategyFact(StrictDTO):
    strategy_id: Identifier
    strategy_version: Identifier
    content_hash: Hash
    relationship: Literal['CONFIGURED_SELECTION']


class StrategySubjectFacts(StrictDTO):
    items: Annotated[list[SelectedStrategyFact], Field(max_length=1)]


class ResearchStageCount(StrictDTO):
    state: JobState
    stage: Annotated[str, Field(min_length=1,max_length=64,pattern=r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')] | None
    count: Annotated[int, Field(ge=0,le=2**63-1)]
    last_observed_at: str


class ResearchStageFacts(StrictDTO):
    items: Annotated[list[ResearchStageCount], Field(max_length=256)]
    total_jobs: Annotated[int, Field(ge=0,le=2**63-1)]


class HistoricalAlertFact(StrictDTO):
    namespace: Literal['FIXTURE','LOCAL_RESEARCH']
    run_id: Identifier
    state: Literal['FAILED']
    revision: Annotated[int, Field(ge=0,le=2**63-1)]
    generation: Annotated[int, Field(ge=0,le=2**63-1)]
    recorded_at: str
    reason_codes: Annotated[list[Identifier], Field(min_length=1,max_length=16)]
    source: Literal['research_queue']
    alert_id: Identifier


class AlertFacts(StrictDTO):
    items: Annotated[list[HistoricalAlertFact], Field(max_length=5)]
    total: Annotated[int, Field(ge=0,le=2**63-1)]


class ProcessObservationFacts(StrictDTO):
    role: ProcessRole
    status: Annotated[str, Field(min_length=1,max_length=64)]
    recorded_state: Annotated[str, Field(min_length=1,max_length=64)] | None
    generation: Annotated[int, Field(ge=0,le=2**63-1)] | None
    process_generation_id: Identifier | None
    started_at: str | None
    heartbeat_at: str | None
    heartbeat_sequence: Annotated[int, Field(ge=0,le=2**63-1)] | None
    config_hash: Hash | None


class ComponentObservations(StrictDTO):
    control: DiagnosticObservation[ProcessObservationFacts]
    research: DiagnosticObservation[ProcessObservationFacts]
    runtime: DiagnosticObservation[ProcessObservationFacts]
    cloud: DiagnosticObservation[ProcessObservationFacts]
    coordinator: DiagnosticObservation[ProcessObservationFacts]

'''
def dto(raw):
    raw=raw.replace('class OverviewView(StrictDTO):',DTO+'\nclass OverviewView(StrictDTO):',1)
    raw=raw.replace("    mode: Literal['RESEARCH', 'PAPER_FIXTURE', 'PAPER_REAL_TIME', 'LIVE']",'''    strategy_subjects: DiagnosticObservation[StrategySubjectFacts | UnobservedFacts]
    research_stage_counts: DiagnosticObservation[ResearchStageFacts | UnobservedFacts]
    resource_limits: DiagnosticObservation[ResourceLimitFacts]
    alerts: DiagnosticObservation[AlertFacts | UnobservedFacts]
    mode: Literal['RESEARCH', 'PAPER_FIXTURE', 'PAPER_REAL_TIME', 'LIVE']''',1)
    raw=raw.replace('class HealthView(StrictDTO):','''class HealthView(StrictDTO):
    components: ComponentObservations
    risk: DiagnosticObservation[UnobservedFacts]
    execution: DiagnosticObservation[UnobservedFacts]
    preflight: DiagnosticObservation[UnobservedFacts]
    external_consumer: DiagnosticObservation[UnobservedFacts]''',1)
    raw=raw.replace('class SettingsView(StrictDTO):','''class SettingsView(StrictDTO):
    resource_limits: DiagnosticObservation[ResourceLimitFacts]
    clock_health: DiagnosticObservation[UnobservedFacts]
    backup: DiagnosticObservation[UnobservedFacts]
    transport_test: DiagnosticObservation[UnobservedFacts]
    credential_presence: DiagnosticObservation[UnobservedFacts]''',1)
    return raw
prepare('src/application/control_api/dto.py',dto)

SERVICE_METHODS='''    def _observation(self, source, *, status='UNAVAILABLE', facts=None, as_of=None, reasons=()):
        return dict(status=status,source=source,as_of=as_of,checked_at=_stamp(self.clock()),
                    reason_codes=list(reasons),facts={} if facts is None else facts,financial_authority='NONE')

    def _resource_limits(self):
        return self._observation('product_config',status='AVAILABLE',
            facts=dict(research_worker_count=self.config.research_worker_count),
            reasons=('CONFIGURED_WORKER_COUNT_ONLY',))

    def settings(self):
        value=self._static_settings()
        value.update(resource_limits=self._resource_limits(),
            clock_health=self._observation('clock_health',reasons=('CLOCK_HEALTH_NOT_OBSERVED',)),
            backup=self._observation('backup_selection',status='NOT_CONFIGURED',reasons=('BACKUP_DESTINATION_NOT_CONFIGURED',)),
            transport_test=self._observation('transport_test',status='NOT_RUN',reasons=('TRANSPORT_TEST_NOT_RUN',)),
            credential_presence=self._observation('credential_presence',reasons=('CREDENTIAL_PRESENCE_NOT_OBSERVED',)))
        return value

    def _components(self):
        from application.platform.supervision import process_health
        result={}
        for role in ('control','research','runtime','cloud','coordinator'):
            observed=process_health(self.config,role,clock=self.clock)
            status=observed['status']
            facts=dict(role=role,status=status,recorded_state=observed.get('state'),
                **{key:observed.get(key) for key in ('generation','process_generation_id','started_at',
                                                    'heartbeat_at','heartbeat_sequence','config_hash')})
            result[role]=self._observation('process_supervision:'+role,
                status='UNAVAILABLE' if status=='SUPERVISION_STORAGE_FAILURE' else 'AVAILABLE',facts=facts,
                as_of=observed.get('heartbeat_at'),reasons=(status,))
        return result

'''
def services(raw):
    raw=raw.replace('    def settings(self):','    def _static_settings(self):',1)
    raw=raw.replace('    def metadata(self, source, *, data=None):',SERVICE_METHODS+'    def metadata(self, source, *, data=None):',1)
    raw=raw.replace('settings = self.settings()','settings = self._static_settings()',1)
    raw=raw.replace("if operation == 'SETTINGS_UPDATE': return self.settings()['revision']", "if operation == 'SETTINGS_UPDATE': return self._static_settings()['revision']",1)
    raw=raw.replace("runtime_llm_calls=0, restoration=restoration,",'''runtime_llm_calls=0, restoration=restoration, components=self._components(),
                risk=self._observation('risk_owner',reasons=('RISK_NOT_OBSERVED',)),
                execution=self._observation('execution_owner',reasons=('EXECUTION_NOT_OBSERVED',)),
                preflight=self._observation('preflight_owner',reasons=('PREFLIGHT_NOT_OBSERVED',)),
                external_consumer=self._observation('external_consumer',reasons=('EXTERNAL_CONSUMER_NOT_OBSERVED',)),''',1)
    raw=raw.replace("cloud_status='NOT_CONNECTED', reason_codes=['OPERATIONAL_OWNERS_NOT_CONFIGURED'])",'''cloud_status='NOT_CONNECTED', reason_codes=['OPERATIONAL_OWNERS_NOT_CONFIGURED'],
            resource_limits=self._resource_limits(),
            strategy_subjects=self._observation('paper_selection',status='NOT_CONFIGURED',reasons=('STRATEGY_SELECTION_NOT_CONFIGURED',)),
            research_stage_counts=self._observation('research_queue',status='NOT_CONFIGURED',reasons=('RESEARCH_QUEUE_NOT_CONFIGURED',)),
            alerts=self._observation('research_queue',status='NOT_CONFIGURED',reasons=('ALERT_OWNER_NOT_CONFIGURED',)))''',1)
    return raw
prepare('src/application/control_api/services.py',services)

COUNTS='''    def state_stage_counts(self):
        """Bounded persisted stage/state facts; no owner work or writable open."""
        from storage.qualification import _readonly_uri
        end=time.monotonic()+2
        allowed={'QUEUED','RUNNING','CANCEL_REQUESTED','COMPLETE','BLOCKED','FAILED','CANCELED','EXPIRED'}
        try:
            identity=self._alert_file_identity(self.path)
            with closing(sqlite3.connect(':memory:')) as model:
                model.executescript((Path(__file__).parents[1]/'migrations/0005_research_queue.sql').read_text(encoding='utf-8'))
                expected=self._alert_schema(model)
            with closing(sqlite3.connect(_readonly_uri(self.path),uri=True,timeout=1)) as db:
                db.row_factory=sqlite3.Row
                db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,65536)
                db.set_progress_handler(lambda:int(time.monotonic()>=end),1000)
                db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
                db.execute('PRAGMA busy_timeout=1000');db.execute('PRAGMA temp_store=MEMORY');db.execute('BEGIN')
                if (self._alert_schema(db)!=expected or self.namespace not in ('FIXTURE','LOCAL_RESEARCH')
                        or [tuple(row) for row in db.execute('SELECT singleton,namespace FROM research_queue_namespace LIMIT 2')]!=[(1,self.namespace)]):
                    raise ResearchQueueError('RESEARCH_QUEUE_COUNTS_UNAVAILABLE')
                cursor=db.execute('SELECT state,stage,updated_at FROM research_queue_jobs')
                groups={};total=0;as_of=None
                while batch:=cursor.fetchmany(128):
                    if time.monotonic()>=end:raise ResearchQueueError('RESEARCH_QUEUE_COUNTS_UNAVAILABLE')
                    for row in batch:
                        state,stage,observed=row['state'],row['stage'],row['updated_at']
                        if (state not in allowed or (stage is not None and (not isinstance(stage,str)
                                or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,63}',stage)))
                                or not isinstance(observed,str) or not 1<=len(observed)<=40
                                or stamp(datetime.fromisoformat(observed.replace('Z','+00:00')))!=observed):
                            raise ResearchQueueError('RESEARCH_QUEUE_COUNTS_UNAVAILABLE')
                        key=(state,stage)
                        if key not in groups:
                            if len(groups)>=256:raise ResearchQueueError('RESEARCH_QUEUE_COUNTS_UNAVAILABLE')
                            groups[key]=dict(state=state,stage=stage,count=0,last_observed_at=observed)
                        group=groups[key]
                        group['count']=_revision_int(group['count']+1)
                        group['last_observed_at']=max(group['last_observed_at'],observed)
                        total=_revision_int(total+1)
                        as_of=observed if as_of is None else max(as_of,observed)
                result=dict(items=[groups[key] for key in sorted(groups,key=lambda key:(key[0],key[1] or ''))],total_jobs=total,as_of=as_of)
                if (len(canonical(result).encode())>65536 or time.monotonic()>=end
                        or self._alert_file_identity(self.path)!=identity):
                    raise ResearchQueueError('RESEARCH_QUEUE_COUNTS_UNAVAILABLE')
                return result
        except (ResearchQueueError,sqlite3.Error,OSError,ValueError,TypeError,KeyError,RecursionError):
            raise ResearchQueueError('RESEARCH_QUEUE_COUNTS_UNAVAILABLE') from None

'''
prepare('src/application/research/queue.py',lambda raw:raw.replace('    def evidence_view(self,run_id):',COUNTS+'    def evidence_view(self,run_id):',1))

OVERVIEW='''            if self.paper_start is not None and self.paper_start.strategy_identity is not None:
                try:
                    identity=self.paper_start.strategy_identity
                    with self.registry_factory() as e6:record=e6.get_strategy(identity)
                    value['strategy_subjects']=self._observation('paper_selection',status='AVAILABLE',
                        facts=dict(items=[dict(strategy_id=identity.strategy_id,strategy_version=identity.strategy_version,
                            content_hash=record.content_hash,relationship='CONFIGURED_SELECTION')]),
                        reasons=('CONFIGURED_SELECTION_NOT_RUNTIME_BINDING',))
                except (ValueError,RuntimeError,KeyError):
                    value['strategy_subjects']=self._observation('paper_selection',reasons=('STRATEGY_SELECTION_UNAVAILABLE',))
            if self.queue is not None:
                try:
                    counts=self.queue.state_stage_counts()
                    value['research_stage_counts']=self._observation('research_queue',status='AVAILABLE',
                        facts=dict(items=counts['items'],total_jobs=counts['total_jobs']),as_of=counts['as_of'])
                    states={}
                    for row in counts['items']:states[row['state']]=states.get(row['state'],0)+row['count']
                    value.update(queued_jobs=states.get('QUEUED',0),running_jobs=states.get('RUNNING',0)+states.get('CANCEL_REQUESTED',0))
                except ResearchQueueError:
                    value['research_stage_counts']=self._observation('research_queue',reasons=('RESEARCH_QUEUE_COUNTS_UNAVAILABLE',))
                try:
                    alerts=self.view('alerts',limit=5,offset=0)
                    value['alerts']=self._observation('research_queue',status='AVAILABLE',
                        facts=dict(items=alerts['items'],total=alerts['total']),
                        as_of=max((row['recorded_at'] for row in alerts['items']),default=None),
                        reasons=('HISTORICAL_FAILURES_NOT_CURRENT_HEALTH',))
                except APIError:
                    value['alerts']=self._observation('research_queue',reasons=('RESEARCH_ALERT_HISTORY_UNAVAILABLE',))
'''
def owners(raw):
    old="""            if self.queue is not None:
                counts=self.queue.counts(); value.update(queued_jobs=counts.get('QUEUED',0),running_jobs=counts.get('RUNNING',0)+counts.get('CANCEL_REQUESTED',0))
"""
    if old not in raw:raise ValueError('Exact original overview required')
    raw=raw.replace(old,OVERVIEW,1)
    old="""            from application.platform.supervision import process_health
            control = process_health(self.config, 'control', clock=self.clock)
            if control['status'] != 'NOT_STARTED': value['control'] = 'PROCESS_' + control['status']
            if self.queue is not None:
                worker = process_health(self.config, 'research', clock=self.clock)
                value['research'] = 'QUEUE_AVAILABLE_WORKER_' + worker['status']
"""
    new="""            components=value['components']
            control=components['control']['facts']
            if control['status']!='NOT_STARTED':value['control']='PROCESS_'+control['status']
            runtime=components['runtime']['facts']
            if runtime['status']!='NOT_STARTED':value['runtime']='PROCESS_'+runtime['status']
            if self.queue is not None:
                value['research']='QUEUE_AVAILABLE_WORKER_'+components['research']['facts']['status']
"""
    if old not in raw:raise ValueError('Exact original health required')
    return raw.replace(old,new,1)
prepare('src/application/control_api/owner_services.py',owners)
(OUT/'manifest.json').write_text(json.dumps(dict(status='UNAPPLIED_NOT_EXECUTED',records=records),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='PREPARED_UNAPPLIED',files=len(records),output=OUT.name)))
