# S09 continuous PAPER implementation ledger

Plan: `docs/product/v0_2/06_EXECUTION_PLAN.md`, S09. Authority: PAPER-01,
APP-01 and existing E2/E4/E5/E6 contracts. Base: a9a59381eef28220bddd713517867dfa4ed88cb9.
Status: IN_PROGRESS. Real provider calls/credentials/capital: zero/none/none.

1. Add E4-owned strict, versioned PaperBroker checkpoint/recovery. Preserve
   original acknowledgements separately from current order truth and actual
   fills. Recovered broker-issued retry permissions must be discarded.
2. Add E6 durable runtime operation/checkpoint storage, compare-and-swap
   generations, immutable receipts and first-fill exit anchors. Domain owner
   work runs outside SQLite transactions; each simulated effect has a durable
   intent and a deterministic identity, with recovery rather than blind retry.
3. Compose actual E2, E5, PaperBroker and E6 into PaperService and independently
   scheduled entry/protective/time-exit processing. Stale/unconfigured data,
   expiry, retirement/pause and unknown recovery deny entries while required
   management remains scheduled. Add real full-cycle and fault tests first.
4. Persist explicitly distinct fixture versus real elapsed observation evidence;
   implement selected-policy forward assessment without manufactured elapsed
   time. Demonstrate resource-limited research isolation from runtime.
5. Run affected/full tests, commit exact executable, qualify clean, retain all
   sanitized logs and Git blob hashes, push evidence and automatically begin S10.

Ruling: E4 snapshots describe the existing simulation broker; they grant no
financial or lifecycle authority. The E6/application wrapper binds run identity,
namespace and source/config generations. A restored broker must still undergo
actual reconciliation before application entry admission. Cost if wrong:
recovery remains blocked rather than silently resetting exposure.

Ruling: retain original ambiguous ACK even when an accepted order subsequently
fills. Reconstructing by submitting/filling again could lose ambiguity or create
duplicate exposure, so restore owner facts directly after strict validation.
Cost if wrong: a deterministic PAPER recovery is denied, with no real mutation.

## Durable-owner foundation checkpoint (S09 remains IN_PROGRESS)

Implemented E4 PaperBroker checkpoint/restore and strict execution-fact codecs;
E6 migration0011 with append-only run/intents/effects/checkpoints/publication and
process generations; E5 exit-anchor checkpoint and actual entry-fill projection
composition; application PaperCoordinator publishing through actual E6 APIs.
Recovery never grants entry permission. Old process generations cannot create
new effects. Unpublished canonical effects fence the next logical operation.
The old secret/provider vocabulary, floats, scalars and inconsistent financial
graphs are rejected. Both checkpoint and publication retain immutable hashes.

Observed REDs: broker checkpoint7 tests/9 errors (missing owner APIs); process
journal7 failures; effect/process fencing2 failures; exit-anchor recovery3
failures; broker validation inside transaction1 failure; entry observation3
failures; inconsistent entry average1 failure; publication recovery2 failures;
secret/scalar durability5 subtest failures. All corresponding repairs now pass:
30 focused tests, zero failures/errors/skips. Concurrent connection exclusion is
characterization after the journal implementation, not a claimed prior RED.

The publication recovery test uses actual E2 as-of evaluation, E5 explicit
RiskPolicy/RiskDecision/ApprovedTradePlan, E4 PaperBroker submit and E6 canonical
writers. Injecting a crash after RiskDecision persistence leaves the exact
applied bundle pending; restart completes its canonical graph without invoking
E2/E5/E4 again. This covers recovery foundation, not yet the continuous full
entry/fill/protection/exit/flat cycle, scheduler, real-forward producer or S09 PASS.

Ruling: compare canonical quantities/prices numerically as exact Decimal values;
accepted trailing-zero serialization is not a financial defect. An initial test
expected0.003 while the exact fill sum serialized0.0030; only this representation
assertion was corrected, with no threshold or financial check weakened.

Ruling: domain producer/validation runs outside SQLite transactions. Inside a
short writer transaction E6 checks retained canonical bytes/hashes and lineage;
recovery releases its read snapshot before constructing/validating E4 state.
Cost if wrong: fail-closed recovery blocks progress without holding a financial
producer/network/statistical operation inside the canonical writer lock.

Ruling: increased partial-entry quantity outgrowing an already verified stop
uses the existing PROTECTION_LOST -> EMERGENCY transition. It cannot silently
retain protected status or invent an OPEN_UNPROTECTED recovery edge. The added
actual E5/E4 characterization confirms this canonical behavior; the continuous
runtime must manage the emergency or cancel unfilled entry remainder before it
can occur. Cost if wrong: entries remain disabled and emergency management runs.

One characterization setup initially supplied an E5 projection as the exact E4
source Position; the owner correctly rejected its projection metadata. The test
now supplies the corresponding broker facts separately, with no guard weakened.
