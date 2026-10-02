# R7 Product Acceptance Matrix — V0.1

Status: PM ACCEPTANCE AUTHORITY
Date: 2026-10-02

This matrix is the product-level Definition of Done for the Codex master
productization program.

A source file existing is not acceptance.
A test definition existing is not acceptance.
A static review is not executable PASS.
A favorable strategy metric is not lifecycle authority.

## A. Product startup

| ID | Requirement | PASS evidence |
|---|---|---|
| A01 | Windows product starts from packaged launcher | local packaged smoke PASS |
| A02 | no manual PYTHONPATH needed | clean launch evidence |
| A03 | local data root configurable | first-run test |
| A04 | cloud root configurable | first-run test |
| A05 | DB initialized/migrated automatically | fresh-profile test |
| A06 | restart preserves prior product state | restart test |
| A07 | clean shutdown leaves restart-safe state | shutdown/reopen test |
| A08 | product version and exact project revision visible | UI/API evidence |

## B. Cloud Strategy Inbox

| ID | Requirement | PASS evidence |
|---|---|---|
| B01 | synced-folder transport initializes root | local test |
| B02 | valid Strategy Package discovered | integration test |
| B03 | manifest written last is recognized | integration test |
| B04 | missing payload = INCOMPLETE_SYNC | deterministic test |
| B05 | transient hash mismatch = INCOMPLETE_SYNC | deterministic test |
| B06 | traversal/absolute path blocked | security test |
| B07 | secret-like fields blocked | security test |
| B08 | duplicate same package idempotent | restart test |
| B09 | same submission ID changed content conflicts | fail-closed test |
| B10 | local intake ledger prevents duplicate execution | restart test |
| B11 | valid package reaches real E6 DRAFT | cross-domain test |
| B12 | no fabricated LOCAL_EXECUTION PASS | negative test |
| B13 | sanitized receipt returned to Cloud Drive | round-trip test |

## C. Dataset / research

| ID | Requirement | PASS evidence |
|---|---|---|
| C01 | exact dataset ID/hash/range resolved | research test |
| C02 | train/tuning/final-OOS split locked | evidence identity test |
| C03 | final OOS cannot influence tuning | leakage regression |
| C04 | E2 compatibility executed, not fabricated | local evidence |
| C05 | actual E2 StrategyRuntime used | cross-role test |
| C06 | actual E3 replay used | cross-role test |
| C07 | fee/slippage/funding explicit | result binding |
| C08 | no-look-ahead enforced | regression |
| C09 | BacktestResult stored in E6 | integration test |
| C10 | OOS ValidationDecision stored in E6 | integration test |
| C11 | failures remain durable | persistence test |
| C12 | research resumes safely after restart | recovery test |

## D. Robustness

| ID | Requirement | PASS evidence |
|---|---|---|
| D01 | parameter-neighborhood generated deterministically | unit test |
| D02 | invalid variants retained as failures | unit/integration |
| D03 | walk-forward windows immutable/order-safe | test |
| D04 | walk-forward no future leakage | regression |
| D05 | Monte Carlo explicit seed | identity test |
| D06 | same seed same result | deterministic test |
| D07 | cost/slippage stress supported | test |
| D08 | robustness decision has versioned policy | schema/test |
| D09 | known robust fixture PASS | local execution |
| D10 | known fragile fixture FAIL | local execution |
| D11 | CANDIDATE cannot bypass robustness | lifecycle negative |

## E. Strategy lifecycle

| ID | Requirement | PASS evidence |
|---|---|---|
| E01 | DRAFT -> BACKTESTING guarded | lifecycle test |
| E02 | BACKTESTING -> REJECTED durable | lifecycle test |
| E03 | BACKTESTING -> CANDIDATE guarded | lifecycle test |
| E04 | CANDIDATE -> PAPER guarded | lifecycle test |
| E05 | PAPER -> READY_FOR_APPROVAL guarded | lifecycle test |
| E06 | READY_FOR_APPROVAL -> APPROVED requires ApprovalRecord | negative+positive |
| E07 | APPROVED -> LIVE requires runtime gates | negative simulation |
| E08 | LIVE -> DEGRADED fail-closed available | runtime test |
| E09 | DEGRADED -> LIVE never automatic | negative test |
| E10 | RETIRED terminal behavior preserved | lifecycle test |
| E11 | no arbitrary generic transition API | interface audit |
| E12 | exact strategy version binding every edge | regression |

## F. Continuous PAPER

| ID | Requirement | PASS evidence |
|---|---|---|
| F01 | scheduler evaluates only closed boundary | test |
| F02 | duplicate boundary does not duplicate trade | restart/idempotence |
| F03 | Signal flows through E5 | integration |
| F04 | Risk REJECT blocks execution | negative test |
| F05 | approved plan flows to PaperBroker | integration |
| F06 | ACK/fill distinction preserved | test |
| F07 | partial fill handled | test |
| F08 | protection verified before safe-open | lifecycle test |
| F09 | protection failure enters safe degraded/emergency state | test |
| F10 | normal exit -> flat + TradeResult | E2E |
| F11 | funding/cost persisted | E2E |
| F12 | restart flat safe | E2E |
| F13 | restart open protected safe | E2E |
| F14 | restart open unprotected blocks new exposure | E2E |
| F15 | ambiguous state requires reconciliation | E2E |
| F16 | PAPER policy PASS/FAIL deterministic | policy test |
| F17 | READY_FOR_APPROVAL only after PAPER evidence | lifecycle test |
| F18 | PAPER report published | cloud round-trip |

## G. Approval / deployment

| ID | Requirement | PASS evidence |
|---|---|---|
| G01 | Product Owner can approve exact strategy version | UI/API test |
| G02 | approval is immutable | persistence test |
| G03 | approval binds project/risk/deployment envelope | contract test |
| G04 | approval never contains credentials | security test |
| G05 | wrong-version approval rejected | negative test |
| G06 | stale/revoked/expired authority blocked | negative test |
| G07 | one approval does not transfer versions | negative test |

## H. LIVE-capable code, credential-free

| ID | Requirement | PASS evidence |
|---|---|---|
| H01 | TradingOrchestrator exists and uses E2/E5/E4 | static+integration |
| H02 | Signal cannot execute directly | negative test |
| H03 | credentials are not authority | negative test |
| H04 | runtime preflight required | negative test |
| H05 | provider reconciliation required | negative test |
| H06 | ACK is not Fill | simulation |
| H07 | ambiguous submit no blind retry | simulation |
| H08 | partial fill uses actual exposure | simulation |
| H09 | missing protection fail closed | simulation |
| H10 | duplicate protection fail closed | simulation |
| H11 | orphan protection fail closed | simulation |
| H12 | close requires authoritative flat truth | simulation |
| H13 | residual below actionable size stable | simulation |
| H14 | kill switch blocks new exposure | simulation |
| H15 | wrong revision/mode/heartbeat blocks runtime | simulation |
| H16 | successful full fake-provider lifecycle | E2E simulation |
| H17 | real provider/private request count remains zero | evidence |
| H18 | real capital exposure remains NONE | evidence |

## I. Control API

| ID | Requirement | PASS evidence |
|---|---|---|
| I01 | local API starts | local test |
| I02 | overview endpoint truthful | API test |
| I03 | research endpoint truthful | API test |
| I04 | strategy lifecycle endpoint truthful | API test |
| I05 | paper endpoint truthful | API test |
| I06 | health endpoint no false green | API test |
| I07 | settings cannot persist secrets | security test |
| I08 | invalid action cannot bypass backend gate | negative test |
| I09 | approval endpoint creates canonical evidence | API test |
| I10 | LIVE action blocked without authority | negative test |

## J. Control Center

| ID | Requirement | PASS evidence |
|---|---|---|
| J01 | Overview renders | browser/manual local smoke |
| J02 | Research progress renders | smoke |
| J03 | Strategies/version history renders | smoke |
| J04 | Trading state renders | smoke |
| J05 | Health plain-language state renders | smoke |
| J06 | alerts visible | smoke |
| J07 | settings usable for local/cloud roots | smoke |
| J08 | no secret value displayed | security smoke |
| J09 | backend rejection shown clearly | smoke |
| J10 | UI does not directly edit DB | architecture audit |

## K. Cloud results / Chat feedback

| ID | Requirement | PASS evidence |
|---|---|---|
| K01 | research manifest published | round-trip |
| K02 | rejected strategy retained | round-trip |
| K03 | candidate evidence index published | round-trip |
| K04 | PAPER report published | round-trip |
| K05 | LIVE sanitized summary schema implemented | test |
| K06 | Chat-facing summary JSON implemented | test |
| K07 | Parquet large tables supported where selected | read/write test |
| K08 | output atomic/idempotent | restart test |
| K09 | no credential/private payload leakage | security scan |

## L. Security

| ID | Requirement | PASS evidence |
|---|---|---|
| L01 | no real secret in Git | repository scan |
| L02 | no secret in cloud fixture/report | artifact scan |
| L03 | strategy cannot execute arbitrary Python/shell | parser/security |
| L04 | cloud path traversal blocked | test |
| L05 | no GitHub workflow compute added | tree audit |
| L06 | no paid LLM API runtime dependency | import/network audit |
| L07 | local runtime DB outside cloud root | config test |
| L08 | logs redact sensitive material | log test |
| L09 | Control API localhost default | config/API test |
| L10 | LIVE cannot start from credentials alone | negative E2E |

## M. Product E2E

| ID | Requirement | PASS evidence |
|---|---|---|
| M01 | valid package -> research -> CANDIDATE | full E2E |
| M02 | weak package -> REJECTED | full E2E |
| M03 | malformed package -> BLOCKED | full E2E |
| M04 | partial sync -> later single successful processing | full E2E |
| M05 | CANDIDATE -> PAPER -> READY_FOR_APPROVAL | full E2E |
| M06 | full PAPER trade -> protected -> exit -> flat | full E2E |
| M07 | product restart preserves correctness | full E2E |
| M08 | cloud results round-trip visible in UI | full E2E |
| M09 | packaged Windows launch works | local product smoke |
| M10 | credential-free LIVE path remains blocked | full E2E |
| M11 | all critical tests have zero skips | final evidence |
| M12 | complete credential-free suite PASS | final evidence |

## N. Final classification

```text
PRODUCT_IMPLEMENTATION_COMPLETE
```

requires all implementation-required items above PASS, with H17/H18 proving no
real provider/private/capital activity occurred.

```text
PRODUCT_REAL_MONEY_ACTIVATED
```

is a separate future state and is not granted by this acceptance matrix.
