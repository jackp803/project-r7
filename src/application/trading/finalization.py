"""Original single-close FIXTURE finalization; no provider effects or new math."""
import json

from application.trading.funding_owner import _fixture
from application.trading.close_owner import original_entry
from application.trading.terminal_stop import require_terminal_stop_read
from application.trading.position_observation import require_position_read
from application.trading.algo_inventory import require_algo_inventory
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from brokers.okx_product_state import restore_product_readback
from storage.product_position import observation_material,inventory_material
from storage.product_finalization import (ProductFinalizationObservation,claim_snapshot,original_refs,require_distinct_journals)
from storage.product_finalization_facts import PROFILE,build_effects,recover_snapshot,require_prefix,fail


def finalize_fixture_trade(service,operation_id,target,native,inventory,*,metadata,proof,expected_revision):
    _fixture(service);require_distinct_journals(service.dispatch,service.canonical)
    saved=service.dispatch.finalization_batch(service.run_id,operation_id)
    if saved is not None:
        # Repeating an original receipt/recovering a committed batch is history,
        # not a new interpretation or renewal of expired native source objects.
        receipt=service.dispatch.finalization_receipt(saved)
        if receipt is None:
            service.recover_publications();receipt=service.dispatch.finalization_receipt(saved)
        if (receipt is None or build_effects(saved.source)!=saved.effects or
                require_prefix(saved.source,saved.effects,recover_snapshot(service.canonical,saved.source))!=3):
            fail('FINALIZATION_ORIGINAL_COMPLETE_RECEIPT_REQUIRED')
        return receipt
    service._guard(expected_revision,'MANAGE_EXISTING')
    def current_reads():
        require_terminal_stop_read(service,target,target.operation_id)
        require_position_read(service,native,metadata=metadata,proof=proof,expected_revision=expected_revision)
        require_algo_inventory(service,inventory,metadata=metadata,proof=proof,expected_revision=expected_revision)
    current_reads()
    operation=service.dispatch.operation(service.run_id,operation_id)
    if operation is None:fail('FINALIZATION_ORIGINAL_CLOSE_REQUIRED')
    prepared=restore_product_readback(operation.request);request=prepared.canonical_request
    if operation_id!=target.close_operation_id:fail('FINALIZATION_EXACT_TERMINAL_CLOSE_BINDING_REQUIRED')
    entry,_,_,_=original_entry(service,request.trade_plan_id)
    flat=service.dispatch.latest_position_publication(service.run_id,operation_id)
    if flat is None:fail('FINALIZATION_ORIGINAL_NATIVE_FLAT_REQUIRED')
    raw=[effect['payload'] for effect in flat.effects if effect['kind']=='RAW_POSITION']
    if len(raw)!=1:fail('FINALIZATION_ONE_ORIGINAL_RAW_FLAT_REQUIRED')
    stamp=lambda value:value.isoformat().replace('+00:00','Z')
    source=dict(profile=PROFILE,run_id=service.run_id,trade_plan_id=request.trade_plan_id,position_id=request.position_id,
        entry_operation_id=entry.operation_id,stop_operation_id=target.operation_id,close_operation_id=operation_id,
        interpreted_at=stamp(service.clock()),raw_flat=raw[0],metadata_hash=canonical_okx_close_sizing_hash(metadata),
        metadata_observed_at=stamp(metadata.observed_at),native_confirmation=observation_material(native),
        inventory_confirmation=inventory_material(inventory),terminal_confirmation=dict(
            row=json.loads(target.observation.row_json),source_hash=target.observation.source_hash,
            request_started_at=stamp(target.request_started_at),received_at=stamp(target.observation.received_at)))
    source['baseline']=recover_snapshot(service.canonical,source)
    source['original_refs']=original_refs(service.dispatch,source)
    source['claim_snapshot']=claim_snapshot(service.dispatch,service.run_id)
    effects=build_effects(source)
    # All expensive interpretation is complete before final issuer/window
    # checks and the existing E6 idle-writer transaction. No source time renews.
    current_reads()
    from storage.product_dispatch import _json
    generation=service.dispatch.claim_inventory_generation()
    observation=ProductFinalizationObservation(_json(source),_json(effects))
    service.dispatch.stage_finalization(service.canonical,service.run_id,operation_id,observation,
        lease=service.lease,clock=service.clock,claim_inventory_generation=generation)
    service.recover_publications()
    saved=service.dispatch.finalization_batch(service.run_id,operation_id)
    receipt=service.dispatch.finalization_receipt(saved)
    if receipt is None:fail('FINALIZATION_CANONICAL_PUBLICATION_INCOMPLETE')
    return receipt
