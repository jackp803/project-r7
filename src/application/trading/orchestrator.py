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
            entries=self.dispatch.pending_entry_publications(self.run_id)
            exits=self.dispatch.pending_exit_publications(self.run_id)
            batches=self.dispatch.pending_publications(self.run_id)
            positions=self.dispatch.pending_position_publications(self.run_id)
            funding=self.dispatch.pending_funding_publications(self.run_id)
            finalizations=self.dispatch.pending_finalizations(self.run_id)
            if not entries and not exits and not batches and not positions and not funding and not finalizations: return
            for batch in entries:
                self.dispatch.require_process(self.lease,now=self.clock())
                # Canonical owners commit idempotently before the separate E6
                # receipt. Neither SQLite writer encloses the other writer.
                self.canonical.publish_canonical_effects(batch.effects)
                self.dispatch.mark_entry_publication(batch,lease=self.lease,now=self.clock())
            for batch in exits:
                self.dispatch.require_process(self.lease,now=self.clock())
                self.canonical.publish_canonical_effects(batch.effects)
                self.dispatch.mark_exit_publication(batch,lease=self.lease,now=self.clock())
            for batch in batches:
                self.dispatch.require_process(self.lease, now=self.clock())
                self.canonical.publish_canonical_effects(batch.effects)
                self.dispatch.mark_publication(batch, lease=self.lease, now=self.clock())
            for batch in positions:
                self.dispatch.require_process(self.lease, now=self.clock())
                self.canonical.publish_canonical_effects(batch.effects)
                self.dispatch.mark_position_publication(batch, lease=self.lease, now=self.clock())
            for batch in funding:
                self.dispatch.require_process(self.lease,now=self.clock())
                self.canonical.publish_canonical_effects(batch.effects)
                self.dispatch.mark_funding_publication(batch,lease=self.lease,now=self.clock())
            for batch in finalizations:
                self.dispatch.publish_finalization(self.canonical,batch,lease=self.lease,clock=self.clock)
        raise ProductDispatchError('TRADING_CANONICAL_PUBLICATION_BACKLOG')

    def observe(self, operation_id, observation, effects):
        self.dispatch.observe(self.run_id, operation_id, observation, lease=self.lease,
                              now=self.clock(), canonical_effects=effects)
        self.recover_publications()

class TradingOrchestrator:
    """Controlled original E2 entry and EXIT join; no production activation."""
    def __init__(self, service):
        # TradingService imports this module; defer service-related imports.
        from application.trading.entry_owner import EntryOwner
        self._entry_owner=EntryOwner(service)
        self._exit_owner=None

    def evaluate_original_exit(self,entry_boundary,*,native_position,metadata,read_proof,close_proof,
                               market_snapshot,market_freshness_classification,action_expires_at,expected_revision):
        if self._exit_owner is None:
            from application.trading.exit_owner import OriginalExitOwner
            self._exit_owner=OriginalExitOwner(self._entry_owner.service)
        return self._exit_owner.evaluate(entry_boundary,native_position=native_position,metadata=metadata,
            read_proof=read_proof,close_proof=close_proof,market_snapshot=market_snapshot,
            market_freshness_classification=market_freshness_classification,
            action_expires_at=action_expires_at,expected_revision=expected_revision)

    def evaluate_entry(self,bundle,*,selected_risk,risk_context,risk_proposal,metadata,
                       prerequisites,capability_proof,prerequisites_proof,expected_revision):
        return self._entry_owner.evaluate_entry(bundle,selected_risk=selected_risk,
            risk_context=risk_context,risk_proposal=risk_proposal,metadata=metadata,
            prerequisites=prerequisites,capability_proof=capability_proof,
            prerequisites_proof=prerequisites_proof,expected_revision=expected_revision)
