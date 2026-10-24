"""Read-only browser QA on actual LOCAL owners and explicitly controlled inputs.

Synthetic clock/source/native boundary; not ordinary/native/forward acceptance.
Fresh test-only authentication, no provider, production profile or credentials.
"""
import argparse
from dataclasses import replace
from datetime import timedelta
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]

from application.control_api.app import create_app
from application.control_api.assets import mount_control_center
from application.control_api.auth import LocalAuth
from application.control_api.commands import CommandLedger
from tests.product.test_paper_recorded_funding import PaperRecordedFundingTests,floor
from tests.product.test_paper_encoded_checkpoint_consumers import EncodedRecordedFundingRegressionTests,encoded_create
from storage.paper_process import PaperProcessJournal
from unittest.mock import patch
import uvicorn


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=('pending','finalized','history-pending'),required=True)
    parser.add_argument('--port',type=int,required=True);args=parser.parse_args()
    scratch=Path(os.environ['R7_BROWSER_SCRATCH_ROOT'])/args.profile
    scratch.mkdir(parents=True,exist_ok=True);tempfile.tempdir=str(scratch)
    fixture=PaperRecordedFundingTests() if args.profile=='history-pending' else EncodedRecordedFundingRegressionTests()
    try:
        if args.profile=='history-pending':
            with patch.object(PaperProcessJournal,'create_run',new=encoded_create(PaperProcessJournal.create_run)):
                fixture.prepare(instance_id='recorded-browser-'+args.profile)
            outcome=fixture.runtime.on_market_event(fixture.event(0,bars=True))
            if outcome.status!='BLOCKED' or 'HISTORY_AUDIT_REQUIRED' not in outcome.reason_codes:
                raise RuntimeError('Actual unaudited owner must refuse entry')
        else:fixture.close_pending(instance_id='recorded-browser-'+args.profile)
        if args.profile=='finalized':
            fixture.clock[0]=floor(fixture.initial)+timedelta(hours=8,seconds=2)
            fixture.observe(fixture.clock[0])
            outcome=fixture.runtime.on_deadline(fixture.clock[0])
            if outcome.status!='CLOSED':raise RuntimeError('Actual E4/E5/E6 finalization required')
        owners=fixture.local.control_services()
        config=replace(fixture.config,control_api_port=args.port);owners.config=config
        auth=LocalAuth(config.local_data_root/'browser-auth.sqlite',namespace='LOCAL_RESEARCH',clock=lambda:fixture.clock[0])
        auth.create_owner('local-owner','explicit-test-only-password-123')
        commands=CommandLedger(config.local_data_root/'browser-commands.sqlite',namespace='LOCAL_RESEARCH',clock=auth.clock)
        app=create_app(config,auth=auth,commands=commands,services=owners)
        mount_control_center(app,ROOT/'ui/dist')
        uvicorn.run(app,host='127.0.0.1',port=args.port,proxy_headers=False,access_log=False,log_level='warning')
    finally:fixture.doCleanups()


if __name__=='__main__':main()
