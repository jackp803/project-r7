"""Recover exact owner-produced simulation effects and canonical publication.

Producer composition is trusted local code, not an API/cloud payload. E2/E5/E4
work precedes the short E6 effect transaction. Publication failures retain their
exact pending bundle, so recovery never renews plans or repeats simulated fills.
"""
from dataclasses import dataclass
import json
import re
from typing import Callable

from storage.paper_process import PaperProcessJournal
from storage.runtime import PaperRuntimeJournal
from storage.runtime_models import RuntimeValidationError
from storage.canonical_publication import CANONICAL_WRITERS as _WRITERS

_STATUSES = {'ACKNOWLEDGED', 'BLOCKED', 'NO_SIGNAL', 'FILLED', 'PROTECTED',
             'EXIT_REQUESTED', 'CLOSED', 'HOLD', 'PAUSED', 'RECOVERED', 'EXPIRED'}


@dataclass(frozen=True)
class PaperStep:
    state: dict
    effects: list[dict]
    status: str
    reason_codes: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.state, dict) or set(self.state) != {'broker', 'runtime'}:
            raise ValueError('Explicit owner broker/runtime state required')
        if not isinstance(self.effects, list) or len(self.effects) > 5000:
            raise ValueError('Bounded canonical publication effects required')
        for effect in self.effects:
            if (not isinstance(effect, dict) or set(effect) != {'kind', 'payload'} or
                effect['kind'] not in _WRITERS or not isinstance(effect['payload'], dict)):
                raise ValueError('Supported canonical owner effect required')
        if self.status not in _STATUSES or not isinstance(self.reason_codes, tuple) or len(self.reason_codes) > 64:
            raise ValueError('Explicit Paper outcome required')
        if any(not isinstance(code, str) or not re.fullmatch('[A-Z][A-Z0-9_]{0,127}', code) for code in self.reason_codes):
            raise ValueError('Sanitized stable Paper reasons required')


@dataclass(frozen=True)
class RuntimeOutcome:
    run_id: str
    operation_id: str
    revision: int
    status: str
    reason_codes: tuple[str, ...]
    effect_hash: str
    # This is an immutable operation receipt, not current admission permission.


class PaperCoordinator:
    def __init__(self, process_journal: PaperProcessJournal,
                 canonical_journal: PaperRuntimeJournal, run_id: str,
                 process_generation: int, producer: Callable, *, clock: Callable):
        if (not isinstance(process_journal, PaperProcessJournal) or
            not isinstance(canonical_journal, PaperRuntimeJournal) or
            not callable(producer) or not callable(clock)):
            raise ValueError('Actual E6 journals and trusted local Paper composition required')
        self.process = process_journal; self.canonical = canonical_journal
        self.run_id = run_id; self.generation = process_generation
        self.producer = producer; self.clock = clock

    def _publish(self, operation):
        if operation.status == 'PUBLISHED': return operation
        if operation.status != 'APPLIED': raise ValueError('Only applied effects may publish')
        outcome = operation.outcome
        if (not isinstance(outcome, dict) or set(outcome) != {'effects', 'status', 'reason_codes'}):
            raise RuntimeValidationError('PAPER_OUTBOX_INVALID', 'Exact Paper publication bundle required')
        # Revalidate trusted retained output before dispatch. No function names or
        # filesystem paths from an untrusted request can choose an E6 writer.
        PaperStep(operation.state, outcome['effects'], outcome['status'], tuple(outcome['reason_codes']))
        self.canonical.publish_canonical_effects(outcome['effects'])
        self.process.mark_published(self.run_id, operation.operation_id, operation.effect_hash, now=self.clock())
        return self.process.operation(self.run_id, operation.operation_id)

    def _finish(self, operation):
        if operation.status == 'PREPARED':
            now = self.clock()
            step = self.producer(operation.base_state, operation.request, now)
            if not isinstance(step, PaperStep): raise ValueError('Actual PaperStep producer output required')
            # Snapshot producer output immediately; a retained reference cannot
            # mutate the immutable effect after the E6 boundary accepts it.
            snapshot = json.loads(json.dumps(step.state, allow_nan=False))
            outcome = json.loads(json.dumps(dict(effects=step.effects, status=step.status,
                                                reason_codes=list(step.reason_codes)), allow_nan=False))
            operation = self.process.complete(self.run_id, operation.operation_id, snapshot, outcome,
                now=self.clock(), process_generation=self.generation)
        operation = self._publish(operation)
        outcome = operation.outcome
        return RuntimeOutcome(self.run_id, operation.operation_id, operation.checkpoint_revision,
                              outcome['status'], tuple(outcome['reason_codes']), operation.effect_hash)

    def execute(self, operation_id: str, request: dict) -> RuntimeOutcome:
        existing = self.process.operation(self.run_id, operation_id)
        revision = existing.base_revision if existing else self.process.recover(self.run_id).revision
        operation = self.process.prepare(self.run_id, operation_id, request,
            expected_revision=revision, now=self.clock(), process_generation=self.generation)
        return self._finish(operation)

    def recover_pending(self) -> tuple[RuntimeOutcome, ...]:
        recovered = self.process.recover(self.run_id)
        return tuple(self._finish(self.process.operation(self.run_id, operation_id))
                     for operation_id in recovered.pending_operations)
