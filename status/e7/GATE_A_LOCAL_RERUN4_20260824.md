# Gate A Local Rerun 4 Evidence — E7-20260824-024

## Authority

- task_id: `E7-20260824-024`
- target_branch: `agent/e7-gate-a-local-rerun4-20260824`
- approved project source revision: `4da559bbbb569ea4f32246a40ef35f4bd8477a71`
- approved environment: `current Windows local development computer`
- preparation evidence: `JOB-F53BD229F125 / SUCCEEDED`
- AgentBridge runtime fix: `ed57928b228720f0876f0060224ed532b17fd799`
- GitHub compute used: `NO`
- provider/private requests: `NOT_SENT`
- PAPER/SHADOW/LIVE: `NOT_USED`
- Registry real promotion: `NONE`

## Fresh ordered matrix

### 1. GATE_A_MARKET_DATA — PASS

```text
request_id = REQ-E7-GATEA-024-01-4E2B6C91
task_id = E7-20260824-024
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

Observed coverage includes Candle contract validation, OKX normalization, historical sequence integrity, and market-data import integrity. All 21 reported tests passed.

### 2. GATE_A_INDICATORS — PASS

```text
request_id = REQ-E7-GATEA-024-02-7B91D4E2
task_id = E7-20260824-024
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

Delivered stderr confirms exact Decimal SMA behavior, binary-float rejection, and insufficient-history handling all passed.

### 3. GATE_A_STRATEGY — PASS

```text
request_id = REQ-E7-GATEA-024-03-5C8A1F77
task_id = E7-20260824-024
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

Delivered stderr confirms parser/schema/runtime-version validation, deterministic runtime behavior, no-look-ahead protections, closed-candle enforcement, structured schema rejects, and TradeIntent entry-profile boundary tests all passed.

### 4. GATE_A_BACKTEST — PASS

```text
request_id = REQ-E7-GATEA-024-04-9D3F6A20
task_id = E7-20260824-024
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

Delivered stderr confirms deterministic fee/slippage/funding cost handling, defined metrics including null profit-factor semantics, actual E2 runtime consumption in the E1→E2→E3 research skeleton, dataset binding, closed-prefix/no-look-ahead behavior, next-open fills, conservative same-candle stop/target ambiguity resolution, and fail-closed schema checks all passed.

### 5. GATE_A_VALIDATION — PASS

```text
request_id = REQ-E7-GATEA-024-05-A71C2E94
task_id = E7-20260824-024
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

Delivered stderr confirms OOS dataset/binding mismatch rejection, binary-float fail-closed behavior, canonical PASS under explicit OOS bindings/thresholds, no Registry/lifecycle authority, E6 contract acceptance, NOT_RUN non-promotion, deterministic decision identity, impossible consecutive-loss blocking, stable quantitative fail ordering, training/OOS separation, and schema/type fail-closed behavior all passed.

### 6. GATE_A_REGISTRY — PASS

```text
request_id = REQ-E7-GATEA-024-06-C4E8B129
task_id = E7-20260824-024
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

Delivered stderr confirms fail-closed BacktestResult and ValidationDecision evidence validation, Decimal/RFC3339 interchange enforcement, lifecycle authority capped at CANDIDATE, DRAFT→BACKTESTING requiring durable local E2 PASS metadata, content-hash/idempotency handling, secret-like field rejection, CANDIDATE requiring both canonical backtest and validation evidence, and no approval/live path. All 19 reported tests passed.

## Evidence limitations

The delivered result excerpts for suites 1-6 do not separately expose Python executable/version, OS identity, cwd, explicit detached-HEAD/clean-worktree fields, SQLite row identifiers, or execution-count fields. E7 does not fabricate missing values. The TASK-approved execution pin/preparation evidence remains the governing environment requirement, and no source/worktree mismatch or execution refusal was reported by these successful Local Runner results.

For each suite, AgentBridge delivered the durable execution-result notification to the E7 conversation.

### Remaining suites

```text
7. GATE_A_STORAGE     = PENDING REQUEST
8. GATE_A_INTEGRATION = NOT_RUN
```

## Current interpretation

```text
LOCAL_EXECUTION_MATRIX = IN_PROGRESS
GATE_A_REVIEW_CANDIDATE = NO
Gate A = BLOCKED / MATRIX IN PROGRESS
```

No Gate A PASS is claimed. Six of eight required suites have fresh successful evidence. The matrix remains event-driven and must stop on the first failed/error/timed-out/unexpected-refused suite.
