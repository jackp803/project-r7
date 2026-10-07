"""Transfer first, verify the transferred leaf, never delete an unverified leaf."""

def remove_verified_leaf(operation, expected):
    operation.expect_original(expected)
    operation.move_to_quarantine()
    try:
        if operation.quarantined_facts() != expected:
            raise ValueError('Transferred removal subject changed')
    except (OSError, ValueError):
        try:
            operation.restore_noreplace()
        except (OSError, ValueError):
            raise ValueError('Unverified leaf preserved in private quarantine; inspect disposition') from None
        raise ValueError('Unverified leaf restored without overwriting a public replacement') from None
    operation.unlink_verified()
    if operation.original_exists():
        raise ValueError('Verified leaf removed; new public replacement preserved')
