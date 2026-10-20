"""Field names only, no canonical/account/provider payload diagnostics."""
from dataclasses import fields
from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[2]/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
def trace(frame,event,arg):
    if (event=='exception' and frame.f_code.co_filename.replace('\\','/').endswith('/application/trading/funding_owner.py')
            and frame.f_code.co_name=='publish_fixture_funding_ledger' and 'before' in frame.f_locals and 'current' in frame.f_locals):
        before=frame.f_locals['before'];current=frame.f_locals['current']
        changed=[f.name for f in fields(before) if getattr(before,f.name)!=getattr(current,f.name)]
        nested=[f.name for f in fields(before.recovered) if getattr(before.recovered,f.name)!=getattr(current.recovered,f.name)]
        print(json.dumps(dict(context_changed_fields=changed,recovery_changed_fields=nested)),flush=True)
    return trace
sys.settrace(trace)
suite=unittest.defaultTestLoader.loadTestsFromName('tests.product.test_trading_funding_v02.TradingFundingV02Tests.test_actual_partial_is_refused_then_flat_paginated_ledger_publishes_without_closing')
result=unittest.TextTestRunner(verbosity=1).run(suite)
sys.settrace(None)
raise SystemExit(0 if result.wasSuccessful() else 1)
