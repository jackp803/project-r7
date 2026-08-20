# System Safety / Policy Test Structure

> Owner: E7 for cross-module safety; E5 owns domain risk-safety tests inside its scope.  
> Execution policy: **LOCAL-ONLY** or another Product-Owner-approved non-GitHub environment.

This directory defines system-level safety tests that cross agent boundaries. Test source may be committed to Git; execution must not occur on GitHub infrastructure.

## Safety invariants

The system must structurally prove, as implementation becomes available:

1. Strategy cannot call Broker/Pionex directly.
2. UI cannot submit exchange orders directly.
3. E4 cannot execute raw Signal/TradeIntent.
4. only E5-approved `ApprovedTradePlan` or authorized `PositionAction` can become executable broker requests.
5. E4 cannot increase quantity/leverage or loosen E5 risk bounds.
6. unknown/stale market, account, order, position, risk, or approval state blocks new exposure.
7. ambiguous order acknowledgement triggers reconciliation before retry.
8. partial fills use actual filled quantity for exposure/protection.
9. an unprotected filled position triggers the defined emergency path.
10. kill switches and risk locks cannot be bypassed by strategy/UI state.
11. Backtest PASS cannot directly become LIVE.
12. API credentials do not imply LIVE authorization.
13. Product Owner approval is required for first LIVE activation under current policy.
14. failed/rejected strategy evidence remains auditable.
15. strategy versions with attached evidence are immutable.
16. `UNKNOWN` health cannot appear as healthy/green.
17. backtest/paper/live-compatible callers use common E2 strategy semantics.
18. no real secrets are committed or emitted in normal logs/test fixtures.
19. GitHub Actions/CI/runners are not used for project verification.

## Planned test groups

```text
tests/safety/
  architecture/
    test_no_strategy_to_broker_bypass.*
    test_no_ui_to_exchange_bypass.*
    test_execution_requires_approved_plan.*
  risk/
    test_unknown_state_blocks_exposure.*
    test_kill_switch_cannot_be_bypassed.*
    test_no_risk_escalation_after_loss.*
    test_no_stop_widening_normal_path.*
  execution/
    test_timeout_requires_reconciliation.*
    test_partial_fill_protection_quantity.*
    test_unprotected_position_emergency.*
  lifecycle/
    test_backtest_cannot_jump_to_live.*
    test_rejected_strategy_retained.*
    test_strategy_version_immutable.*
    test_live_requires_approval.*
  security/
    test_secret_redaction.*
    test_credentials_do_not_enable_live.*
  policy/
    test_no_github_workflow_dependency.*
```

Framework/extensions remain unspecified until the implementation stack is committed.

## GitHub compute policy check definition

When a local checkout is available, E7 must verify that project execution is not configured under GitHub Actions. A suitable local inspection may include commands equivalent to:

```text
git ls-files .github/workflows
```

Expected result under current policy: no project workflow files that build, test, backtest, reproduce bugs, run E2E, run Monte Carlo, schedule project jobs, or execute project code.

A repository may contain no `.github/workflows/` directory at all, which is acceptable.

If any workflow appears, E7 must inspect it locally/read-only and mark integration `FAIL` if it violates the Product Owner policy. Do not run the workflow to determine whether it is acceptable.

## Secret hygiene check definition

When a local checkout is available, run a local secret-hygiene inspection appropriate to the repository stack. At minimum inspect tracked content for credential-shaped names/values and review any examples/configs/log fixtures.

Do not print real discovered secret values into GitHub issues, PRs, chat handoffs, screenshots, or committed reports. If a real credential is found in tracked/public history:

1. stop normal release work;
2. mark a security blocker;
3. notify the Product Owner;
4. require credential rotation;
5. require Git-history remediation as appropriate;
6. do not claim the incident is resolved merely because the current file was deleted.

## Local evidence format

```text
Safety criterion:
Status: PASS | FAIL | BLOCKED | NOT_RUN | NOT_APPLICABLE
Revision:
Environment:
Command:
Result summary:
Owner:
Timestamp UTC:
```

If there is no allowed local runtime, use `NOT_RUN`; never move the workload to GitHub CI.