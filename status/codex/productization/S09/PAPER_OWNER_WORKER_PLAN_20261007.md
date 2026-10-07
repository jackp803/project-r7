# Independent PAPER owner implementation checkpoint

Task: CODEX-R7-PRODUCTIZATION-MASTER-20261002; r7-product-v0.2.

The unfinished S09/S13 integration needs a runtime-role process that opens its
actual E6/PAPER connections on its own thread, discovers accepted starts, and
keeps protective management independent of acquisition and research. This
component consumes the existing PaperService; it issues no qualification receipt
or financial permission. Production release admission continues to require the
unresolved qualified-release profile. No real provider or capital is involved.

1. Add actual-owner regression cases before implementation and observe intended
   failures for the missing worker. Use one canonical fixture database and actual
   research, registry, process journal, broker, scheduler and API control ports.
2. Add `src/application/paper/worker.py`: runtime-role ProcessSupervisor scope
   before factory/attachments, owner-thread connection lifetime, bounded accepted
   start discovery and acquisition queues, existing deadline-first schedulers,
   explicit capacity/attachment failure states and cooperative ManagedStop.
   API reads/pause/start must not attach or replace the runtime generation.
3. Verify singleton admission, restart fencing/reconciliation, actual ACK/fill/
   protection/target closure, pause and queue-pressure deadline priority, thread
   confinement, profile drift, and factory cleanup on failed composition.
4. Review and repair findings with regression coverage. Commit an exact-clean
   candidate, run appropriate source qualification and persist sanitized counts,
   commands, identities, limitations and hashes. Continue native composition,
   qualification issuer/adapters and packaged fixture probes afterward; source
   component tests do not complete ordinary native PAPER or cross-platform
   acceptance.

Ownership: worker module, its application tests/fixture helper, and this evidence.
Preserve canonical E2/E4/E5/E6 behavior and existing test thresholds. An empty or
capacity-limited worker never reports exposure as flat or all runs as managed.
