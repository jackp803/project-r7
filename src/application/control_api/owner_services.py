"""Actual local E6/intake/research/PAPER read and command service adapters."""
from dataclasses import asdict
import json

from application.control_api.services import LocalControlServices
from application.control_api.errors import APIError
from application.control_api.auth import _stamp
from application.research.queue import ResearchQueueError
from registry import StrategyIdentity, ConcurrencyConflict, EvidenceGateError
from storage.runtime_models import RuntimePersistenceError


class OwnerControlServices(LocalControlServices):
    def __init__(self, config, *, namespace, clock, registry_factory, intake_factory=None, inbox_factory=None,
                 research_queue=None, research_resolver=None, paper_reader=None, paper_start=None, approval=None, deployment=None):
        super().__init__(config, namespace=namespace, clock=clock)
        if not callable(registry_factory): raise ValueError('Actual E6 registry factory required')
        self.registry_factory, self.intake_factory, self.inbox_factory = registry_factory, intake_factory, inbox_factory
        self.queue, self.resolver = research_queue, research_resolver
        self.paper_reader, self.paper_start, self.approval, self.deployment = paper_reader, paper_start, approval, deployment
        if research_queue is not None and research_queue.namespace != namespace: raise ValueError('Same namespace research queue required')
        with self._db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS control_scans(singleton INTEGER PRIMARY KEY CHECK(singleton=1),revision INTEGER NOT NULL);
                INSERT OR IGNORE INTO control_scans VALUES(1,0);
                CREATE TABLE IF NOT EXISTS control_scan_receipts(command_id TEXT PRIMARY KEY,request_json TEXT NOT NULL,receipt_json TEXT NOT NULL,summary_json TEXT NOT NULL);''')

    @staticmethod
    def _page(items, limit, offset, *, total=None):
        return dict(items=items,limit=limit,offset=offset,total=total,status='AVAILABLE',reason_codes=[])

    def install_authenticator(self,issuer):
        if self.approval is not None: self.approval.install_authenticator(issuer)
        if self.deployment is not None: self.deployment.install_authenticator(issuer)

    @staticmethod
    def _object(payload, revision, contract, *, status='AVAILABLE', reasons=()):
        return dict(status=status,revision=revision,contract=contract,payload=payload,reason_codes=list(reasons))

    @staticmethod
    def _strategy(record, *, detail=False):
        value=asdict(record); value.pop('definition_json')
        definition=json.loads(record.definition_json)
        rules=definition.get('rules',{})
        value.update(evaluation_timeframe=rules.get('evaluation_timeframe'),required_timeframes=definition.get('required_timeframes'),
            max_hold_seconds=rules.get('exit_policy',{}).get('max_hold_seconds'))
        if detail: value['definition']=definition
        return value

    def view(self,name,*,subject=None,limit=50,offset=0):
        if name=='approval_preview' and self.approval is not None:
            identity=StrategyIdentity(*subject[:2])
            return self.approval.preview(identity,envelope_ref=subject[2],expected_revision=subject[3])
        if name=='strategies':
            with self.registry_factory() as e6:
                if subject is not None:
                    record=e6.get_strategy(StrategyIdentity(*subject))
                    payload=self._strategy(record,detail=True)
                    if self.resolver is not None and self.intake_factory is not None:
                        with self.intake_factory() as intake:
                            submission=intake.find_strategy_submission(record.identity.strategy_id,record.identity.strategy_version,record.content_hash)
                        if submission is not None:
                            payload['author_metadata']=dict(submission_id=submission,manifest=self.resolver.manifest_view(submission))
                    if self.deployment is not None:
                        payload['deployment']=self.deployment.strategy_subject(record.identity)
                    return self._object(payload,record.registry_revision,record.strategy_schema_version)
                return self._page([self._strategy(row) for row in e6.list_strategies(limit=limit,offset=offset)],limit,offset,
                    total=sum(e6.lifecycle_counts().values()))
        if name=='submissions' and self.intake_factory is not None:
            with self.intake_factory() as intake:
                if subject is not None:
                    value=intake.submission_view(subject)
                    if value is None: raise APIError('UNAVAILABLE','SUBMISSION_NOT_FOUND',404)
                    if self.resolver is not None and value['receipt'] is not None:
                        value['author_manifest']=self.resolver.manifest_view(subject)
                    return self._object(value,value['revision'],'r7-intake-receipt-v0.2')
                return self._page(list(intake.list_submissions(limit=limit,offset=offset)),limit,offset)
        if name=='research_runs' and self.queue is not None:
            try:
                if subject is not None:
                    value=self.queue.get(subject)
                    value['evidence']=self.queue.evidence_view(subject)
                    return self._object(value,value['revision'],'r7-research-queue-v0.2',status=value['state'],reasons=value['reason_codes'])
                return self._page(self.queue.list(limit=limit,offset=offset),limit,offset,total=sum(self.queue.counts().values()))
            except ResearchQueueError: raise APIError('UNAVAILABLE','RESEARCH_JOB_NOT_FOUND',404) from None
        if name=='policies' and (self.resolver is not None or self.paper_start is not None):
            rows=[] if self.resolver is None else [dict(row,kind='RESEARCH') for row in self.resolver.policy_views()]
            if self.paper_start is not None: rows.extend(self.paper_start.policy_views())
            return self._page(rows[offset:offset+limit],limit,offset,total=len(rows))
        if name=='datasets' and self.resolver is not None:
            rows=self.resolver.dataset_views()
            if any(row['namespace']!=self.namespace for row in rows): raise APIError('INVALID_INPUT','DATASET_NAMESPACE_CONFLICT',422)
            return self._page(rows[offset:offset+limit],limit,offset,total=len(rows))
        if name=='overview':
            value=super().view(name)
            with self.registry_factory() as e6: value['lifecycle_counts']=e6.lifecycle_counts()
            if self.inbox_factory is not None:
                with self._db() as db: value['scan_revision']=db.execute('SELECT revision FROM control_scans WHERE singleton=1').fetchone()[0]
            if self.queue is not None:
                counts=self.queue.counts(); value.update(queued_jobs=counts.get('QUEUED',0),running_jobs=counts.get('RUNNING',0)+counts.get('CANCEL_REQUESTED',0))
            return value
        if name=='health':
            value=super().view(name)
            with self.registry_factory() as e6: e6.lifecycle_counts()
            value['storage']='E6_AND_CONTROL_STORES_AVAILABLE'
            if self.queue is not None: value['research']='QUEUE_AVAILABLE_WORKER_HEALTH_UNKNOWN'
            return value
        if name=='paper_runs' and self.paper_reader is not None:
            if subject is None:
                return self._page(self.paper_reader.list(self.registry_factory,limit=limit,offset=offset),limit,offset)
            return self.paper_reader.view(subject)
        return super().view(name,subject=subject,limit=limit,offset=offset)

    def metadata(self,source,*,data=None):
        value=super().metadata(source,data=data)
        if source=='application:approval_preview' and data is not None:
            value['as_of']=data['observed_at']
        if source=='application:paper_runs' and data is not None and 'payload' in data:
            value['as_of']=data['payload']['broker_observed_at']
            value['freshness']='UNKNOWN'
            value['current_or_last_known']='LAST_KNOWN_GOOD' if value['as_of'] else 'UNAVAILABLE'
        return value

    def revision(self,operation,resource,arguments):
        try:
            if operation=='INBOX_SCAN' and self.inbox_factory is not None:
                with self._db() as db: return db.execute('SELECT revision FROM control_scans').fetchone()[0]
            if operation=='RESEARCH_ENQUEUE' and self.queue is not None:
                return self.queue.selected_submission_revision(arguments['submission_id'],arguments['policy_id'])
            if operation=='RESEARCH_CANCEL' and self.queue is not None: return self.queue.get(resource.removeprefix('research:'))['revision']
            if operation=='PAPER_PAUSE' and self.paper_reader is not None: return self.paper_reader.revision(resource.removeprefix('paper:'))
            if operation=='PAPER_START' and self.paper_start is not None:
                with self.registry_factory() as e6:
                    return e6.get_strategy(StrategyIdentity(arguments['strategy_id'],arguments['strategy_version'])).registry_revision
            if operation=='APPROVAL' and self.approval is not None: return self.approval.revision(arguments)
            if operation.startswith('DEPLOYMENT_') and self.deployment is not None: return self.deployment.revision(resource,arguments)
            return super().revision(operation,resource,arguments)
        except ResearchQueueError as error: raise APIError('NOT_CONFIGURED','RESEARCH_SELECTION_UNAVAILABLE',503) from error

    def execute(self,operation,resource,arguments,*,actor,human,command_id,expected_revision):
        try:
            if operation=='RESEARCH_ENQUEUE' and self.queue is not None:
                result=self.queue.enqueue(arguments['submission_id'],arguments['policy_id'],command_id,expected_revision,actor=actor)
                return self._receipt(command_id,actor,resource,expected_revision,expected_revision,'QUEUED','research-job:'+result['run_id'],result['observed_at'])
            if operation=='RESEARCH_CANCEL' and self.queue is not None:
                result=self.queue.cancel(resource.removeprefix('research:'),expected_revision,command_id,actor=actor)
                return self._receipt(command_id,actor,resource,expected_revision,result['revision'],'COMPLETE','research-job:'+result['run_id'],result['observed_at'],
                    reasons=[result['status']])
            if operation=='INBOX_SCAN' and self.inbox_factory is not None:
                return self._scan(command_id,actor,expected_revision)
            if operation=='PAPER_PAUSE' and self.paper_reader is not None:
                result=self.paper_reader.pause(resource.removeprefix('paper:'),command_id,actor,expected_revision)
                return self._receipt(command_id,actor,resource,expected_revision,result['resource_revision'],'PAUSED','paper:'+result['run_id'],result['observed_at'],
                    reasons=result['reason_codes'])
            if operation=='PAPER_START' and self.paper_start is not None:
                return self.paper_start.start(arguments,actor=actor,command_id=command_id,expected_revision=expected_revision)
            if operation=='APPROVAL' and self.approval is not None:
                return self.approval.record(arguments,actor=actor,human=human,command_id=command_id,expected_revision=expected_revision)
            if operation.startswith('DEPLOYMENT_') and self.deployment is not None:
                return self.deployment.execute(operation,resource,arguments,actor=actor,human=human,command_id=command_id,expected_revision=expected_revision)
            return super().execute(operation,resource,arguments,actor=actor,human=human,command_id=command_id,expected_revision=expected_revision)
        except (ResearchQueueError,ConcurrencyConflict): raise APIError('CONFLICT','OWNER_COMMAND_CONFLICT',409) from None
        except EvidenceGateError: raise APIError('INSUFFICIENT_EVIDENCE','CURRENT_OWNER_EVIDENCE_REQUIRED',409) from None
        except RuntimePersistenceError: raise APIError('UNAVAILABLE','PAPER_CONTROL_UNAVAILABLE',503,terminal=False) from None

    @staticmethod
    def _receipt(command_id,actor,resource,expected,revision,status,reference,observed,*,reasons=()):
        return dict(command_id=command_id,actor=actor,resource=resource,expected_revision=expected,resource_revision=revision,
                    status=status,effect_ref=reference,reason_codes=list(reasons),observed_at=observed)

    def _scan(self,command_id,actor,expected_revision):
        raw=json.dumps(dict(actor=actor,expected_revision=expected_revision),sort_keys=True)
        with self._db() as db:
            cached=db.execute('SELECT * FROM control_scan_receipts WHERE command_id=?',(command_id,)).fetchone()
            if cached:
                if cached['request_json']!=raw: raise APIError('CONFLICT','COMMAND_CONTENT_CONFLICT',409)
                return json.loads(cached['receipt_json'])
            if db.execute('SELECT revision FROM control_scans').fetchone()[0]!=expected_revision:
                raise APIError('CONFLICT','RESOURCE_REVISION_CONFLICT',409)
        with self.inbox_factory() as inbox: summary=inbox.scan_once(self.clock())
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute('UPDATE control_scans SET revision=revision+1 WHERE singleton=1 AND revision=?',(expected_revision,))
            if changed.rowcount!=1: raise APIError('CONFLICT','RESOURCE_REVISION_CONFLICT',409)
            receipt=self._receipt(command_id,actor,'inbox',expected_revision,expected_revision+1,'COMPLETE','inbox-scan:'+command_id,_stamp(self.clock()))
            db.execute('INSERT INTO control_scan_receipts VALUES(?,?,?,?)',(command_id,raw,json.dumps(receipt,sort_keys=True),json.dumps(asdict(summary),sort_keys=True)))
            return receipt
