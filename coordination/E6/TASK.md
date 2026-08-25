# E6 Current Task

- task_id: `E6-20260825-022`
- issued_at: `2026-08-25T12:10:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-gate-c-shadow-mode-20260825`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75 merge `c158c8ca4fd01fa9314dd2e7a1a9c0c0d2935624`, Product Owner Gate C / SHADOW-only authorization

## Objective

Close only the E6 Phase-1 Gate C gap from `status/e7/GATE_C_READINESS_BASELINE_20260825.md`: implement the existing shared `OperationalMode` contract as authoritative durable runtime state for SHADOW, with sanitized Shadow checkpoint/audit/restart semantics and strict separation from PAPER and LIVE authority.

Do not implement provider clients, risk derivation, strategy logic, or order execution.

## Required behavior

1. Persist the existing operational modes distinctly, including `RESEARCH`, `PAPER`, `SHADOW`, `LIVE`, `PAUSED`, and `LOCKED` exactly as defined by the accepted shared contract; do not create a parallel lifecycle enum.
2. The current Product Owner authority permits Gate C work and SHADOW readiness only. No path in this task may transition into or infer `LIVE`.
3. Operational mode must be authoritative backend state, not a UI-only label or transient process flag.
4. Persist an auditable mode transition record containing previous mode, new mode, timestamp, actor/source, reason/evidence reference, and revision/identity as appropriate.
5. Implement sanitized Shadow observation/checkpoint persistence sufficient to remember the last accepted provider-observation boundary without persisting secrets or prohibited sensitive provider/account material.
6. Restart must restore the exact operational mode and last accepted Shadow checkpoint.
7. If restart state is missing, contradictory, corrupt, or lacks required current provider evidence, recovery must fail closed and require fresh reconciliation before planning may be considered safe.
8. PAPER journal/evidence must not be silently reinterpreted as SHADOW provider truth.
9. SHADOW records/checkpoints must not become LIVE execution authority and there must be no automatic `SHADOW -> LIVE` transition.
10. Credential presence/provider availability must never imply mode promotion.

## Shadow checkpoint security boundary

Durable/public-safe Shadow checkpoint material may contain only sanitized fields such as:

- provider/environment classification;
- regional hostname classification/config reference without credentials;
- canonical/provider instrument identity;
- observation timestamps;
- permission category (`read_only` only when later observed);
- booleans/known-status and bounded counts such as market healthy, balance known, unexpected exposure, pending-order count, unreconciled-fill count;
- provider observation/hash/reference IDs generated internally by R7;
- fail-closed/degraded reason codes.

It must not persist raw API key/secret/passphrase/signature, raw UID/main UID/API label/bound IPs, exact account balances, provider order/fill IDs, complete provider responses, cookies, tokens, or browser-auth material.

## Tests

Add/update only E6-owned tests proving at minimum:

- each OperationalMode persists/restores distinctly;
- SHADOW is not strategy lifecycle state and cannot be conflated with PAPER/LIVE;
- authorized transition into SHADOW is auditable;
- no automatic/inferred SHADOW->LIVE path exists;
- credential/provider-presence-like metadata cannot promote mode;
- Shadow checkpoint survives restart with exact sanitized identity/freshness metadata;
- missing/corrupt/contradictory checkpoint causes fail-closed recovery requiring fresh reconciliation;
- PAPER evidence cannot satisfy SHADOW provider checkpoint requirements;
- SHADOW evidence cannot become LIVE execution authority;
- redaction/prohibited-field rejection prevents secret/sensitive material from entering durable Shadow evidence;
- migration/additive persistence behavior is deterministic and idempotent if a new E6 migration is required.

If a storage migration is needed, it must be additive, E6-owned, backward-compatible with accepted Gate B data, and covered by migration/restart tests. Do not redefine shared OperationalMode semantics.

## Executable verification

Product Owner authorizes approved-local, non-GitHub, **credential-free** verification for this bounded task. If the approved local runner is available, run only relevant E6 storage/platform tests after implementation, for example:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
```

No external provider network call or credential use is authorized in this task. If approved-local execution is unavailable, record `NOT_RUN` with exact commands. `NOT_RUN != PASS`.

## Writable scope

Only E6-owned paths needed for this task:

- `src/storage/**`;
- `src/platform/**`;
- `src/registry/**` only if the accepted architecture already places operational-mode state there;
- E6-owned migrations under `src/storage/migrations/**` if strictly necessary;
- `tests/storage/**`;
- `tests/platform/**`;
- `tests/registry/**` only if required by the chosen E6-owned persistence surface;
- bounded E6 docs;
- `coordination/E6/STATUS.md`.

Forbidden:

- provider/network/auth implementation;
- E1-E5/E7 production/tests;
- risk semantics;
- execution/order submission semantics;
- shared contract/ADR changes without escalation;
- credentials/secrets/raw provider-sensitive fixtures;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- PAPER/SHADOW runtime start;
- LIVE or any LIVE promotion mechanism;
- order/provider mutation/capital movement;
- unrelated cleanup.

## Acceptance

### DONE

- durable authoritative OperationalMode/SHADOW state, audit, sanitized checkpoint, restart and fail-closed separation are implemented;
- accepted Gate B persistence remains compatible;
- no provider/private work or credential use occurred;
- local evidence is PASS or explicitly `NOT_RUN` without misclassification;
- commit/push to target branch and terminal E6 STATUS.

### BLOCKED

If the existing OperationalMode contract is insufficient or a shared architecture decision is required, stop with exact evidence for E7 and do not invent semantics.

## Completion

Execute only this TASK, update `coordination/E6/STATUS.md`, commit/push required work to the target branch, and stop. Do not self-start E5 composition, provider verification, or another Gate C task.