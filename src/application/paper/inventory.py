"""Committed PQR command/test inventory for three separately qualified targets.

The generated data is source code packaged by the native build. Updating it is
a development operation followed by a new clean commit, never an API selection.
"""
import json
from pathlib import Path
import platform
import sys

from registry.product_assessment import canonical
from strategy.v02.capabilities import build_capability_snapshot

TARGETS=('windows-11-x86_64','ubuntu-24.04-x86_64','ubuntu-26.04-x86_64')
NATIVE_ASSERTIONS={
    'PQR-02':('EXACT_NATIVE_IDENTITY_RESOURCES_LICENSES_UI','TAMPER_DENIED_EXTERNAL_DATA'),
    'PQR-03':('PUBLIC_FRESH_AUTH_INTAKE_RESEARCH_THREE_OUTCOMES','NEGATIVE_UI_AND_AUTHENTICATED_API_NO_RUN',
              'INDEPENDENT_NATIVE_PAPER_ACK_FILL_PROTECT_PAUSE_RESTART_EXIT_FLAT','TRUTHFUL_RENDERED_UI_DIRECTION'),
    'PQR-04':('NATIVE_MALFORMED_UNSUPPORTED_CONFLICT_PARTIAL_RETRY','NATIVE_COMPLETED_SAME_ID_IDEMPOTENCY',
              'EXPIRY_DISCOVERY_ENQUEUE_RESEARCH_CHECKPOINT_PREENTRY','EXPIRED_OPEN_POSITION_PROTECTION_PRESERVED'),
    'PQR-05':('NATIVE_EXCLUSIVITY_STALE_FENCING','ACTUAL_GRACEFUL_CONTROL_AND_WORKER_STOP',
              'CRASH_FLAT_PROTECTED_UNPROTECTED_RECONCILIATION','PARTIAL_DUPLICATE_STALE_MISSING_MARKET_PROTECTION',
              'PRIVATE_CONSISTENT_BACKUP_RESTORED_INHIBITION','RESEARCH_FAULT_PROTECTION_ISOLATION',
              'ACTUAL_HOST_BOUNDED_CAPACITY_RESOURCE_MEASUREMENT','TARGET_SERVICE_APPLICABILITY'),
    'PQR-06':('NATIVE_AUTH_HOST_ORIGIN_CSRF_STALE_IDEMPOTENT_GUARDS','NO_CALLER_PASS_CODE_GENERATION_FINANCIAL_AUTHORITY',
              'RECEIPT_SUBJECT_ARTIFACT_CURRENT_RUNTIME_NEGATIVE_GATES','IMMUTABLE_RECEIPT_REPLAY_CONFLICT_NAMESPACE'),
    'PQR-07':('ACTUAL_OWNER_REPORTS_DURABLE_OUTBOX','SIMULATED_REAL_ELAPSED_DISCLOSURE_REDACTION',
              'STAGED_REMOTE_ACK_SEPARATION_FAILED_PUBLICATION_RETRY_IDEMPOTENCY'),
}


def current_target():
    if platform.machine().lower() not in ('amd64','x86_64'):
        raise ValueError('Named native x86-64 target required')
    if platform.system()=='Windows' and sys.getwindowsversion().build>=22000:
        return TARGETS[0]
    if platform.system()=='Linux':
        rows=dict(line.split('=',1) for line in Path('/etc/os-release').read_text(encoding='utf-8').splitlines() if '=' in line)
        version=rows.get('VERSION_ID','').strip('"')
        if rows.get('ID','').strip('"')=='ubuntu' and version in ('24.04','26.04'):
            return f'ubuntu-{version}-x86_64'
    raise ValueError('Actual Windows11 or Ubuntu24.04/26.04 native host required')


def fixed_profile(target):
    if target not in TARGETS:raise ValueError('Named supported native target required')
    from ._fixed_inventory import FROZEN
    value=json.loads(canonical(FROZEN))
    value.update(platform_id=target,capability_hash=build_capability_snapshot().snapshot_hash,
        os_applicability=dict(systemd='OS_INAPPLICABLE_WINDOWS' if target==TARGETS[0]
                             else 'REQUIRED_ACTUAL_UNPRIVILEGED_SERVICE'))
    return value
