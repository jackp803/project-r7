"""Non-TestCase H01 recovery/schema helpers.
Controlled FIXTURE source regression; separate from native acceptance.
No protection setup; one normal H01 fixture per exposed test module.
"""
from contextlib import ExitStack
from dataclasses import replace
from datetime import timedelta
import json

from tests.product import h01_entry_fixture as entry_fixtures
from tests.integration import test_runtime_preflight as preflight_fixtures
from application.trading.admission import RuntimeAdmission
from application.trading.service import TradingService
from application.trading.provider import FakeProductProvider
from brokers.okx_product_capability import OKXProductCapabilityOwner
from brokers.okx_product import OKXProductTranslator
from registry.operational_authority import stamp
from storage.product_dispatch import open_product_dispatch_journal
from storage.runtime import open_paper_runtime_journal


class H01RecoveryFixture:
    def __enter__(self):
        self.stack = ExitStack()
        try:
            self.fixture = self.stack.enter_context(entry_fixtures.H01EntryFixture())
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def install_initial_script(self, responses):
        """Fresh trusted fake composition BEFORE any decision/claim/effect."""
        f = self.fixture
        if f.provider.calls or f.dispatch.entry_decision(f.service.run_id, f.authority.identity, f.bundle.boundary):
            raise AssertionError('Initial script must be selected before actual owner work')
        provider = FakeProductProvider(responses)
        service = TradingService(admission=f.admission,
            translator=OKXProductTranslator(f.capabilities), dispatch=f.dispatch,
            canonical=f.canonical, provider=provider, identity=f.authority.identity,
            run_id=f.service.run_id, clock=lambda:f.authority.clock[0])
        service.bind_process(expected_revision=f.authority.revision,
                            expected_generation=f.service.lease.generation)
        # Existing same original process instance idempotently retains lease1.
        if service.lease != f.service.lease:
            raise AssertionError('Initial fake composition must not create another process generation')
        return service, provider

    def successor(self):
        """New objects/connections and actual E7 interpreter; E7 release stays1."""
        f = self.fixture
        release_before = f.authority.release[0]
        f.authority.clock[0] += timedelta(seconds=1)
        started = f.authority.clock[0]
        instance = 'process-fixture-h01-entry-successor'

        def current_preflight():
            base = preflight_fixtures.RuntimePreflightV01Tests(); base.setUp()
            release = f.authority.release[0]
            base.revision = release.executable_revision
            base.config_hash = release.config_hash
            base.capability_hash = release.capability_hash
            base.authorization_capability_hash = release.capability_hash
            value = base._input(role='PAPER_RUNTIME')
            now = f.authority.clock[0]
            runtime_generation = 'runtime-generation:' + str(release.runtime_generation)
            config_generation = 'config-generation:' + str(release.config_generation)
            value = replace(value,
                runtime_preflight_profile_version='product-runtime-preflight-v0.2',
                runtime_role='LIVE_RUNTIME', requested_operational_mode='LIVE',
                evaluated_at=stamp(now), process_instance_id=instance,
                process_start_generation_id=runtime_generation, process_started_at=stamp(started),
                runtime_config_generation_id=config_generation,
                heartbeat_evidence=dict(value.heartbeat_evidence,
                    heartbeat_process_instance_id=instance,
                    heartbeat_process_start_generation_id=runtime_generation,
                    heartbeat_observed_at=stamp(now), heartbeat_received_at=stamp(now)),
                reconciliation_evidence=dict(value.reconciliation_evidence,
                    reconciliation_observed_at=stamp(now)),
                external_consumer_evidence=dict(value.external_consumer_evidence,
                    compatibility_observed_at=stamp(now)),
                authorization_evidence=dict(value.authorization_evidence,
                    authorization_class='PERSISTENT_LIVE_RUNTIME', authorized_runtime_role='LIVE_RUNTIME'))
            authority = base._authority(value)
            return value, replace(authority,
                runtime_config_authority=dict(authority.runtime_config_authority,
                    runtime_config_generation_id=config_generation))

        admission = RuntimeAdmission(namespace='FIXTURE', registry_factory=f.authority.factory,
            current_preflight=current_preflight, clock=lambda:f.authority.clock[0],
            maximum_observation_age_seconds=5)
        capabilities = OKXProductCapabilityOwner()
        translator = OKXProductTranslator(capabilities)
        # New handles to SAME durable files, not empty replacement files.
        dispatch = open_product_dispatch_journal(f.authority.root/'h01-dispatch.sqlite')
        self.stack.callback(dispatch.close)
        canonical = open_paper_runtime_journal(f.authority.root/'h01-canonical.sqlite')
        self.stack.callback(canonical.close)
        provider = FakeProductProvider([])
        service = TradingService(admission=admission, translator=translator,
            dispatch=dispatch, canonical=canonical, provider=provider,
            identity=f.authority.identity, run_id=f.service.run_id,
            clock=lambda:f.authority.clock[0])
        lease = service.bind_process(expected_revision=f.authority.revision, expected_generation=1)
        if lease.generation != 2 or lease.instance_id != instance:
            raise AssertionError('Actual new dispatch process generation2 required')
        if f.authority.release[0] != release_before or release_before.runtime_generation != 1:
            raise AssertionError('Dispatch successor must not rewrite original E7 release/runtime generation1')
        if any(left is right for left, right in ((admission,f.admission),
                (capabilities,f.capabilities),(translator,f.service.translator),
                (provider,f.provider),(dispatch,f.dispatch),(canonical,f.canonical))):
            raise AssertionError('Successor must reconstruct every transient owner and journal handle')
        return service


def canonical_object(journal, kind, canonical_id):
    """Read test-owned canonical owner row; never writes financial tables.
    recover(plan_id) cannot find a risk row before its parent plan is durable.
    """
    if kind not in ('RISK_DECISION', 'APPROVED_TRADE_PLAN'):
        raise AssertionError('Narrow canonical test reader only')
    row = journal._store._object_row(kind, canonical_id)
    return None if row is None else (row['payload_json'], row['payload_hash'])


def entry_storage_snapshot(dispatch):
    return {table: tuple(tuple(row) for row in dispatch._db.execute(
        'SELECT * FROM '+table+' ORDER BY run_id,boundary').fetchall())
        for table in ('product_entry_decisions','product_entry_publications')}
