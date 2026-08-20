import unittest

from position import (
    PositionEvent,
    PositionLifecycleState,
    UnsafeTransitionError,
    state_allows_safe_open_claim,
    state_blocks_new_exposure,
    transition,
)


class PositionStateMachineTests(unittest.TestCase):
    def test_fill_is_unprotected_until_protection_is_verified(self):
        state = transition(PositionLifecycleState.PENDING_ENTRY, PositionEvent.ENTRY_FILL_OBSERVED)
        self.assertEqual(PositionLifecycleState.OPEN_UNPROTECTED, state)
        self.assertFalse(state_allows_safe_open_claim(state))
        state = transition(state, PositionEvent.PROTECTION_VERIFIED)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, state)
        self.assertTrue(state_allows_safe_open_claim(state))

    def test_protection_failure_enters_emergency(self):
        state = transition(PositionLifecycleState.OPEN_UNPROTECTED, PositionEvent.PROTECTION_FAILED)
        self.assertEqual(PositionLifecycleState.EMERGENCY, state)
        self.assertTrue(state_blocks_new_exposure(state))

    def test_unknown_state_requires_reconciliation(self):
        state = transition(PositionLifecycleState.OPEN_PROTECTED, PositionEvent.STATE_UNKNOWN)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, state)
        self.assertFalse(state_allows_safe_open_claim(state))
        self.assertTrue(state_blocks_new_exposure(state))

    def test_pending_entry_cannot_skip_unprotected_state(self):
        with self.assertRaises(UnsafeTransitionError):
            transition(PositionLifecycleState.PENDING_ENTRY, PositionEvent.PROTECTION_VERIFIED)

    def test_reconciliation_may_restore_protected_only_by_explicit_event(self):
        state = transition(
            PositionLifecycleState.RECONCILIATION_REQUIRED,
            PositionEvent.RECONCILED_OPEN_PROTECTED,
        )
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, state)

    def test_unknown_enum_fails_closed(self):
        self.assertTrue(state_blocks_new_exposure("SOMETHING_NEW"))
        self.assertFalse(state_allows_safe_open_claim("SOMETHING_NEW"))


if __name__ == "__main__":
    unittest.main()
