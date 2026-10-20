"""genuine H01 original-exit fixture, not TestCase.

Same H01 service/provider throughout. Native wire rows are explicit controlled
FIXTURE observations parsed by actual owners; no PaperBroker/SQL financial writes.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from application.trading.orchestrator import TradingOrchestrator
from application.trading.provider import FakeProductProvider
from brokers.okx_product_state import restore_product_readback
from brokers.paper_state import decode_fact
from execution.models import OrderRequest,OrderResult,Fill
from execution.protection_trigger import prepare_trigger_validated_protection_order
from execution.protection_registry_evidence_boundary import build_protection_registry_multiplicity_evidence
from market_data.current import MarketSnapshot
from position import CurrentProtectionRegistryAuthority
from position.entry_observation import product_entry_position_id
from position.protection import build_protect_position_action
from position.protection_registry_policy import canonical_protection_registry_hash
from position.protection_trigger_validity import build_protection_trigger_validity_evidence
from position.lifecycle_execution_binding import (validate_position_lifecycle_execution_evidence_binding,
    build_position_lifecycle_execution_evidence_binding)
from tests.product import h01_entry_fixture as entry_fixtures
from tests.product import test_trading_inventory_v02 as inventory_fixtures
from tests.brokers import test_okx_demo_adapter as metadata_fixtures
from tests.execution import test_protection_registry_evidence as registry_fixtures


def stamp(value): return value.isoformat().replace('+00:00','Z')


class H01OriginalExitFixture:
    def __init__(self,testcase):
        self.test=testcase
        self._context=entry_fixtures.H01EntryFixture()
        self.f=None

    def __enter__(self):
        self.f=self._context.__enter__()
        try:
            self.service=self.f.service;self.provider=self.f.provider
            self.provider_identity=id(self.provider)
            self.runner=TradingOrchestrator(self.service)
            first=self.runner.evaluate_entry(self.f.bundle,**self.f.arguments)
            self.test.assertEqual('ACK_PENDING',first.dispatch_outcome.status)
            self.entry_operation=first.operation_id
            self.entry_decision=self.f.dispatch.entry_decision(self.service.run_id,self.f.authority.identity,self.f.bundle.boundary)
            self.plan=self.entry_decision.effects[1]['payload']
            self.test.assertEqual(self.f.plan,self.plan)
            self.entry=restore_product_readback(self.f.dispatch.operation(self.service.run_id,self.entry_operation).request)
            self.contracts=format(self.entry.materialization.provider_contract_quantity,'f')
            self.test.assertEqual(Decimal('10'),Decimal(self.contracts),'Fail visibly if the existing H01 fixture recipe changes')
            # Consume the fixture's original live-zero readback script normally,
            # then append actual full-fill rows. No provider/script replacement.
            self.clock[0]+=timedelta(seconds=1)
            self.service.reconcile(self.entry_operation,expected_revision=self.revision)
            self.test.assertFalse(self.provider._responses)
            self.clock[0]+=timedelta(seconds=1)
            self.first_fill_at=self.clock[0]-timedelta(seconds=1)
            order=dict(self.entry.materialization.body,instType='SWAP',ordId='1234',
                state='filled',accFillSz=self.contracts,avgPx='60000',reduceOnly=False)
            fill=dict(instId='BTC-USDT-SWAP',clOrdId=self.entry.materialization.provider_cl_ord_id,
                ordId='1234',tradeId='1',side='buy',posSide='net',fillSz=self.contracts,fillPx='60000',
                fillTime=str(int(self.first_fill_at.timestamp()*1000)),fee='-0.01',feeCcy='USDT')
            self.append(dict(code='0',data=[order]),dict(code='0',data=[fill]),self.position_response(self.contracts))
            self.service.reconcile(self.entry_operation,expected_revision=self.revision)
            self.metadata,self.read_proof=self.fresh()
            self.native=self.service.read_position(metadata=self.metadata,proof=self.read_proof,
                expected_revision=self.revision,expected_provider_position_id='5678')
            self.service.project_entry_position(self.entry_operation,self.native,metadata=self.metadata,
                proof=self.read_proof,expected_revision=self.revision)
            entered=self.assert_binding()
            self.first_projection=entered.current_position_projection
            self.first_binding=entered.current_lifecycle_execution_binding
            self.test.assertEqual('OPEN_UNPROTECTED',self.first_projection.payload['lifecycle_state'])
            self.test.assertEqual(self.first_fill_at,datetime_utc(self.first_projection.payload['opened_at']))
            self.protect()
            return self
        except BaseException:
            self.__exit__(None,None,None)
            raise

    def __exit__(self,*args): return self._context.__exit__(*args)
    @property
    def clock(self): return self.f.authority.clock
    @property
    def revision(self): return self.f.authority.revision

    def append(self,*responses):
        self.test.assertEqual(self.provider_identity,id(self.service.provider))
        self.provider._responses.extend(FakeProductProvider(list(responses))._responses)

    def position_response(self,quantity,*,average='60000'):
        return dict(code='0',data=[dict(instType='SWAP',instId='BTC-USDT-SWAP',mgnMode='isolated',
            posSide='net',ccy='USDT',posId='5678',pos=quantity,avgPx=average,
            uTime=str(int(self.clock[0].timestamp()*1000)))])

    def fresh(self,role='READ_ONLY_RECONCILIATION'):
        now=self.clock[0]
        metadata=replace(metadata_fixtures._metadata(now),ct_val=Decimal('0.0001'))
        proof=self.f.capabilities.issue(role,self.f.account,metadata,observed_at=now,now=now)
        return metadata,proof

    def recover(self):
        return self.f.canonical.recover(trade_plan_id=self.plan['trade_plan_id'],
            position_id=product_entry_position_id(self.plan['trade_plan_id']))

    def assert_binding(self):
        recovered=self.recover()
        self.test.assertTrue(recovered.restart_authoritative,recovered.reason_codes)
        validate_position_lifecycle_execution_evidence_binding(recovered.current_lifecycle_execution_binding.payload,
            recovered.current_position_projection.payload)
        rebuilt=build_position_lifecycle_execution_evidence_binding(recovered.current_position_projection.payload,
            order_requests=tuple(decode_fact(OrderRequest,row.payload) for row in recovered.order_requests),
            order_results=tuple(decode_fact(OrderResult,row.payload) for row in recovered.order_result_observations),
            fills=tuple(decode_fact(Fill,row.payload) for row in recovered.fills))
        self.test.assertEqual(rebuilt,recovered.current_lifecycle_execution_binding.payload)
        self.test.assertEqual(self.provider_identity,id(self.service.provider))
        return recovered

    def protect(self):
        # Procedural existing GenuineProtectedCloseContext.protect recipe ONLY.
        # No other trading service is constructed and no generic-close tail runs.
        now=self.clock[0];recovered=self.assert_binding()
        position=recovered.current_position_projection.payload
        binding=recovered.current_lifecycle_execution_binding.payload
        action=build_protect_position_action(position,self.plan,created_at=now,expires_at=now+timedelta(seconds=30))
        self.f.canonical.persist_position_action(action)
        market=dict(schema_version='contracts-v0.1',symbol='BTC_USDT_PERP',source='FIXTURE_H01_EXIT_MARKET',
            observed_at=stamp(now),received_at=stamp(now),health_status='HEALTHY',last_price='60000',freshness_ms=0)
        trigger=build_protection_trigger_validity_evidence(position,action,self.plan,market,
            market_freshness_classification='FRESH',evaluated_at=now)
        request=prepare_trigger_validated_protection_order(action,self.plan,position,trigger,market,
            market_freshness_classification='FRESH',now=now)
        registry=registry_fixtures.ProtectionRegistryMultiplicityEvidenceTests(methodName='runTest')
        registry.setUp();self.test.addCleanup(registry.doCleanups)
        registry.provider_observed_at=now;registry.provider_received_at=now;registry.evaluated_at=now
        lineage=registry.intended_lineage(position,position_action_id=action['position_action_id'],
            position_action_hash=canonical_protection_registry_hash(action),
            approved_trade_plan_hash=canonical_protection_registry_hash(self.plan),
            protection_order_request_hash=canonical_protection_registry_hash(request),
            protection_order_request_ref=request.order_request_id,
            trigger_validity_ref=trigger['protection_trigger_validity_id'],
            lifecycle_projection_ref=position['lifecycle_projection_id'],
            lifecycle_execution_binding_ref=binding['lifecycle_execution_binding_id'])
        evidence=build_protection_registry_multiplicity_evidence(registry.input_for(position=position,lineage=lineage,
            observed_set=registry.observed_set([]),lifecycle_projection_ref=position['lifecycle_projection_id'],
            lifecycle_execution_binding_ref=binding['lifecycle_execution_binding_id']))
        authority=CurrentProtectionRegistryAuthority(evidence['position_ref'],evidence['position_hash'],position,position,
            binding,evidence['provider_identity_ref'],evidence['provider_instrument_ref'],
            evidence['provider_observation_generation_id'],evidence['provider_observed_at'],
            evidence['provider_received_at'],evidence['observed_active_protection_set_hash'])
        metadata,proof=self.fresh('PROTECTION_STOP')
        self.stop=self.service.translator.prepare_protection(action=action,plan=self.plan,position=position,
            trigger_evidence=trigger,market=market,market_freshness_classification='FRESH',
            registry_evidence=evidence,registry_authority=authority,metadata=metadata,proof=proof,now=now)
        self.algo=dict(self.stop.materialization.body,instType='SWAP',algoId='2345',state='live',ordIdList=[],
            actualSz='0',failCode='',cTime=str(int(now.timestamp()*1000)),uTime=str(int(now.timestamp()*1000)))
        self.append(dict(code='0',data=[dict(algoId='2345',algoClOrdId=self.algo['algoClOrdId'],sCode='0')]))
        self.service.execute(self.stop,expected_revision=self.revision)
        self.clock[0]+=timedelta(seconds=1)
        self.refresh_protected()

    def refresh_protected(self):
        scans=inventory_fixtures.TradingInventoryV02Tests(methodName='runTest').scans([self.algo])
        self.append(dict(code='0',data=[self.algo]),self.position_response(self.contracts),*scans)
        self.service.reconcile(self.stop.canonical_request.order_request_id,expected_revision=self.revision)
        self.metadata,self.read_proof=self.fresh()
        self.native=self.service.read_position(metadata=self.metadata,proof=self.read_proof,
            expected_revision=self.revision,expected_provider_position_id='5678')
        self.service.project_entry_position(self.entry_operation,self.native,metadata=self.metadata,
            proof=self.read_proof,expected_revision=self.revision)
        inventory=self.service.read_algo_inventory(metadata=self.metadata,proof=self.read_proof,expected_revision=self.revision)
        self.service.project_protection(self.stop.canonical_request.order_request_id,self.native,inventory,
            metadata=self.metadata,proof=self.read_proof,expected_revision=self.revision)
        recovered=self.assert_binding()
        self.test.assertEqual('OPEN_PROTECTED',recovered.current_position_projection.payload['lifecycle_state'])
        self.test.assertEqual(self.first_projection.payload['opened_at'],recovered.current_position_projection.payload['opened_at'])
        self.test.assertFalse(self.provider._responses)
        return recovered

    def exit_arguments(self):
        metadata,close_proof=self.fresh('POSITION_EXIT')
        self.test.assertEqual(self.metadata,metadata)
        now=self.clock[0]
        return dict(native_position=self.native,metadata=self.metadata,read_proof=self.read_proof,
            close_proof=close_proof,market_snapshot=MarketSnapshot('contracts-v0.1','BTC_USDT_PERP',now,now,
                'HEALTHY','FIXTURE_H01_EXIT_MARKET',last_price=Decimal('60000'),freshness_ms=0),
            market_freshness_classification='FRESH',action_expires_at=now+timedelta(seconds=30),
            expected_revision=self.revision)

    def close_responses(self,close,*,flat):
        now=self.clock[0]
        if not hasattr(self,'first_close_fill'):
            self.first_close_fill=dict(instId='BTC-USDT-SWAP',clOrdId=close.materialization.provider_cl_ord_id,
                ordId='3456',tradeId='2',side='sell',posSide='net',fillSz='4',fillPx='60000',
                fillTime=str(int((now-timedelta(seconds=1)).timestamp()*1000)),fee='-0.01',feeCcy='USDT')
        fills=[deepcopy(self.first_close_fill)]
        if flat:
            fills.append(dict(self.first_close_fill,tradeId='3',fillSz='6',fillTime=str(int(now.timestamp()*1000))))
        order=dict(close.materialization.body,instType='SWAP',ordId='3456',
            state='filled' if flat else 'partially_filled',accFillSz=self.contracts if flat else '4',avgPx='60000')
        return dict(code='0',data=[order]),dict(code='0',data=fills)

    def project_residual(self,close,*,flat):
        self.append(self.position_response('0' if flat else '6',average='0' if flat else '60000'))
        metadata,proof=self.fresh()
        native=self.service.read_position(metadata=metadata,proof=proof,expected_revision=self.revision,
            expected_provider_position_id='5678')
        self.service.project_close_position(close.canonical_request.order_request_id,native,
            metadata=metadata,proof=proof,expected_revision=self.revision)
        return self.assert_binding()


def datetime_utc(value):
    from datetime import datetime
    return datetime.fromisoformat(value.replace('Z','+00:00'))
