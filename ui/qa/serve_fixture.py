"""Explicit local browser fixture server; no remote provider or real authority."""
import argparse
from dataclasses import replace
from datetime import timedelta
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.control_api.app import create_app
from application.control_api.assets import mount_control_center
from tests.product.test_api_authority import APIFixture
from tests.product.test_api_owner_services import APIOwnerServicesTests
from tests.product.test_api_paper_services import APIPaperServicesTests
from application.control_api.owner_services import OwnerControlServices
from storage.platform import open_sqlite_platform
import unittest
import uvicorn

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--profile',choices=['empty','research','paper','protected','temporal','approval'],required=True)
    parser.add_argument('--port',type=int,required=True); args=parser.parse_args()
    scratch=ROOT.parent.parent/'artifacts/S11-browser'/args.profile; scratch.mkdir(parents=True,exist_ok=True)
    tempfile.tempdir=str(scratch)
    if args.profile=='empty':
        class Empty(APIFixture,unittest.TestCase): pass
        fixture=Empty(); fixture.setUp(); owners=None
    elif args.profile=='approval':
        from tests.product.test_api_approval_preview import APIApprovalPreviewTests
        fixture=APIApprovalPreviewTests(methodName='runTest');fixture.setUp();owners=fixture.app.state.owners
    elif args.profile in ('research','temporal'):
        fixture=APIOwnerServicesTests(); fixture.setUp(); owners=fixture.owners
        if args.profile=='temporal':
            from tests.strategy.v02_fixtures import definition_v02
            from tests.application.cloud_fixtures import package
            from tests.application.dataset_fixtures import encoded
            from strategy import compute_content_hash
            from strategy.v02.capabilities import build_capability_snapshot
            value=definition_v02(); value['strategy_id']='fixture-v02-4h-tactical'
            value['rules']['exit_policy']['max_hold_seconds']=7200; value['content_hash']=compute_content_hash(value)
            folder,manifest,_=package(fixture.cloud,submission='fixture-temporal',version='0.2',definition=value)
            manifest.update(capability_snapshot_hash=build_capability_snapshot().snapshot_hash,research_hypothesis='明確的四小時策略測試',
                intent_class='TACTICAL_STRATEGY',validity={'from':fixture.clock[0].isoformat().replace('+00:00','Z'),
                    'until':(fixture.clock[0]+timedelta(hours=4)).isoformat().replace('+00:00','Z')})
            (folder/'manifest.json').write_bytes(encoded(manifest))
    else:
        fixture=APIPaperServicesTests(); fixture.setUp()
        if args.profile=='protected':
            _,_,run_id=fixture.api_start(); runtime=fixture.h.service.runtime(run_id)
            runtime.on_market_event(fixture.h.event(0,bars=True)); runtime.on_market_event(fixture.h.event(1))
        owners=OwnerControlServices(fixture.config,namespace='FIXTURE',clock=lambda:fixture.h.clock[0],
            registry_factory=lambda:open_sqlite_platform(fixture.path,research_namespace='FIXTURE'),
            paper_reader=fixture.reader,paper_start=fixture.start_port)
    fixture.client.close()
    config=replace(fixture.config,control_api_port=args.port)
    if owners is not None: owners.config=config
    # Always construct a new app with the actual same-origin port; no disabled
    # security middleware, mocked response or financial approval override.
    from application.control_api.commands import CommandLedger
    commands=CommandLedger(config.local_data_root/'browser-commands.sqlite',namespace='FIXTURE',clock=fixture.auth.clock)
    app=create_app(config,auth=fixture.auth,commands=commands,services=owners)
    if (ROOT/'ui/dist/index.html').exists(): mount_control_center(app,ROOT/'ui/dist')
    try: uvicorn.run(app,host='127.0.0.1',port=args.port,proxy_headers=False,access_log=False,log_level='warning')
    finally: fixture.doCleanups()

if __name__=='__main__': main()
