"""Durable provider coordination; this object owns no credential or HTTP driver."""
from brokers.okx_product_state import durable_product_intent
from storage.product_dispatch import ProductDispatchJournal, ProductProcessLease, ProductDispatchError
from storage.runtime import PaperRuntimeJournal


class TradingCoordinator:
    def __init__(self, dispatch, canonical, run_id, lease, *, clock):
        if (type(dispatch) is not ProductDispatchJournal or type(canonical) is not PaperRuntimeJournal or
            type(lease) is not ProductProcessLease or lease.run_id != run_id or not callable(clock)):
            raise ProductDispatchError('ACTUAL_CANONICAL_TRADING_COORDINATION_REQUIRED')
        self.dispatch=dispatch; self.canonical=canonical; self.run_id=run_id; self.lease=lease; self.clock=clock

    def prepare_and_claim(self, prepared):
        operation_id=prepared.canonical_request.order_request_id
        self.dispatch.prepare(self.run_id, operation_id, durable_product_intent(prepared), lease=self.lease, now=self.clock())
        # A committed first claim is data, not permission to send. The actual
        # service independently rechecks E6/E7/E5/E4 after this returns.
        return self.dispatch.claim_dispatch(self.run_id, operation_id, lease=self.lease, now=self.clock())

    def recover_publications(self):
        # The E6 read is paginated. Drain every retained page before a new effect;
        # reaching the finite bound preserves the backlog and blocks dispatch.
        for _ in range(100):
            self.dispatch.require_process(self.lease, now=self.clock())
            batches=self.dispatch.pending_publications(self.run_id)
            positions=self.dispatch.pending_position_publications(self.run_id)
            if not batches and not positions: return
            for batch in batches:
                self.dispatch.require_process(self.lease, now=self.clock())
                self.canonical.publish_canonical_effects(batch.effects)
                self.dispatch.mark_publication(batch, lease=self.lease, now=self.clock())
            for batch in positions:
                self.dispatch.require_process(self.lease, now=self.clock())
                self.canonical.publish_canonical_effects(batch.effects)
                self.dispatch.mark_position_publication(batch, lease=self.lease, now=self.clock())
        raise ProductDispatchError('TRADING_CANONICAL_PUBLICATION_BACKLOG')

    def observe(self, operation_id, observation, effects):
        self.dispatch.observe(self.run_id, operation_id, observation, lease=self.lease,
                              now=self.clock(), canonical_effects=effects)
        self.recover_publications()
