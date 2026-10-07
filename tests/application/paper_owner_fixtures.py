"""One-store actual owners; immutable accelerated FIXTURE release only."""
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal

from application.control_api.paper_ports import PaperReadControlPort, PaperStartControlPort
from application.paper.service import PaperService, PaperMarketEvent
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from registry import StrategyIdentity
from registry.operational_authority import ReleaseBinding, ProductLifecycleComposition, HumanAuthenticator
from storage.platform import open_sqlite_platform
from storage.paper_process import open_paper_process_journal
from storage.runtime import open_paper_runtime_journal
from strategy.v02.capabilities import _revision, build_capability_snapshot
from tests.product import test_api_owner_services as api_fixtures
from tests.product.test_paper_runtime_v02 import simulation_fixture
from tests.application.test_product_assessment_binding import risk_fixture
from tests.validation.robustness_fixtures import subject
from tests.validation.test_paper_promotion_policy import policy_fixture


class PaperOwnerFixture:
    def __init__(self, case):
        h = api_fixtures.APIOwnerServicesTests()
        case.addCleanup(lambda: case.assertTrue(h.doCleanups(), 'Actual owner fixture cleanup failed'))
        h.setUp()
        response = h.enqueue()
        job_id = response.json()['effect_ref'].removeprefix('research-job:')
        claim = h.queue.claim_next()
        case.assertEqual(claim.run_id, job_id)
        outcome = h.queue.step(claim.run_id, claim.generation)
        case.assertEqual(outcome['state'], 'COMPLETE')
        case.assertEqual(outcome['outcome']['strategy_lifecycle'], 'CANDIDATE')
        self.h, self.config = h, h.config
        self.identity = StrategyIdentity(subject()['strategy_id'], subject()['strategy_version'])
        self.initial_now = h.clock[0]
        with h.registry_factory() as registry:
            product = registry.candidate_product_assessment(self.identity)
        self.release = ReleaseBinding(namespace='FIXTURE', implementation_hash=_revision(),
            executable_revision=h.queue.evidence_view(job_id)['provenance']['executable_revision'],
            build_hash='sha256:'+'1'*64, config_hash='sha256:'+'2'*64, config_generation=1,
            capability_hash=build_capability_snapshot().snapshot_hash, provider_profile_hash='sha256:'+'3'*64,
            provider_ref='fixture-paper', account_ref='fixture-account', risk_policy_hash=product.risk_policy_hash,
            risk_generation=1, runtime_generation=1, release_kind='FIXTURE')
        self.factory_calls = []
        self.closed_factories = 0
        self.simulation = simulation_fixture()
        self.reader = PaperReadControlPort(namespace='FIXTURE',
            process_factory=lambda: open_paper_process_journal(h.config.database_path),
            canonical_factory=lambda: open_paper_runtime_journal(h.config.database_path), clock=lambda: h.clock[0])
        self.starter = PaperStartControlPort(namespace='FIXTURE', service_factory=self.factory)

    @contextmanager
    def factory(self):
        import threading
        self.factory_calls.append(threading.get_ident())
        h = self.h
        boundary = ProductLifecycleComposition(namespace='FIXTURE', current_release=lambda: self.release,
            resolve_evidence=lambda *args: None,
            authenticator=HumanAuthenticator(namespace='FIXTURE', reauth_seconds=300,
                verifier=lambda proof: None, clock=lambda: h.clock[0]), clock=lambda: h.clock[0])
        promotion = policy_fixture()
        boundary.select_paper_policy('owner-fixture-policy', promotion)
        try:
            with open_sqlite_platform(h.config.database_path, research_namespace='FIXTURE', lifecycle_boundary=boundary) as registry, \
                    open_paper_process_journal(h.config.database_path) as process, \
                    open_paper_runtime_journal(h.config.database_path) as canonical:
                service = PaperService(registry=registry, process_journal=process, canonical_journal=canonical,
                    namespace='FIXTURE', simulation_policy=self.simulation, risk_policy=risk_fixture(),
                    promotion_policy=promotion, paper_policy_ref='owner-fixture-policy', actor='fixture-paper-owner',
                    workflow_authorized=True,
                    submission_validity={'intent_class': 'EVERGREEN_STRATEGY', 'validity': {'from': None, 'until': None}},
                    current_release=lambda: self.release, clock=lambda: h.clock[0])
                boundary._resolve = service.resolve_owner_evidence
                yield service
        finally:
            self.closed_factories += 1

    def second_candidate(self):
        from strategy import compute_content_hash
        from application.research.service import ResearchService
        from tests.application import dataset_fixtures
        from tests.validation import robustness_fixtures
        from tests.application.test_research_robustness import selected
        from unittest.mock import patch
        definition = subject()
        definition['strategy_id'] = 'fixture-worker-second'
        definition['content_hash'] = compute_content_hash(definition)
        root = self.h.root/'second-inputs'
        # A second actual candidate needs a fresh, nonoverlapping sealed period.
        # Shift public fixture generation inputs; never reset the holdout ledger.
        shifted = dataset_fixtures.START+timedelta(days=7)
        with patch.object(dataset_fixtures, 'START', shifted), patch.object(robustness_fixtures, 'START', shifted):
            selected(root)
        (root/'risk.json').write_bytes(dataset_fixtures.encoded(risk_fixture()))
        with ResearchService(local_root=root, database_path=self.h.root/'research.sqlite',
                registry_path=self.config.database_path, namespace='FIXTURE', owner_id='worker-second-fixture') as research:
            result = research.run(submission_id='worker-second', definition=definition,
                dataset_ref='dataset.json', split_policy_ref='split.json', cost_policy_ref='cost.json',
                research_policy_ref='research.json', robustness_policy_ref='robustness.json',
                family_id='worker-second-family', seed=42, risk_policy_ref='risk.json')
            if result.strategy_lifecycle != 'CANDIDATE':
                raise AssertionError('Actual second fixture candidate did not qualify: '+repr(result))
        return StrategyIdentity(definition['strategy_id'], definition['strategy_version'])

    def start(self, command_id='owner-start', identity=None):
        identity = self.identity if identity is None else identity
        with self.h.registry_factory() as registry:
            revision = registry.get_strategy(identity).registry_revision
        receipt = self.starter.start(dict(strategy_id=identity.strategy_id,
            strategy_version=identity.strategy_version, policy_id='owner-fixture-policy'),
            actor='fixture-owner', command_id=command_id, expected_revision=revision)
        return receipt['effect_ref'].removeprefix('paper:')

    def recover(self, run_id):
        with open_paper_process_journal(self.config.database_path) as process:
            return process.recover(run_id)

    def restore_inhibited(self, case):
        from datetime import datetime, timezone
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from application.platform.backup import create_database_backup
        from application.platform.database_restore import restore_database_backup
        from application.config import load_config
        temp = TemporaryDirectory(prefix='R7 fixture worker restore ')
        case.addCleanup(temp.cleanup)
        root = Path(temp.name)
        create_database_backup(self.config, root/'backup', timeout_seconds=10)
        restore_database_backup(self.config, root/'backup', root/'restored')
        self.config = self.h.config = load_config(root/'restored'/'restored-product.json')
        self.initial_now = self.h.clock[0] = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)+timedelta(hours=1)

    def event(self, seconds, price='60000', bars=False):
        now = self.initial_now + timedelta(seconds=seconds)
        self.h.clock[0] = now
        snapshot = MarketSnapshot('contracts-v0.1', 'BTC_USDT_PERP', now, now,
            'HEALTHY', 'EXPLICIT_FIXTURE', last_price=Decimal(price), freshness_ms=0)
        candles = tuple(Candle('contracts-v0.1', 'BTC_USDT_PERP', '1h',
            self.initial_now-timedelta(hours=2-index), self.initial_now-timedelta(hours=1-index),
            Decimal(value), Decimal(value)+1, Decimal(value)-1, Decimal(value), Decimal('1'),
            True, 'EXPLICIT_FIXTURE', received_at=self.initial_now)
            for index, value in enumerate(('59000', '60000'))) if bars else ()
        return PaperMarketEvent(snapshot, candles, 'FIXTURE')
