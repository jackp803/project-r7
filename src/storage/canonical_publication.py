"""Fixed supported canonical writers; replay persists facts, never executes trades."""
from types import MappingProxyType
from storage.runtime_models import RuntimeValidationError


CANONICAL_WRITERS = MappingProxyType({
    'RISK_DECISION': 'persist_risk_decision', 'APPROVED_TRADE_PLAN': 'persist_approved_trade_plan',
    'POSITION_ACTION': 'persist_position_action', 'ORDER_REQUEST': 'persist_order_request',
    'ORDER_RESULT': 'persist_order_result', 'FILL': 'persist_fill',
    'RAW_POSITION': 'persist_raw_position_observation', 'POSITION_PROJECTION': 'persist_position_projection',
    'LIFECYCLE_EXECUTION_BINDING': 'persist_lifecycle_execution_binding',
    'FUNDING_EVIDENCE': 'persist_funding_evidence', 'TRADE_RESULT': 'persist_trade_result',
})


def publish_canonical_effects(journal, effects):
    if not isinstance(effects, list) or len(effects) > 5000:
        raise RuntimeValidationError('CANONICAL_PUBLICATION_INVALID', 'Bounded supported canonical effects required')
    for effect in effects:
        if (not isinstance(effect, dict) or set(effect) != {'kind', 'payload'} or
            not isinstance(effect['kind'], str) or effect['kind'] not in CANONICAL_WRITERS or
            not isinstance(effect['payload'], dict)):
            raise RuntimeValidationError('CANONICAL_PUBLICATION_INVALID', 'Supported canonical effect required')
        journal._check_payload_policy(effect['payload'])
    # Each owner writer commits its fact. Exact replay is idempotent, including
    # recovery from a failure between two facts; no network capability exists.
    return tuple(getattr(journal, CANONICAL_WRITERS[effect['kind']])(effect['payload']) for effect in effects)
