"""Actual authenticated owner path; completed replay is history after expiry."""
import unittest
from fastapi.testclient import TestClient
from application.config import load_config
from application.control_api.app import create_app
from application.control_api.auth import LocalAuth
from application.control_api.commands import CommandLedger
from tests.application import test_submission_validity_research as validity


class ExpiredResearchAPIReplayTests(unittest.TestCase):
    def test_same_completed_command_replays_after_expiry_without_new_owner_work(self):
        helper=validity.SubmissionValidityResearchTests();helper.setUp();self.addCleanup(helper.doCleanups)
        local=helper.selected();config=load_config(helper.config_path)
        auth=LocalAuth(config.local_data_root/'replay-auth.sqlite',namespace='FIXTURE',clock=lambda:helper.clock[0])
        auth.create_owner('explicit-fixture-replay-owner','synthetic-replay-test-only-password')
        commands=CommandLedger(config.local_data_root/'replay-commands.sqlite',namespace='FIXTURE',clock=lambda:helper.clock[0])
        app=create_app(config,auth=auth,commands=commands,services=local.control_services())
        origin=f'http://127.0.0.1:{config.control_api_port}'
        with TestClient(app,base_url=origin,client=('127.0.0.1',42000),raise_server_exceptions=False) as client:
            login=client.post('/api/v1/auth/login',json=dict(username='explicit-fixture-replay-owner',
                password='synthetic-replay-test-only-password',command_id='replay-test-login',expected_revision=0),headers={'Origin':origin})
            self.assertEqual(login.status_code,200,login.text)
            headers={'Origin':origin,'X-R7-CSRF':login.json()['csrf_token']}
            body=dict(command_id='accepted-replay',expected_revision=helper.submission_revision,
                      submission_id=helper.submission,policy_id=helper.policy)
            first=client.post('/api/v1/research/runs',json=body,headers=headers)
            self.assertEqual(first.status_code,202,first.text)
            helper.clock[0]=validity.UNTIL
            claim=local.queue.claim_next();expired=local.queue.step(claim.run_id,claim.generation)
            self.assertEqual(expired['state'],'EXPIRED')
            before=local.queue.list()
            replay=client.post('/api/v1/research/runs',json=body,headers=headers)
            self.assertEqual(replay.status_code,202,replay.text)
            self.assertEqual(replay.json(),first.json())
            for changed in ({**body,'policy_id':'changed-policy'},{**body,'expected_revision':body['expected_revision']+1}):
                conflict=client.post('/api/v1/research/runs',json=changed,headers=headers)
                self.assertEqual(conflict.status_code,409,conflict.text)
            denied=client.post('/api/v1/research/runs',json={**body,'command_id':'new-expired-work'},headers=headers)
            self.assertNotEqual(denied.status_code,202)
            self.assertEqual(local.queue.list(),before)
            helper.retained(local,'DRAFT')


if __name__=='__main__':unittest.main()
