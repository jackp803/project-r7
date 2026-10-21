"""E4 public-rate source units; controlled raw pages, no provider calls."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN, localcontext
import json
import unittest

from brokers.paper import PaperBroker
import execution.funding as funding
from execution.models import OrderRequest, Side, stable_client_order_id, stable_order_request_id

BASE = datetime(2026, 8, 24, tzinfo=timezone.utc)


def at(hours=0, seconds=0):
    return BASE + timedelta(hours=hours, seconds=seconds)


def stamp(value):
    return value.isoformat().replace('+00:00', 'Z')


def millis(value):
    return str(int(value.timestamp() * 1000))


class PublicRecordedFundingTests(unittest.TestCase):
    def model(self):
        factory = getattr(funding, 'public_recorded_funding_model', None)
        self.assertTrue(callable(factory), 'Registered settled-public-rate Paper model is unavailable; zero funding cannot substitute')
        return factory()

    def page(self, events=None, *, observed=None, cursor=None):
        observed = at(16, 2) if observed is None else observed
        events = [(0, '0.0001'), (8, '0.0001'), (16, '0.0001')] if events is None else events
        rows = [dict(instId='BTC-USDT-SWAP', fundingTime=millis(at(hour)), realizedRate=rate,
                     fundingRate='0.99') for hour, rate in sorted(events, reverse=True)]
        cursor = observed - timedelta(seconds=1) if cursor is None else cursor
        return dict(url='https://www.okx.com/api/v5/public/funding-rate-history?after=' + millis(cursor) + '&instId=BTC-USDT-SWAP&limit=100',
            request_started_at=stamp(observed-timedelta(seconds=1)), received_at=stamp(observed),
            http_status=200, response_body=json.dumps(dict(code='0', msg='', data=rows), separators=(',', ':')).encode())

    def observed(self, model, *, pages=None, start=None, observed=None):
        observed = at(16, 2) if observed is None else observed
        return model.observe((self.page(observed=observed),) if pages is None else tuple(pages),
            coverage_start=at() if start is None else start, observed_at=observed)

    def position(self, *, opened=None, closed=None, **changes):
        value = dict(schema_version='contracts-v0.1', position_id='position-public', symbol='BTC_USDT_PERP',
            actual_quantity='0', reconciliation_status='CONSISTENT', opened_at=stamp(at(8) if opened is None else opened),
            broker_state_observed_at=stamp(at(12) if closed is None else closed))
        value.update(changes)
        return value

    def entry(self, *, side=Side.BUY, opened=None, quantity='0.001', price='100000'):
        opened = at(8) if opened is None else opened
        client = stable_client_order_id('plan-public', 'entry')
        request = OrderRequest('contracts-v0.1', stable_order_request_id(client), 'plan-public', client,
            'BTC_USDT_PERP', side, 'MARKET', Decimal(quantity), 'base-asset-v0.1', 'BASE_ASSET', 'BTC',
            opened-timedelta(seconds=1))
        broker = PaperBroker(); broker.submit_order(request)
        fill = broker.record_fill(client, quantity=Decimal(quantity), price=Decimal(price), filled_at=opened)
        return request, (fill,)

    def allocate(self, model, observed, *, side=Side.BUY, position=None, quantity='0.001', price='100000', calculated=None):
        position = self.position() if position is None else position
        opened = datetime.fromisoformat(position['opened_at'].replace('Z', '+00:00'))
        request, fills = self.entry(side=side, opened=opened, quantity=quantity, price=price)
        plan = dict(schema_version='contracts-v0.1', trade_plan_id='plan-public', symbol='BTC_USDT_PERP',
            direction='LONG' if side == Side.BUY else 'SHORT')
        return model.allocate(plan, position, request, fills, observed=observed,
            calculated_at=at(16, 2) if calculated is None else calculated)

    def test_registered_model_uses_actual_settled_rate_for_signed_paper_allocation(self):
        model = self.model(); observed = self.observed(model)
        for side, cost in ((Side.BUY, '0.01'), (Side.SELL, '-0.01')):
            with self.subTest(side=side):
                evidence = self.allocate(model, observed, side=side)
                self.assertEqual((evidence['funding_cost'], evidence['status'], evidence['source_record_count']), (cost, 'INCLUDED', 1))
                self.assertEqual(evidence['source_kind'], 'PAPER_MODEL')
                self.assertEqual(evidence['source_version'], 'paper-public-recorded-entry-notional-v0.1')
                self.assertRegex(evidence['source_material_hash'], r'^[0-9a-f]{64}$')
                self.assertRegex(evidence['funding_evidence_id'], r'^fundev_[0-9a-f]{64}$')

    def test_negative_zero_and_offsetting_events_never_mean_absent_records(self):
        for events, opened, expected, count in (
            ([(0, '0'), (8, '-0.0001'), (16, '0')], at(8), '-0.01', 1),
            ([(0, '0'), (8, '-0.0000'), (16, '0')], at(8), '0', 1),
            ([(0, '0.0001'), (8, '-0.0001'), (16, '0')], at(), '0', 2)):
            with self.subTest(events=events):
                model = self.model(); observed = self.observed(model, pages=[self.page(events)])
                evidence = self.allocate(model, observed, position=self.position(opened=opened))
                self.assertEqual((evidence['funding_cost'], evidence['source_record_count'], evidence['status']), (expected, count, 'INCLUDED'))

    def test_half_open_boundaries_zero_requires_positive_complete_source(self):
        model = self.model(); observed = self.observed(model)
        first = self.allocate(model, observed, position=self.position(closed=at(16)))
        self.assertEqual((first['funding_cost'], first['source_record_count']), ('0.01', 1))
        empty = self.allocate(model, observed, position=self.position(opened=at(8)+timedelta(microseconds=1)))
        self.assertEqual((empty['status'], empty['source_record_count'], empty['funding_cost']), ('ZERO_CONFIRMED', 0, '0'))

    def test_missing_future_upper_bracket_stays_pending_not_zero(self):
        model = self.model(); observed = self.observed(model, pages=[self.page([(0, '0'), (8, '0.0001')])])
        self.assertFalse(model.health(observed, now=at(16, 2)))
        with self.assertRaisesRegex(ValueError, 'FUNDING_SOURCE_INCOMPLETE'):
            self.allocate(model, observed)

    def test_health_has_actual_settled_grid_freshness_and_clock_guards(self):
        model = self.model(); observed = self.observed(model)
        self.assertTrue(model.health(observed, now=at(16, 2)))
        self.assertTrue(model.health(observed, now=at(16, 62)))
        self.assertFalse(model.health(observed, now=at(16, 63)))
        self.assertFalse(model.health(observed, now=at(16, 1)))
        self.assertFalse(model.health(observed, now=at(24)))
        self.assertFalse(self.model().health(observed, now=at(16, 2)))

    def test_observation_is_source_owned_detached_and_identity_ignores_calculation_time(self):
        model = self.model(); pages = [self.page()]; observed = self.observed(model, pages=pages)
        pages[0]['response_body'] = b'{}'
        first = self.allocate(model, observed)
        later = self.allocate(model, observed, calculated=at(22))
        self.assertEqual(first['funding_evidence_id'], later['funding_evidence_id'])
        forged = replace(observed, canonical_json=observed.canonical_json+' ')
        with self.assertRaises(ValueError): self.allocate(model, forged)
        with self.assertRaises(ValueError): self.allocate(self.model(), observed)

    def test_grid_gaps_duplicates_predictions_and_wrong_instrument_are_refused(self):
        variants = []
        page = self.page(); raw = json.loads(page['response_body'])
        for change in ('gap', 'duplicate', 'prediction_only', 'instrument', 'off_grid', 'bad_rate'):
            changed = deepcopy(raw)
            if change == 'gap': changed['data'].pop(1)
            if change == 'duplicate': changed['data'].append(deepcopy(changed['data'][0]))
            if change == 'prediction_only': changed['data'][0]['realizedRate'] = ''
            if change == 'instrument': changed['data'][0]['instId'] = 'ETH-USDT-SWAP'
            if change == 'off_grid': changed['data'][0]['fundingTime'] = millis(at(15))
            if change == 'bad_rate': changed['data'][0]['realizedRate'] = 'NaN'
            variants.append(dict(page, response_body=json.dumps(changed).encode()))
        for page in variants:
            with self.subTest(page=page), self.assertRaises(ValueError): self.observed(self.model(), pages=[page])

    def test_page_provenance_bounds_partial_pages_and_private_endpoint_are_refused(self):
        page = self.page()
        invalid = [dict(page, url=page['url'].replace('/public/funding-rate-history', '/account/bills')),
            dict(page, http_status=500), dict(page, extra=True), dict(page, received_at=stamp(at(16, 3))),
            dict(page, response_body=b'{'), dict(page, response_body=b'x'*(2*1024*1024+1))]
        for p in invalid:
            with self.subTest(kind=p.keys()), self.assertRaises(ValueError): self.observed(self.model(), pages=[p])
        with self.assertRaises(ValueError): self.observed(self.model(), pages=[])
        with self.assertRaises(ValueError): self.observed(self.model(), pages=[page]*17)
        with self.assertRaises(ValueError): self.observed(self.model(), start=at(-24*90))

    def test_actual_entry_fill_basis_and_lineage_not_approved_notional(self):
        model = self.model(); observed = self.observed(model)
        evidence = self.allocate(model, observed, quantity='0.0004', price='100000')
        self.assertEqual(evidence['funding_cost'], '0.004')
        request, fills = self.entry(); plan = dict(schema_version='contracts-v0.1', trade_plan_id='plan-public', symbol='BTC_USDT_PERP', direction='LONG')
        for bad_fills in ((), (fills[0], fills[0]), (replace(fills[0], trade_plan_id='other'),),
                          (replace(fills[0], side=Side.SELL),), (replace(fills[0], filled_at=at(9)),)):
            with self.subTest(fills=bad_fills), self.assertRaises(ValueError):
                model.allocate(plan, self.position(), request, bad_fills, observed=observed, calculated_at=at(16, 2))
        for bad_position in (self.position(actual_quantity='1'), self.position(symbol='ETH_USDT_PERP'), self.position(reconciliation_status='UNKNOWN')):
            with self.subTest(position=bad_position), self.assertRaises(ValueError):
                model.allocate(plan, bad_position, request, fills, observed=observed, calculated_at=at(16, 2))

    def test_arithmetic_is_exact_under_hostile_ambient_context_and_rejects_rounding(self):
        model = self.model(); observed = self.observed(model)
        with localcontext() as ctx:
            ctx.prec = 2; ctx.rounding = ROUND_DOWN
            evidence = self.allocate(model, observed, price='100001.23456789')
        self.assertEqual(evidence['funding_cost'], '0.010000123456789')
        # Input is finite decimal34 but this selected source deliberately cannot
        # silently round a product requiring more than downstream34 digits.
        with self.assertRaises(ValueError):
            self.allocate(model, observed, quantity='0.123456789012345678', price='123456789012345678.1234567890123456')

    def test_existing_e5_canonical_signed_funding_validator_accepts_exact_allocation(self):
        from position.trade_result import _validate_canonical_funding_evidence
        model = self.model(); observed = self.observed(model)
        evidence = self.allocate(model, observed)
        status, cost, identity, _ = _validate_canonical_funding_evidence(evidence,
            trade_plan_id='plan-public', position_id='position-public', symbol='BTC_USDT_PERP', opened_at=at(8), closed_at=at(12))
        self.assertEqual((status, cost, identity), ('INCLUDED', Decimal('0.01'), evidence['funding_evidence_id']))

    def test_source_observation_also_ignores_hostile_decimal_context(self):
        page = self.page([(0, '0'), (8, '0.999999999999999999'), (16, '0')])
        model = self.model()
        with localcontext() as ctx:
            ctx.prec = 2; ctx.rounding = 'ROUND_UP'
            try:
                observed = self.observed(model, pages=[page])
            except funding.FundingEvidenceError as error:
                self.fail('Valid settled rate changed meaning under ambient Decimal context: '+error.code)
        self.assertTrue(model.health(observed, now=at(16, 2)))

    def test_complete_page_chain_and_last_page_are_bound_to_source_identity(self):
        pages = [self.page([(8, '0.0001'), (16, '0.0001')]),
                 self.page([(0, '0')], cursor=at(8))]
        model = self.model(); observed = self.observed(model, pages=pages)
        first = self.allocate(model, observed)
        pages[1] = self.page([(0, '0.00001')], cursor=at(8))
        changed = self.observed(model, pages=pages)
        self.assertNotEqual(self.allocate(model, changed)['funding_evidence_id'], first['funding_evidence_id'])
        with self.assertRaises(ValueError): self.observed(model, pages=[pages[0]])
        with self.assertRaises(ValueError): self.observed(model, pages=[pages[0], self.page([(0, '0')], cursor=at(7))])

    def test_duplicate_json_fields_and_numeric_rates_do_not_create_source_truth(self):
        model = self.model(); page = self.page()
        for raw in (b'{"code":"0","code":"0","msg":"","data":[]}',
                    page['response_body'].replace(b'"0.0001"', b'0.0001')):
            with self.subTest(raw=raw[:50]), self.assertRaises(ValueError):
                self.observed(model, pages=[dict(page, response_body=raw)])


if __name__ == '__main__':
    unittest.main()
