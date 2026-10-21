"""Immutable published-prefix facts in the SAME E6 SQLite transaction.

These records are not historical-audit permission. The current integration keeps
the complete operation scan, verifies every fact and compares the indexed tail.
No serialized prefix or caller callback can stand in for a full history audit.
"""
import hashlib
import json
from datetime import datetime,timedelta

from .paper_state_codec import CODEC
from .runtime_models import RuntimeValidationError

PROFILE='r7-paper-published-prefix-v0.1'
ZERO='sha256:'+'0'*64


def _invalid():raise RuntimeValidationError('PAPER_CHECKPOINT_INVALID','Stored Paper published prefix invalid')


def _digest(raw):return 'sha256:'+hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _hash(value):return _digest(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False))


def _clock(value):
    if type(value) is not str:_invalid()
    try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:_invalid()
    if (parsed.utcoffset()!=timedelta(0)
            or parsed.isoformat(timespec='microseconds').replace('+00:00','Z')!=value):_invalid()
    return value


class PublishedPrefixes:
    def __init__(self,journal):self.journal=journal;self.db=journal._db

    def _available(self):
        return self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='paper_process_prefix_profiles'").fetchone() is not None

    def enabled(self,run_id):
        if not self._available():return False
        rows=self.db.execute('SELECT profile FROM paper_process_prefix_profiles WHERE run_id=? LIMIT 2',(run_id,)).fetchall()
        if not rows:
            if self.db.execute('SELECT 1 FROM paper_process_published_prefixes WHERE run_id=? LIMIT 1',(run_id,)).fetchone():_invalid()
            return False
        if len(rows)!=1 or rows[0]['profile']!=PROFILE:_invalid()
        return True

    def select_new(self,run_id,at):
        if self._available():self.db.execute('INSERT INTO paper_process_prefix_profiles VALUES(?,?,?)',(run_id,PROFILE,at))

    def _root(self,run_id):
        run=self.journal._run(run_id);checkpoint=self.journal._checkpoint(run_id,0)
        storage=self.db.execute('SELECT profile,created_at FROM paper_process_storage_profiles WHERE run_id=?',(run_id,)).fetchone()
        selected=self.db.execute('SELECT profile,created_at FROM paper_process_prefix_profiles WHERE run_id=?',(run_id,)).fetchone()
        at=_clock(checkpoint['recorded_at'])
        if (storage is None or selected is None or storage['profile']!=CODEC or selected['profile']!=PROFILE
                or _clock(run['created_at'])!=at or _clock(storage['created_at'])!=at or _clock(selected['created_at'])!=at):_invalid()
        material=dict(schema_version=PROFILE,run_id=run_id,revision=0,operation_id=None,
            previous_hash=ZERO,binding_hash=run['binding_hash'],state_hash=checkpoint['state_hash'],
            storage_profile=CODEC,run_created_at=run['created_at'],storage_selected_at=storage['created_at'],
            prefix_selected_at=selected['created_at'],recorded_at=at)
        return run_id,0,None,ZERO,_hash(material),checkpoint['recorded_at']

    def initialize(self,run_id):
        if self.enabled(run_id):
            self.db.execute('INSERT INTO paper_process_published_prefixes VALUES(?,?,?,?,?,?)',self._root(run_id))

    def _record(self,operation,previous_hash):
        publication=self.db.execute('SELECT * FROM paper_process_publications WHERE run_id=? AND operation_id=?',
            (operation.run_id,operation.operation_id)).fetchone()
        if (publication is None or publication['effect_hash']!=operation.effect_hash
                or operation.state_json is None or operation.outcome_json is None):_invalid()
        clocks=self.db.execute('''SELECT o.prepared_at,e.completed_at,b.recorded_at AS base_at,c.recorded_at AS checkpoint_at
            FROM paper_process_operations o JOIN paper_process_effects e USING(run_id,operation_id)
            JOIN paper_process_checkpoints b ON b.run_id=o.run_id AND b.revision=o.base_revision
            JOIN paper_process_checkpoints c ON c.run_id=e.run_id AND c.revision=e.checkpoint_revision
            WHERE o.run_id=? AND o.operation_id=?''',(operation.run_id,operation.operation_id)).fetchone()
        if clocks is None:_invalid()
        prepared,completed=_clock(clocks['prepared_at']),_clock(clocks['completed_at'])
        if not _clock(clocks['base_at'])<=prepared<=completed==_clock(clocks['checkpoint_at'])<=_clock(publication['published_at']):_invalid()
        material=dict(schema_version=PROFILE,run_id=operation.run_id,revision=operation.checkpoint_revision,
            operation_id=operation.operation_id,previous_hash=previous_hash,request_hash=_digest(operation.request_json),
            state_hash=_digest(operation.state_json),outcome_hash=_digest(operation.outcome_json),
            effect_hash=operation.effect_hash,prepared_at=prepared,completed_at=completed,recorded_at=publication['published_at'])
        return (operation.run_id,operation.checkpoint_revision,operation.operation_id,
            previous_hash,_hash(material),publication['published_at'])

    def append_published(self,operation):
        if not self.enabled(operation.run_id):return
        previous=self.db.execute('SELECT prefix_hash FROM paper_process_published_prefixes WHERE run_id=? AND revision=?',
            (operation.run_id,operation.checkpoint_revision-1)).fetchone()
        if previous is None:_invalid()
        wanted=self._record(operation,previous['prefix_hash'])
        existing=self.db.execute('SELECT * FROM paper_process_published_prefixes WHERE run_id=? AND revision=?',
            (operation.run_id,operation.checkpoint_revision)).fetchone()
        if existing is not None:
            if tuple(existing)!=wanted:_invalid()
        else:self.db.execute('INSERT INTO paper_process_published_prefixes VALUES(?,?,?,?,?,?)',wanted)

    def audit_start(self,run_id):
        if not self.enabled(run_id):return None
        wanted=self._root(run_id)
        root=self.db.execute('SELECT * FROM paper_process_published_prefixes WHERE run_id=? AND revision=0',(run_id,)).fetchone()
        if root is None or tuple(root)!=wanted:_invalid()
        return dict(run_id=run_id,revision=0,prefix_hash=wanted[4],pending=0,applied=0)

    def audit_operation(self,context,operation):
        if context is None:return
        if context['pending']:_invalid()
        if operation.status!='PUBLISHED':
            if operation.base_revision!=context['revision']:_invalid()
            context['pending']=1
            context['applied']=int(operation.status=='APPLIED')
            return
        if operation.checkpoint_revision!=context['revision']+1:_invalid()
        wanted=self._record(operation,context['prefix_hash'])
        row=self.db.execute('SELECT * FROM paper_process_published_prefixes WHERE run_id=? AND revision=?',
            (context['run_id'],operation.checkpoint_revision)).fetchone()
        if row is None or tuple(row)!=wanted:_invalid()
        context.update(revision=operation.checkpoint_revision,prefix_hash=wanted[4])

    def indexed_pending(self,context):
        rows=self.db.execute('''SELECT o.operation_id FROM paper_process_operations o
            LEFT JOIN paper_process_publications p USING(run_id,operation_id)
            WHERE o.run_id=? AND o.base_revision>=? AND p.operation_id IS NULL
            ORDER BY o.base_revision,o.operation_id LIMIT 2''',(context['run_id'],context['revision'])).fetchall()
        return tuple(row['operation_id'] for row in rows)

    def current_context(self,run_id):
        """Bounded current facts only; never a complete-history audit proof."""
        context=self.audit_start(run_id)
        if context is None:return None
        tip=self.db.execute('SELECT * FROM paper_process_published_prefixes WHERE run_id=? ORDER BY revision DESC LIMIT 1',
            (run_id,)).fetchone()
        if tip is None:_invalid()
        if tip['revision']==0:return context
        previous=self.db.execute('SELECT prefix_hash FROM paper_process_published_prefixes WHERE run_id=? AND revision=?',
            (run_id,tip['revision']-1)).fetchone()
        operation=self.journal.operation(run_id,tip['operation_id'])
        if (previous is None or operation is None or operation.status!='PUBLISHED'
                or operation.checkpoint_revision!=tip['revision']):_invalid()
        wanted=self._record(operation,previous['prefix_hash'])
        if tuple(tip)!=wanted:_invalid()
        context.update(revision=tip['revision'],prefix_hash=tip['prefix_hash'])
        return context

    def audit_finish(self,context,pending,checkpoint_revision):
        if context is None:return
        count=self.db.execute('SELECT count(*) FROM paper_process_published_prefixes WHERE run_id=?',(context['run_id'],)).fetchone()[0]
        tail=self.indexed_pending(context)
        if count!=context['revision']+1 or len(tail)>1 or tuple(pending)!=tail:_invalid()
        if checkpoint_revision!=context['revision']+context['applied']:_invalid()
        for table,expected in (('paper_process_operations',context['revision']+context['pending']),
                ('paper_process_effects',context['revision']+context['applied']),
                ('paper_process_checkpoints',context['revision']+context['applied']+1),
                ('paper_process_publications',context['revision'])):
            actual=self.db.execute('SELECT count(*) FROM '+table+' WHERE run_id=?',(context['run_id'],)).fetchone()[0]
            if actual!=expected:_invalid()
