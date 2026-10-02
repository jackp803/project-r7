"""Continuous application composition of actual E1/E2/E4/E5 owners.

This engine calculates no alternative lifecycle, risk decision or final PnL.
The returned simulation state and canonical owner effects are committed by E6.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import json

from brokers.paper import PaperBroker
from brokers.paper_state import decode_fact, encode_fact
from execution.close import prepare_close_order
from execution.funding import produce_paper_zero_funding_evidence
from execution.gateway import ExecutionGateway
from execution.models import OrderRequest, OrderResult, Fill, OrderStatus, Side
from execution.protection_trigger import prepare_trigger_validated_protection_order
from market_data.candle import Candle
from market_data.current import MarketSnapshot
from position import (ProtectionResultEvidence, interpret_protection_result,
    build_position_lifecycle_transition_with_execution_binding,
    build_position_lifecycle_reattestation_with_execution_binding,
    build_position_lifecycle_closed_transition,
    build_position_lifecycle_execution_evidence_binding, build_trade_result)
from position.entry_observation import build_entry_projection
from position.exit_requests import (anchor_exit_request, interpret_exit_request,
    resolve_exit_constraints, CurrentExitAuthority)
from position.exit_state import encode_exit_anchor, restore_exit_anchor
from position.lifecycle_projection import _broker_fact_payload
from position.close import authorize_close_position_action
from risk.engine import RiskContext, RiskProposal, evaluate_trade_intent, build_approved_trade_plan
from strategy import StrategyRuntime, parse_strategy_definition, build_trade_intent
from strategy.v02.exits import ExitRequest, build_exit_request
from strategy.v02.temporal import build_asof_bundle, assess_submission_validity
from .orchestrator import PaperStep
from .observation import initial_forward_observation, record_forward_observation


def utc(value): return datetime.fromisoformat(value.replace('Z', '+00:00'))
def stamp(value): return value.isoformat().replace('+00:00', 'Z')


def initial_runtime_state(service, strategy):
    # Initial state is independent of invocation time for identical start retries.
    return dict(schema_version='r7-paper-runtime-v0.2', mode=service.simulation.as_dict()['mode'],
        paper_entries_allowed=True, strategy_id=strategy.identity.strategy_id,
        strategy_version=strategy.identity.strategy_version, strategy_content_hash=strategy.content_hash,
        position=None, plan=None, risk_decision=None, entry_request=None,
        protection_request=None, protection_action=None, exit_request=None, exit_action=None, exit_source_position=None,
        strategy_exit_request=None, exit_anchor=None, last_market=None,
        candles={}, last_entry_boundary=None, last_signal=None, last_intent=None,
        closed_trades=[], entry_days={}, market_status='NOT_CONNECTED', forward=initial_forward_observation())


def _market(value):
    material=dict(value)
    for name in ('observed_at', 'received_at'): material[name]=utc(material[name])
    for name in ('last_price', 'best_bid', 'best_ask'):
        if material.get(name) is not None: material[name]=Decimal(material[name])
    return MarketSnapshot(**material)


def _candle(value):
    material=dict(value)
    for name in ('open_time', 'close_time', 'received_at'):
        if material.get(name) is not None: material[name]=utc(material[name])
    for name in ('open', 'high', 'low', 'close', 'volume'): material[name]=Decimal(material[name])
    return Candle(**material)


def _evidence(broker, plan_id):
    requests, results, fills = [], [], []
    for item in broker.export_state()['payload']['submissions']:
        if item['request']['trade_plan_id'] != plan_id: continue
        requests.append(decode_fact(OrderRequest, item['request']))
        results.append(decode_fact(OrderResult, item['acknowledgement']))
        if item['order'] is not None:
            current=decode_fact(OrderResult,item['order']['result'])
            if current != results[-1]: results.append(current)
            fills.extend(decode_fact(Fill,value) for value in item['order']['fills'])
    return dict(order_requests=tuple(requests),order_results=tuple(results),fills=tuple(fills))


class PaperEngine:
    def __init__(self, service, identity):
        self.service=service; self.identity=identity
        self.strategy=parse_strategy_definition(service.registry.get_strategy(identity).definition_json)
        self.config=service.simulation.as_dict(); self.reconciled=False; self.recovery_reason=None

    def reconcile(self, state, canonical):
        broker=PaperBroker.from_state(state['broker']); runtime=state['runtime']
        position=runtime['position']
        if position is not None:
            signed=Decimal(position['actual_quantity']) * (1 if position['side']=='LONG' else -1)
            if broker.query_position(position['symbol']).net_quantity != signed:
                self.recovery_reason='POSITION_RECONCILIATION_REQUIRED'; return
            recovered=canonical.recover(position_id=position['position_id'])
            if recovered.status != 'READY':
                self.recovery_reason='PROTECTION_RECONCILIATION_REQUIRED' if position['lifecycle_state']=='RECONCILIATION_REQUIRED' else 'CANONICAL_RECOVERY_NOT_READY'
                return
        elif broker.query_position(self.strategy.symbol).net_quantity != 0:
            self.recovery_reason='UNKNOWN_RECOVERED_EXPOSURE'; return
        if runtime['entry_request']:
            request=decode_fact(OrderRequest,runtime['entry_request'])
            result=broker.query_order(request.client_order_id)
            if result is None: self.recovery_reason='ENTRY_ORDER_UNKNOWN'; return
            # Explicit query/reconcile uses the restored broker's owner truth.
            broker.reconcile(request,order_snapshot=result,position_snapshot=broker.query_position(request.symbol))
        self.reconciled=True; self.recovery_reason=None

    @staticmethod
    def _effect(effects, kind, payload): effects.append(dict(kind=kind,payload=payload))

    def _save_projection(self, runtime, broker, effects, projection):
        evidence=_evidence(broker,runtime['plan']['trade_plan_id'])
        binding=build_position_lifecycle_execution_evidence_binding(projection,**evidence)
        self._effect(effects,'POSITION_PROJECTION',projection)
        self._effect(effects,'LIFECYCLE_EXECUTION_BINDING',binding)
        runtime['position']=projection

    def _fresh(self, market, now):
        return (market is not None and market.health_status=='HEALTHY' and market.last_price is not None
            and market.symbol==self.strategy.symbol and market.observed_at<=now and market.received_at<=now
            and (now-market.observed_at).total_seconds()<=self.config['market_max_age_seconds']
            and type(market.freshness_ms) is int
            and market.freshness_ms<=self.config['market_max_age_seconds']*1000)

    def _entry_allowed(self, runtime, now):
        if not self.reconciled: return False,'RECONCILIATION_REQUIRED'
        if not runtime['paper_entries_allowed']: return False,'PAPER_ENTRIES_PAUSED'
        if not self.service.authorized: return False,'PAPER_WORKFLOW_NOT_AUTHORIZED'
        if self.service.registry.get_strategy(self.identity).current_lifecycle_state!='PAPER':
            return False,'STRATEGY_NOT_IN_PAPER'
        product=self.service.registry.candidate_product_assessment(self.identity)
        if product.risk_policy_hash!=self.service.risk.policy_hash: return False,'RISK_POLICY_CHANGED'
        validity=assess_submission_validity(json.loads(self.service.validity_json),now)
        if not validity.new_entry_allowed: return False,'SUBMISSION_'+validity.status
        return True,None

    def _fill(self, broker, request, quantity, market, now, effects, *, cancel_entry_remainder=False):
        direction=Decimal(1) if request.side==Side.BUY else Decimal(-1)
        price=market.last_price*(1+direction*Decimal(self.config['slippage_bps'])/10000)
        fee=quantity*price*Decimal(self.config['fee_rate'])
        producer=broker.record_entry_fill_and_cancel_remainder if cancel_entry_remainder else broker.record_fill
        fill=producer(request.client_order_id,quantity=quantity,price=price,
            filled_at=now,fee=fee,fee_currency='USDT',liquidity_role='TAKER')
        self._effect(effects,'ORDER_RESULT',encode_fact(broker.query_order(request.client_order_id)))
        self._effect(effects,'FILL',encode_fact(fill))
        return fill

    def _fill_entry(self, runtime, broker, effects, market, now):
        if not runtime['entry_request'] or runtime['position'] is not None: return None
        request=decode_fact(OrderRequest,runtime['entry_request'])
        current=broker.query_order(request.client_order_id)
        if current is None: return 'BLOCKED',('ENTRY_ORDER_UNKNOWN',)
        if current.order_status not in (OrderStatus.OPEN,OrderStatus.PARTIALLY_FILLED): return None
        allowed,reason=self._entry_allowed(runtime,now)
        if not allowed or now>=utc(runtime['plan']['expires_at']):
            if now<=current.observed_at:
                return 'BLOCKED',('ENTRY_CANCELLATION_OBSERVATION_PENDING',)
            canceled=broker.cancel_order(request.client_order_id,observed_at=now)
            self._effect(effects,'ORDER_RESULT',encode_fact(canceled))
            return ('EXPIRED',('ENTRY_PLAN_EXPIRED',)) if now>=utc(runtime['plan']['expires_at']) else ('BLOCKED',(reason,))
        if not self._fresh(market,now) or market.observed_at<=request.created_at: return None
        quantity=request.quantity*Decimal(self.config['initial_fill_fraction'])
        self._fill(broker,request,quantity,market,now,effects,cancel_entry_remainder=quantity<request.quantity)
        composed=build_entry_projection(runtime['plan'],request,broker.query_order(request.client_order_id),
            broker.query_fills(request.client_order_id),broker.query_position(request.symbol),observed_at=now)
        for item in composed.projections: self._save_projection(runtime,broker,effects,item.lifecycle_projection)
        exits=ExitRequest(json.dumps(runtime['strategy_exit_request']))
        runtime['exit_anchor']=encode_exit_anchor(anchor_exit_request(exits,runtime['position'],runtime['plan']))
        day=now.date().isoformat(); runtime['entry_days'][day]=runtime['entry_days'].get(day,0)+1
        return None

    def _refresh_position(self, runtime, broker, effects, now):
        position=runtime['position']
        signed=Decimal(position['actual_quantity'])*(1 if position['side']=='LONG' else -1)
        if broker.query_position(position['symbol']).net_quantity!=signed:
            raise ValueError('Current Paper exposure differs from durable E5 position')
        # This clock belongs to the synchronous E4 readback above. It never
        # changes opened_at or the first-fill exit anchor. E5 reattests the
        # exact retained financial facts against the complete execution graph.
        if now > utc(position['broker_state_observed_at']):
            source=dict(_broker_fact_payload(position),lifecycle_state=position['lifecycle_state'],
                        broker_state_observed_at=stamp(now))
            composed=build_position_lifecycle_reattestation_with_execution_binding(source,position,
                lifecycle_interpreted_at=now,**_evidence(broker,runtime['plan']['trade_plan_id']))
            self._save_projection(runtime,broker,effects,composed.lifecycle_projection)

    def _observe_protection(self, runtime, broker, effects, now):
        position=runtime['position']
        if not runtime['protection_request'] or position['lifecycle_state'] not in ('OPEN_PROTECTED','PROFIT_PROTECTED'):
            return
        request=decode_fact(OrderRequest,runtime['protection_request'])
        interpreted=interpret_protection_result(request,ProtectionResultEvidence(True,
            broker.query_order(request.client_order_id)),position['lifecycle_state'])
        if interpreted.event is not None:
            source=dict(_broker_fact_payload(position),lifecycle_state=position['lifecycle_state'],
                        broker_state_observed_at=stamp(now))
            composed=build_position_lifecycle_transition_with_execution_binding(source,position,
                lifecycle_event=interpreted.event,lifecycle_interpreted_at=now,
                **_evidence(broker,runtime['plan']['trade_plan_id']))
            self._save_projection(runtime,broker,effects,composed.lifecycle_projection)

    def _request_close(self, runtime, broker, effects, action, event, now):
        position=runtime['position']
        request=prepare_close_order(action,runtime['plan'],position,now=now)
        ack=broker.submit_order(request)
        self._effect(effects,'POSITION_ACTION',action)
        self._effect(effects,'ORDER_REQUEST',encode_fact(request)); self._effect(effects,'ORDER_RESULT',encode_fact(ack))
        source=dict(_broker_fact_payload(position),lifecycle_state=position['lifecycle_state'])
        composed=build_position_lifecycle_transition_with_execution_binding(source,position,
            lifecycle_event=event,lifecycle_interpreted_at=now,**_evidence(broker,runtime['plan']['trade_plan_id']))
        self._save_projection(runtime,broker,effects,composed.lifecycle_projection)
        runtime['exit_request']=encode_fact(request); runtime['exit_action']=action
        runtime['exit_source_position']=source
        return 'EXIT_REQUESTED',()

    def _close(self, runtime, broker, effects, request, action, market, now):
        position=runtime['position']; plan=runtime['plan']
        if not self._fresh(market,now): return 'EXIT_REQUESTED',('CURRENT_MARKET_UNAVAILABLE',)
        if now<=request.created_at or now<=utc(position['broker_state_observed_at']):
            return 'EXIT_REQUESTED',('POSITION_REDUCTION_OBSERVATION_PENDING',)
        self._fill(broker,request,Decimal(position['actual_quantity']),market,now,effects)
        flat=broker.observe_position_after_close(request,runtime['exit_source_position'],observed_at=now)
        funding=produce_paper_zero_funding_evidence(plan,flat,calculated_at=now)
        entry=decode_fact(OrderRequest,runtime['entry_request'])
        result=build_trade_result(plan,current_lifecycle_state=position['lifecycle_state'],exit_authority=action,
            entry_order_requests=(entry,),entry_fills=broker.query_fills(entry.client_order_id),
            exit_order_request=request,exit_fills=broker.query_fills(request.client_order_id),
            final_position=flat,funding_evidence=funding)
        # Cancel the unused simulated protective order only after actual flat
        # observation. Retirement/pause never cancels open-position protection.
        if runtime['protection_request']:
            protection=decode_fact(OrderRequest,runtime['protection_request'])
            current=broker.query_order(protection.client_order_id)
            if current and current.order_status in (OrderStatus.OPEN,OrderStatus.PARTIALLY_FILLED):
                self._effect(effects,'ORDER_RESULT',encode_fact(broker.cancel_order(protection.client_order_id,observed_at=now)))
        closed=build_position_lifecycle_closed_transition(flat,position,trade_result_outcome=result,lifecycle_interpreted_at=now)
        self._save_projection(runtime,broker,effects,closed)
        self._effect(effects,'FUNDING_EVIDENCE',funding)
        self._effect(effects,'TRADE_RESULT',result.trade_result)
        runtime['closed_trades'].append(result.trade_result)
        return 'CLOSED',()

    def _manage(self, runtime, broker, effects, market, now):
        position=runtime['position']
        if position is None or position['lifecycle_state']=='CLOSED': return None
        if runtime['exit_request']:
            return self._close(runtime,broker,effects,decode_fact(OrderRequest,runtime['exit_request']),
                               runtime['exit_action'],market,now)
        self._observe_protection(runtime,broker,effects,now)
        if runtime['position']['lifecycle_state']=='RECONCILIATION_REQUIRED':
            self.reconciled=False
            return 'BLOCKED',('PROTECTION_RECONCILIATION_REQUIRED',)
        self._refresh_position(runtime,broker,effects,now); position=runtime['position']
        if position['lifecycle_state']=='EMERGENCY':
            outcome=authorize_close_position_action(position,runtime['plan'],action='EMERGENCY_EXIT',
                created_at=now,expires_at=now+timedelta(seconds=self.config['action_ttl_seconds']))
            return self._request_close(runtime,broker,effects,outcome.position_action,outcome.event,now)
        fresh=self._fresh(market,now)
        if fresh and position['lifecycle_state'] in ('OPEN_PROTECTED','PROFIT_PROTECTED'):
            stop=decode_fact(OrderRequest,runtime['protection_request'])
            triggered=(market.last_price<=stop.stop_price if position['side']=='LONG' else market.last_price>=stop.stop_price)
            if triggered:
                # The already verified standing stop supplies E5 authority;
                # never replace it with a newly manufactured market EXIT.
                runtime['exit_request']=runtime['protection_request']
                runtime['exit_action']=runtime['protection_action']
                runtime['exit_source_position']=dict(_broker_fact_payload(position),lifecycle_state=position['lifecycle_state'])
                return 'EXIT_REQUESTED',('PROTECTION_TRIGGER_OBSERVED',)
        exits=ExitRequest(json.dumps(runtime['strategy_exit_request']))
        anchor=restore_exit_anchor(runtime['exit_anchor'],request=exits,position=position,plan=runtime['plan'])
        outcome=interpret_exit_request(exits,CurrentExitAuthority(position,runtime['plan'],anchor,
            market if fresh else None,'FRESH' if fresh else 'STALE',now,now+timedelta(seconds=self.config['action_ttl_seconds'])))
        runtime['exit_anchor']=encode_exit_anchor(outcome.anchor)
        if outcome.status=='NON_EXECUTABLE_PROFILE': return 'HOLD',('MODIFY_PROFILE_UNAVAILABLE',)
        if outcome.position_action is None:
            return ('BLOCKED',outcome.reason_codes) if outcome.status=='BLOCKED' else ('HOLD',())
        action=outcome.position_action
        if action['action']=='PROTECT':
            self._effect(effects,'POSITION_ACTION',action)
            request=prepare_trigger_validated_protection_order(action,runtime['plan'],position,
                outcome.trigger_validity_evidence,market,market_freshness_classification='FRESH',now=now)
            ack=broker.submit_order(request)
            self._effect(effects,'ORDER_REQUEST',encode_fact(request)); self._effect(effects,'ORDER_RESULT',encode_fact(ack))
            interpreted=interpret_protection_result(request,ProtectionResultEvidence(True,
                broker.query_order(request.client_order_id),ack),position['lifecycle_state'])
            source=dict(_broker_fact_payload(position),lifecycle_state=position['lifecycle_state'])
            composed=build_position_lifecycle_transition_with_execution_binding(source,position,
                lifecycle_event=interpreted.event,lifecycle_interpreted_at=now,**_evidence(broker,runtime['plan']['trade_plan_id']))
            self._save_projection(runtime,broker,effects,composed.lifecycle_projection)
            runtime['protection_request']=encode_fact(request); runtime['protection_action']=action
            return ('PROTECTED',()) if interpreted.protection_verified else ('BLOCKED',(interpreted.reason_code,))
        # ACK is not a fill or flat observation. A later owner observation must
        # carry the quantity reduction at a strictly later actual clock.
        return self._request_close(runtime,broker,effects,action,outcome.lifecycle_intent,now)

    def _evaluate(self, runtime, broker, effects, market, now):
        allowed,reason=self._entry_allowed(runtime,now)
        if not allowed: return 'BLOCKED',(reason,)
        if runtime['position'] is not None and runtime['position']['lifecycle_state']!='CLOSED': return 'HOLD',()
        if runtime['entry_request'] and runtime['position'] is None:
            current=broker.query_order(runtime['entry_request']['client_order_id'])
            if current is None or current.order_status not in (OrderStatus.CANCELED,OrderStatus.EXPIRED,OrderStatus.REJECTED):
                return 'HOLD',()
        rows={frame:tuple(_candle(row) for row in runtime['candles'].get(frame,[])) for frame in self.strategy.required_timeframes}
        evaluation=rows.get(self.strategy.required_timeframe,())
        if not evaluation: return 'NO_SIGNAL',('EVALUATION_CANDLE_UNAVAILABLE',)
        boundary=evaluation[-1].close_time
        if runtime['last_entry_boundary']==stamp(boundary): return 'HOLD',()
        runtime['last_entry_boundary']=stamp(boundary)
        bundle=build_asof_bundle(rows,boundary,now)
        signal=StrategyRuntime().evaluate(self.strategy,bundle,boundary)
        runtime['last_signal']=signal
        if signal['direction']=='NO_TRADE': return 'NO_SIGNAL',tuple(signal['reason_codes'])
        exits=build_exit_request(self.strategy,bundle); constraints=resolve_exit_constraints(exits)
        if constraints.stop_level is None: return 'BLOCKED',('EXECUTABLE_STOP_REQUIRED',)
        intent=build_trade_intent(signal,entry_profile_version='entry-v0.1',entry_order_type='MARKET',generated_at=boundary,
            strategy_stop_level=constraints.stop_level,strategy_target_level=constraints.target_level,
            max_hold_seconds=constraints.max_hold_seconds)
        runtime['last_intent']=intent
        quantity=Decimal(self.config['quantity']); reference=market.last_price; leverage=Decimal(self.config['leverage'])
        notional=quantity*reference
        closed=runtime['closed_trades']; pnl=sum((Decimal(trade['net_pnl']) for trade in closed),Decimal('0'))
        equity=Decimal(self.config['initial_balance_usdt'])+pnl; peak=Decimal(self.config['initial_balance_usdt'])
        walking=peak; losses=0
        for trade in closed:
            value=Decimal(trade['net_pnl']); walking+=value; peak=max(peak,walking)
            losses=losses+1 if value<0 else 0
        context=RiskContext('HEALTHY',True,'KNOWN',True,'FLAT',True,'KNOWN',True,False,True,
            runtime['entry_days'].get(now.date().isoformat(),0),0,False,losses,peak-equity,equity)
        proposal=RiskProposal(quantity,notional,notional/leverage,leverage,
            quantity*abs(reference-constraints.stop_level),Decimal(self.config['estimated_roundtrip_cost_usdt']),
            quantity*abs(constraints.target_level-reference) if constraints.target_level is not None else Decimal('0'),
            constraints.stop_level,constraints.target_level)
        risk=evaluate_trade_intent(intent,context,proposal,self.service.risk.risk_policy,decided_at=now)
        runtime['risk_decision']=risk; self._effect(effects,'RISK_DECISION',risk)
        if risk['decision']!='APPROVE': return 'BLOCKED',tuple(risk['reason_codes'])
        plan=build_approved_trade_plan(intent,risk,self.service.risk.risk_policy,created_at=now)
        request=ExecutionGateway().prepare_entry_order(plan,now=now); ack=broker.submit_order(request)
        runtime.update(plan=plan,position=None,entry_request=encode_fact(request),protection_request=None,
            protection_action=None,exit_request=None,exit_action=None,exit_source_position=None,
            strategy_exit_request=exits.as_dict(),exit_anchor=None)
        self._effect(effects,'APPROVED_TRADE_PLAN',plan)
        self._effect(effects,'ORDER_REQUEST',encode_fact(request)); self._effect(effects,'ORDER_RESULT',encode_fact(ack))
        if ack.order_status in (OrderStatus.UNKNOWN,OrderStatus.RECONCILIATION_REQUIRED):
            self.reconciled=False
            return 'BLOCKED',('ENTRY_SUBMIT_RECONCILIATION_REQUIRED',)
        if ack.order_status==OrderStatus.REJECTED: return 'BLOCKED',('ENTRY_SUBMIT_REJECTED',)
        return 'ACKNOWLEDGED',()

    def produce(self, state, request, now):
        if self.recovery_reason is not None:
            return PaperStep(state,[],'BLOCKED',(self.recovery_reason,))
        broker=PaperBroker.from_state(state['broker']); runtime=state['runtime']; effects=[]
        kind=request['kind']; market=_market(runtime['last_market']) if runtime['last_market'] else None
        if kind=='MARKET':
            market=_market(request['snapshot'])
            runtime['last_market']=request['snapshot']
            for payload in request['candles']:
                row=_candle(payload)
                if row.symbol!=self.strategy.symbol or row.timeframe not in self.strategy.required_timeframes:
                    raise ValueError('Paper candle subject/timeframe mismatch')
                if not row.is_closed or row.close_time>now or row.received_at is None or row.received_at>now:
                    raise ValueError('Unfinalized/future Paper candle cannot enter runtime')
                frame=runtime['candles'].setdefault(row.timeframe,[])
                existing=next((value for value in frame if value['open_time']==payload['open_time']),None)
                if existing is not None and existing!=payload: raise ValueError('Changed finalized candle identity')
                if existing is None:
                    if frame and utc(payload['open_time'])<utc(frame[-1]['open_time']): raise ValueError('Out-of-order Paper candle')
                    frame.append(payload)
                    del frame[:-self.config['maximum_cached_candles_per_timeframe']]
            runtime['market_status']='FRESH' if self._fresh(market,now) else 'STALE'
        elif kind=='PAUSE': runtime['paper_entries_allowed']=False
        elif kind!='DEADLINE': raise ValueError('Unsupported Paper scheduler operation')
        entry_outcome=self._fill_entry(runtime,broker,effects,market,now)
        managed=self._manage(runtime,broker,effects,market,now)
        if managed is not None: status,reasons=managed
        elif entry_outcome is not None: status,reasons=entry_outcome
        elif not self._fresh(market,now): status,reasons='BLOCKED',('MARKET_STALE' if market else 'MARKET_NOT_CONNECTED',)
        elif kind=='PAUSE': status,reasons='PAUSED',()
        elif kind=='MARKET': status,reasons=self._evaluate(runtime,broker,effects,market,now)
        else: status,reasons='HOLD',()
        position=runtime['position']
        healthy=self._fresh(market,now) and self.reconciled and (position is None or position['lifecycle_state'] in ('OPEN_PROTECTED','PROFIT_PROTECTED','CLOSED'))
        record_forward_observation(runtime,self.service,now,healthy)
        return PaperStep(dict(broker=broker.export_state(),runtime=runtime),effects,status,reasons)
