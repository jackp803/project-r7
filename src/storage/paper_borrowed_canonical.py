"""Trusted, sequential Paper-only reuse of the existing E6 process connection.

Not transaction composition: every original canonical writer still commits its
own fact. Never used for the distinct trading/financial journal authorities.
"""
from functools import wraps

from ._paper_runtime import _PaperRuntimeStore
from .canonical_publication import CANONICAL_WRITERS
from .runtime import PaperRuntimeJournal
from .runtime_models import RuntimeValidationError


def _invalid(reason):
    raise RuntimeValidationError('PAPER_BORROWED_CANONICAL_INVALID',reason)


class _BorrowedStore(_PaperRuntimeStore):
    def close(self):pass  # The process journal owns this connection.


class BorrowedPaperRuntimeJournal(PaperRuntimeJournal):
    __slots__=('_owner','_closed','_previous_isolation','_reading')

    def __init__(self,owner):
        if owner._db.in_transaction or owner._borrowed_canonical is not None:
            _invalid('One idle process owner connection is required')
        self._owner=owner;self._closed=False;self._reading=0
        self._previous_isolation=owner._db.isolation_level
        # Canonical conflict recording retains its original implicit single-fact
        # transaction semantics; principal writers already use explicit BEGIN.
        owner._db.isolation_level=''
        super().__init__(_BorrowedStore(owner._db))
        owner._borrowed_canonical=self

    def _idle(self):
        if self._closed or self._owner._borrowed_canonical is not self:
            _invalid('Borrowed canonical facade is closed')
        if self._owner._db.in_transaction:
            _invalid('Canonical call cannot enter or roll back a lender transaction')

    def __enter__(self):
        self._idle();return self

    def close(self):
        if self._closed:return
        self._idle()
        self._owner._db.isolation_level=self._previous_isolation
        self._owner._borrowed_canonical=None;self._closed=True

    def _lender_closed(self):
        self._closed=True

    def publish_canonical_effects(self,effects):
        self._idle()
        # Fixed inner writers get individual boundaries, preserving partial
        # publication and exact replay. No bundle transaction is introduced.
        return super().publish_canonical_effects(effects)


def _borrowed_call(function):
    @wraps(function)
    def call(self,*args,**kwargs):
        self._idle();db=self._owner._db
        with self._owner._history.owned_write('CANONICAL',None):
            try:
                result=function(self,*args,**kwargs)
                if db.in_transaction:_invalid('Canonical writer returned an unfinished transaction')
                return result
            except BaseException:
                db.rollback();raise
    return call


def _borrowed_read(function):
    @wraps(function)
    def call(self,*args,**kwargs):
        nested=self._reading>0
        if not nested:self._idle()
        elif function.__name__!='recover':_invalid('Only canonical recovery may reuse its own read snapshot')
        self._reading+=1
        try:
            result=function(self,*args,**kwargs)
            if not nested and self._owner._db.in_transaction:
                _invalid('Canonical reader returned an unfinished snapshot')
            return result
        finally:
            self._reading-=1
            if not nested and self._owner._db.in_transaction:self._owner._db.rollback()
    return call


for _name in CANONICAL_WRITERS.values():
    setattr(BorrowedPaperRuntimeJournal,_name,_borrowed_call(getattr(PaperRuntimeJournal,_name)))
for _name in ('recover','current_execution_subject','require_current_execution_subject'):
    setattr(BorrowedPaperRuntimeJournal,_name,_borrowed_read(getattr(PaperRuntimeJournal,_name)))
