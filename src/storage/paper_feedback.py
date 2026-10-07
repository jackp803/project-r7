"""Bounded immutable feedback outbox in the existing actual PAPER owner store.

Report production and HTTP calls occur outside write transactions. The writer
atomically binds a report to the unchanged current run/checkpoint/generation.
Publishing historical reports never attaches or renews a runtime owner lease.
"""
import json
from application.cloud.feedback import FeedbackError
from application.cloud.manifest import byte_hash,canonical_bytes
from application.cloud.paper_feedback import build_paper_feedback,paper_feedback_bundle,validate_paper_feedback_publication
from application.cloud.protocol import ArtifactBundle,CloudError
from application.cloud.publisher import PublishSummary
from .paper_process import PaperProcessJournal,_digest,_stamp
from .runtime_models import RuntimeConflictError,RuntimeValidationError

MAX_PENDING=1000
MAX_PENDING_BYTES=16*1024*1024

def _artifact(payloads):return byte_hash(canonical_bytes({name:byte_hash(raw) for name,raw in payloads.items()}))

class PaperFeedbackOutbox:
    def __init__(self,journal):
        if type(journal) is not PaperProcessJournal:raise FeedbackError('ACTUAL_PAPER_FEEDBACK_JOURNAL_REQUIRED')
        self.journal=journal

    def queue(self,runtime,*,performance_opt_in=False,fault_hook=None):
        from application.paper.service import PaperRuntime
        if type(runtime) is not PaperRuntime or runtime.service.process is not self.journal:
            raise FeedbackError('SAME_ACTUAL_PAPER_FEEDBACK_OWNER_REQUIRED')
        if self.journal._db.in_transaction:raise FeedbackError('PAPER_FEEDBACK_IDLE_OWNER_CONNECTION_REQUIRED')
        before=self.journal.recover(runtime.run_id)
        feedback=build_paper_feedback(runtime,performance_opt_in=performance_opt_in)
        if feedback['assessment']['run_revision']!=before.revision or feedback['producer']['process_generation']!=before.process_generation:
            raise FeedbackError('PAPER_FEEDBACK_CHECKPOINT_CHANGED')
        bundle=paper_feedback_bundle(feedback);raw=canonical_bytes(feedback);commitment=byte_hash(raw)
        payloads=canonical_bytes({name:value.decode('utf-8') for name,value in bundle.payloads.items()}).decode('utf-8')
        artifact=_artifact(bundle.payloads);operation='r7-paper-feedback-'+commitment[7:]
        if len(raw)>256*1024 or len(payloads.encode('utf-8'))>1024*1024:
            raise FeedbackError('PAPER_FEEDBACK_PUBLICATION_LIMIT')
        if fault_hook is not None:fault_hook('AFTER_REPORT_BEFORE_OUTBOX')
        at=_stamp(runtime.service.clock())
        try:
            with self.journal._write():
                self.journal._require_process(runtime.run_id,before.process_generation)
                if runtime.coordinator.generation!=before.process_generation:
                    raise FeedbackError('PAPER_FEEDBACK_RUNTIME_GENERATION_CHANGED')
                run=self.journal._run(runtime.run_id);checkpoint=self.journal._checkpoint(runtime.run_id)
                if (run['binding_json']!=before.binding_json or checkpoint['revision']!=before.revision
                        or checkpoint['state_hash']!=_digest(before.state_json)):
                    raise FeedbackError('PAPER_FEEDBACK_CHECKPOINT_CHANGED')
                existing=self.journal._db.execute('SELECT * FROM paper_feedback_publications WHERE operation_id=?',(operation,)).fetchone()
                if existing is not None:
                    expected=(runtime.run_id,before.revision,before.process_generation,run['binding_hash'],checkpoint['state_hash'],raw.decode('utf-8'),
                        commitment,bundle.logical_path,payloads,artifact)
                    if tuple(existing[key] for key in ('run_id','run_revision','process_generation','binding_hash','checkpoint_state_hash','feedback_json',
                            'feedback_hash','logical_path','payloads_json','artifact_hash'))!=expected:
                        raise FeedbackError('IMMUTABLE_PAPER_FEEDBACK_CONFLICT')
                    return operation
                count,size=self.journal._db.execute("SELECT count(*),coalesce(sum(length(CAST(payloads_json AS BLOB))),0) FROM paper_feedback_publications WHERE state!='CLOUD_ACKNOWLEDGED'").fetchone()
                if count>=MAX_PENDING or size+len(payloads.encode('utf-8'))>MAX_PENDING_BYTES:
                    raise FeedbackError('PAPER_FEEDBACK_OUTBOX_CAPACITY')
                self.journal._db.execute('INSERT INTO paper_feedback_publications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (operation,runtime.run_id,before.revision,before.process_generation,run['binding_hash'],checkpoint['state_hash'],
                        raw.decode('utf-8'),commitment,bundle.logical_path,payloads,artifact,'PENDING',0,at))
        except (RuntimeConflictError,RuntimeValidationError):
            raise FeedbackError('PAPER_FEEDBACK_DURABLE_OWNER_WRITE_REFUSED') from None
        return operation

    def _check_record(self,row):
        raw=row['feedback_json'].encode('utf-8');encoded=row['payloads_json'].encode('utf-8')
        if len(raw)>256*1024 or len(encoded)>1024*1024 or byte_hash(raw)!=row['feedback_hash']:
            raise FeedbackError('PAPER_FEEDBACK_STORED_REPORT_CHANGED')
        payloads={name:value.encode('utf-8') for name,value in json.loads(encoded).items()}
        validate_paper_feedback_publication(row['logical_path'],payloads)
        if payloads['feedback.json']!=raw or _artifact(payloads)!=row['artifact_hash'] or row['operation_id']!='r7-paper-feedback-'+row['feedback_hash'][7:]:
            raise FeedbackError('PAPER_FEEDBACK_STORED_BUNDLE_CHANGED')
        run=self.journal._run(row['run_id']);checkpoint=self.journal._checkpoint(row['run_id'],row['run_revision'])
        generation=self.journal._db.execute('SELECT instance_id FROM paper_process_generations WHERE run_id=? AND generation=?',
            (row['run_id'],row['process_generation'])).fetchone()
        document=json.loads(raw);binding=json.loads(run['binding_json'])
        if (run['binding_hash']!=row['binding_hash'] or checkpoint['state_hash']!=row['checkpoint_state_hash'] or generation is None
                or document['run_id']!=row['run_id'] or document['assessment']['run_revision']!=row['run_revision']
                or document['producer']['process_generation']!=row['process_generation']
                or document['producer']['process_instance_hash']!=byte_hash(generation['instance_id'].encode('utf-8'))
                or document['namespace']!=binding['namespace'] or document['observation']['mode']!=binding['mode']
                or document['source']['implementation_hash']!=binding['implementation_hash']
                or document['strategy']!=dict(strategy_id=binding['strategy_id'],strategy_version=binding['strategy_version'],content_hash=binding['strategy_content_hash'])
                or document['binding']!={key:binding[key] for key in ('config_hash','risk_policy_hash','paper_policy_hash')}):
            raise FeedbackError('PAPER_FEEDBACK_STORED_LINEAGE_CHANGED')
        return ArtifactBundle(row['logical_path'],payloads)

    def pending(self,limit):
        if type(limit) is not int or not 1<=limit<=100:raise FeedbackError('BOUNDED_PAPER_FEEDBACK_BATCH_REQUIRED')
        rows=self.journal._db.execute("SELECT * FROM paper_feedback_publications WHERE state IN ('PENDING','LOCAL_STAGED','UNAVAILABLE') ORDER BY operation_id LIMIT ?",(limit,)).fetchall()
        return tuple((row['operation_id'],self._check_record(row),row['artifact_hash']) for row in rows)

    def publications(self,limit=100):
        if type(limit) is not int or not 1<=limit<=100:raise FeedbackError('BOUNDED_PAPER_FEEDBACK_BATCH_REQUIRED')
        return [dict(row) for row in self.journal._db.execute('SELECT operation_id,run_id,run_revision,process_generation,feedback_hash,artifact_hash,state,attempts FROM paper_feedback_publications ORDER BY operation_id LIMIT ?',(limit,)).fetchall()]

    def _record(self,operation,status,artifact_hash=None):
        if status not in ('LOCAL_STAGED','CLOUD_ACKNOWLEDGED','UNAVAILABLE','CONFLICT'):
            raise FeedbackError('PAPER_FEEDBACK_PUBLICATION_STATUS_INVALID')
        with self.journal._write():
            row=self.journal._db.execute('SELECT artifact_hash,state FROM paper_feedback_publications WHERE operation_id=?',(operation,)).fetchone()
            if row is None or status in ('LOCAL_STAGED','CLOUD_ACKNOWLEDGED') and row['artifact_hash']!=artifact_hash:
                raise FeedbackError('PAPER_FEEDBACK_ACK_IDENTITY_CHANGED')
            if row['state']=='CLOUD_ACKNOWLEDGED':
                if status!='CLOUD_ACKNOWLEDGED':raise FeedbackError('PAPER_FEEDBACK_ACK_CANNOT_REGRESS')
                return
            self.journal._db.execute('UPDATE paper_feedback_publications SET state=?,attempts=attempts+1 WHERE operation_id=?',(status,operation))

    def flush(self,transport,*,limit,fault_hook=None):
        if self.journal._db.in_transaction:raise FeedbackError('PAPER_FEEDBACK_IDLE_OWNER_CONNECTION_REQUIRED')
        items=self.pending(limit);counts=dict(local_staged=0,cloud_acknowledged=0,unavailable=0,conflicts=0)
        for operation,bundle,expected in items:
            try:
                receipt=transport.publish(bundle,operation)
                if fault_hook is not None:fault_hook('AFTER_UPLOAD_BEFORE_ACK')
                if receipt.operation_id!=operation or receipt.artifact_hash!=expected or receipt.status not in ('LOCAL_STAGED','CLOUD_ACKNOWLEDGED'):
                    raise CloudError('UNAVAILABLE','PAPER_FEEDBACK_TRANSPORT_RECEIPT_INVALID')
                self._record(operation,receipt.status,receipt.artifact_hash)
                counts['local_staged' if receipt.status=='LOCAL_STAGED' else 'cloud_acknowledged']+=1
            except CloudError as error:
                status='CONFLICT' if error.code=='CONFLICT' else 'UNAVAILABLE';self._record(operation,status)
                counts['conflicts' if status=='CONFLICT' else 'unavailable']+=1
        return PublishSummary(len(items),**counts)
