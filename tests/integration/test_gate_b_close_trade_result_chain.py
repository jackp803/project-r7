"""Superseded E7 Gate B close-to-TradeResult integration definitions.

Historical revisions of this file intentionally captured two blockers that were
true before PR #52-#54:

- no governed real Paper funding producer/consumer chain;
- no real PROTECTION_STOP same-position flat observation.

Those assumptions are no longer current. The authoritative in-memory Gate B
integration definitions are now:

- tests/integration/test_gate_b_paper_trade_result_integration.py
- tests/safety/test_gate_b_paper_trade_result_safety.py

Git history retains the older blocker definitions for audit. Keeping executable
tests here would encode stale expected behavior and could create false failures
when the approved-local Gate B suite is eventually run.
"""

SUPERSEDED_BY = (
    "tests/integration/test_gate_b_paper_trade_result_integration.py",
    "tests/safety/test_gate_b_paper_trade_result_safety.py",
)
