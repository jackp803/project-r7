# Gate A Local Rerun 4 Evidence — E7-20260824-024

## Authority

- task_id: `E7-20260824-024`
- target_branch: `agent/e7-gate-a-local-rerun4-20260824`
- approved project source revision: `4da559bbbb569ea4f32246a40ef35f4bd8477a71`
- approved environment: `current Windows local development computer`
- required worktree state: `detached HEAD / HEAD=4da559bbbb569ea4f32246a40ef35f4bd8477a71 / CLEAN`
- preparation evidence: `JOB-F53BD229F125 / SUCCEEDED`
- AgentBridge runtime fix: `ed57928b228720f0876f0060224ed532b17fd799`
- AgentBridge PR #6 head: `af6ae97f96e172572496de987cfb96f261f58e0c`
- GitHub compute used: `NO`
- GitHub Actions / CI / hosted runners: `NOT_USED`
- provider/private requests: `NOT_SENT`
- PAPER/SHADOW/LIVE: `NOT_USED`
- Registry real promotion: `NONE`
- production/test/contract changes to force PASS: `NONE`

## Fresh ordered matrix

### 1. GATE_A_MARKET_DATA — PASS

```text
request_id = REQ-E7-GATEA-024-01-4E2B6C91
action_id = GATE_A_MARKET_DATA
job_id = JOB-14EAF870409F7BF8
state = SUCCEEDED
exit_code = 0
duration_seconds = 0.547
Ran 21 tests in 0.007s
OK
```

Registered command:

```powershell
python -m unittest discover -s tests/market_data -p "test_*.py" -v
```

Observed coverage includes Candle contract validation, OKX normalization, historical sequence integrity, and market-data import integrity.

### 2. GATE_A_INDICATORS — PASS

```text
request_id = REQ-E7-GATEA-024-02-7B91D4E2
action_id = GATE_A_INDICATORS
job_id = JOB-B6401E246AEE0542
state = SUCCEEDED
exit_code = 0
duration_seconds = 0.312
Ran 3 tests in 0.001s
OK
```

Registered command:

```powershell
python -m unittest discover -s tests/indicators -p "test_*.py" -v
```

Delivered stderr confirms exact Decimal SMA behavior, binary-float rejection, and insufficient-history handling.

### 3. GATE_A_STRATEGY — PASS

```text
request_id = REQ-E7-GATEA-024-03-5C8A1F77
action_id = GATE_A_STRATEGY
job_id = JOB-2D6AB3BA7A887087
state = SUCCEEDED
exit_code = 0
duration_seconds = 0.375
Ran 21 tests in 0.009s
OK
```

Registered command:

```powershell
python -m unittest discover -s tests/strategy -p "test_*.py" -v
```

Delivered stderr confirms parser/schema/runtime-version validation, deterministic runtime behavior, no-look-ahead protections, closed-candle enforcement, structured schema rejects, and TradeIntent entry-profile boundary tests.

### 4. GATE_A_BACKTEST — PASS

```text
request_id = REQ-E7-GATEA-024-04-9D3F6A20
action_id = GATE_A_BACKTEST
job_id = JOB-CB2A624F87270A7D
state = SUCCEEDED
exit_code = 0
duration_seconds = 0.750
Ran 21 tests in 0.012s
OK
```

Registered command:

```powershell
python -m unittest discover -s tests/backtest -p "test_*.py" -v
```

Delivered stderr confirms fee/slippage/funding behavior, metrics, actual E2 runtime consumption in the E1→E2→E3 research skeleton, dataset binding, closed-prefix/no-look-ahead behavior, next-open fills, conservative same-candle ambiguity handling, and fail-closed schema checks.

### 5. GATE_A_VALIDATION — PASS

```text
request_id = REQ-E7-GATEA-024-05-A71C2E94
action_id = GATE_A_VALIDATION
job_id = JOB-2C31FA616EC7E442
state = SUCCEEDED
exit_code = 0
duration_seconds = 0.359
Ran 15 tests in 0.007s
OK
```

Registered command:

```powershell
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

Delivered stderr confirms OOS binding checks, binary-float fail-closed behavior, canonical PASS under explicit OOS bindings/thresholds, no Registry/lifecycle authority, E6 contract acceptance, NOT_RUN non-promotion, stable quantitative failure ordering, and schema/type fail-closed behavior.

### 6. GATE_A_REGISTRY — PASS

```text
request_id = REQ-E7-GATEA-024-06-C4E8B129
action_id = GATE_A_REGISTRY
job_id = JOB-B330F8AA8F17A773
state = SUCCEEDED
exit_code = 0
duration_seconds = 0.469
Ran 19 tests in 0.066s
OK
```

Registered command:

```powershell
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

Delivered stderr confirms fail-closed BacktestResult/ValidationDecision validation, Decimal/RFC3339 interchange enforcement, lifecycle authority capped at CANDIDATE, durable local E2 PASS requirements, content-hash/idempotency handling, secret-like field rejection, and no approval/live path.

### 7. GATE_A_STORAGE — PASS

```text
request_id = REQ-E7-GATEA-024-07-D5A7C318
action_id = GATE_A_STORAGE
job_id = JOB-EEFC8AE652AD4B0A
state = SUCCEEDED
exit_code = 0
duration_seconds = 0.687
Ran 26 tests in 0.280s
OK
```

Registered command:

```powershell
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Delivered stderr confirms CANDIDATE lifecycle evidence authority, durable E2 authority requirements, rollback on unauthorized transition, public persistence boundary restrictions, no public raw writer/connection authority, DRAFT revision-zero intake, exact early lifecycle-edge enforcement, append-only history, migration idempotence, immutable strategy content, and restart persistence.

### 8. GATE_A_INTEGRATION — PASS

```text
request_id = REQ-E7-GATEA-024-08-E6B2F4C7
action_id = GATE_A_INTEGRATION
job_id = JOB-3091E94AD96AF7A2
state = SUCCEEDED
exit_code = 0
duration_seconds = 0.547
Ran 1 test in 0.008s
OK
```

Registered command:

```powershell
python -m unittest discover -s tests/integration -p "test_*.py" -v
```

Delivered stderr confirms the real cross-role research pipeline is canonical while synthetic PASS evidence has no promotion authority.

## Matrix summary

```text
1. GATE_A_MARKET_DATA = PASS / 21 tests
2. GATE_A_INDICATORS  = PASS / 3 tests
3. GATE_A_STRATEGY    = PASS / 21 tests
4. GATE_A_BACKTEST    = PASS / 21 tests
5. GATE_A_VALIDATION  = PASS / 15 tests
6. GATE_A_REGISTRY    = PASS / 19 tests
7. GATE_A_STORAGE     = PASS / 26 tests
8. GATE_A_INTEGRATION = PASS / 1 test

TOTAL = 127 tests reported / zero failure or error
LOCAL_EXECUTION_MATRIX = PASS
GATE_A_REVIEW_CANDIDATE = YES
```

Every request/result identity matched `E7-20260824-024` and the ordered target-branch mailbox request. AgentBridge delivered each durable execution-result notification to the E7 conversation. No suite reported source/worktree mismatch, failure, error, timeout, or refusal.

## Evidence limitations

The user-visible execution-result excerpts do not separately expose Python executable/version, OS identity, cwd, explicit detached-HEAD/clean-worktree fields, SQLite row identifiers, or execution-count fields. E7 does not fabricate values that were not delivered in the notification. The TASK-approved exact source pin, required detached-clean worktree, approved Windows environment, and preparation evidence remain the governing execution constraints; no mismatch was reported by any of the eight successful Local Runner jobs.

## Terminal interpretation

```text
LOCAL_EXECUTION_MATRIX = PASS
GATE_A_REVIEW_CANDIDATE = YES
Gate A = NOT DECLARED PASS / SEPARATE PM-E7 EVIDENCE REVIEW REQUIRED
Gate B/C/D = BLOCKED / UNCHANGED
PAPER/SHADOW/LIVE = UNAUTHORIZED / UNCHANGED
```

This task establishes a fresh complete local Gate A execution matrix only. It does not itself approve Gate A, start the Gate A release review, authorize provider/private work, promote any strategy, or authorize PAPER/SHADOW/LIVE.
