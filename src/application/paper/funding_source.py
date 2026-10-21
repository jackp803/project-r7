"""Trusted cached E4 source port; no network, database or caller PASS input."""
from execution.public_recorded_funding import PublicRecordedFundingModel
import re


class PaperFundingSource:
    def __init__(self,model,reader,*,status_reader=None):
        if (type(model) is not PublicRecordedFundingModel or not callable(reader)
                or status_reader is not None and not callable(status_reader)):
            raise ValueError('Actual E4 source and trusted owner observation reader required')
        self.model,self.reader=model,reader
        self.status_reader=status_reader

    def current(self,now):
        try:
            observed=self.reader()
            return observed if self.model.health(observed,now=now) else None
        except (ValueError,TypeError,RuntimeError,OSError):return None

    def status(self,now):
        observed=self.current(now)
        value=dict(status='UNAVAILABLE',reason_code='PUBLIC_FUNDING_SOURCE_UNAVAILABLE',
            observed_at=None,coverage_start=None,complete_through=None,snapshot_hash=None)
        if observed is not None:
            return dict(status='HEALTHY',reason_code=None,observed_at=observed.observed_at,
                coverage_start=observed.coverage_start,complete_through=observed.complete_through,
                snapshot_hash=observed.snapshot_hash)
        if self.status_reader is not None:
            try:
                actual=self.status_reader();reason=actual.get('reason_code')
                if type(reason) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,127}',reason):value['reason_code']=reason
                from application.datasets.catalog import utc
                if all(actual.get(key) is not None for key in ('observed_at','coverage_start','complete_through','snapshot_hash')):
                    for key in ('observed_at','coverage_start','complete_through'):utc(actual[key])
                    if type(actual['snapshot_hash']) is str and re.fullmatch('[0-9a-f]{64}',actual['snapshot_hash']):
                        value.update({key:actual[key] for key in ('observed_at','coverage_start','complete_through','snapshot_hash')})
            except (ValueError,TypeError,KeyError,RuntimeError,OSError):pass
        return value


def funding_status(runtime,*,now):
    """Allowlisted last-known owner facts; never an entry permission or PnL."""
    from datetime import datetime
    pending=runtime.get('pending_funding');finalized=runtime.get('funding_finalizations',[])
    flat=None
    if pending is not None:
        flat={key:pending['flat'][key] for key in ('position_id','symbol','actual_quantity','broker_state_observed_at')}
    since=None if pending is None else pending['started_at']
    impact=runtime.get('funding_opportunities',{})
    opportunities={key:impact.get(key,0) for key in ('evaluated_boundaries','valid_blocked','non_directional',
        'other_gate_blocked','unresolved_financial','stale_or_invalid')}
    opportunities['last_boundary']=impact.get('last_boundary')
    return dict(funding_model='OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1',source_kind='PAPER_MODEL',
        cost_basis='ACTUAL_ENTRY_FILL_NOTIONAL',billing_disclosure='PAPER_MODEL_NOT_EXCHANGE_ACCOUNT_BILL',
        status='FUNDING_PENDING' if pending else 'FINALIZED' if finalized else 'NO_FINANCIAL_SAMPLE',
        pending_allocations=1 if pending else 0,finalized_allocations=len(finalized),pending_since=since,
        wall_wait_seconds=0 if since is None else max(0,int((now-datetime.fromisoformat(since.replace('Z','+00:00'))).total_seconds())),
        observed_wait_seconds=0 if pending is None else pending['observed_wait_ns']//1_000_000_000,
        wait_reason=None if pending is None else pending['reason'],flat_observation=flat,
        opportunities=opportunities,
        latest_source=runtime.get('funding_source_observation',dict(status='UNAVAILABLE',reason_code='PUBLIC_FUNDING_SOURCE_UNAVAILABLE',
            observed_at=None,coverage_start=None,complete_through=None,snapshot_hash=None)))
