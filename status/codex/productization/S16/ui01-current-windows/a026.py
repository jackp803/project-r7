"""Actual authenticated unconfigured API projections; supplemental RED only.

Normal existing fixture owns setup/auth/cleanup. No private-provider access,
accepted-answer patching, direct financial writes or qualification membership.
"""
from datetime import timedelta
import unittest
from tests.product.test_api_authority import APIFixture


class UI01ObservationContractTests(APIFixture,unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def observed(self,route):
        response=self.client.get('/api/v1/'+route)
        self.assertEqual(200,response.status_code)
        return response.json()

    def test_overview_exposes_subject_stage_resource_and_alert_observations_without_selecting_newest_strategy(self):
        body=self.observed('overview')['data']
        for key in ('strategy_subjects','research_stage_counts','resource_limits','alerts'):
            with self.subTest(field=key):
                self.assertIn(key,body,'Required Overview fact has no actual projection')

    def test_health_distinguishes_component_observation_times_from_unobserved_risk_execution_preflight_and_fp(self):
        body=self.observed('health')['data']
        self.assertFalse(body['live_authorized'])
        for key in ('components','risk','execution','preflight','external_consumer'):
            with self.subTest(field=key):
                self.assertIn(key,body,'Required Health observation is absent')
                if key!='components':
                    self.assertEqual('UNAVAILABLE',body[key]['status'])
                    self.assertIsNone(body[key]['as_of'])

    def test_settings_reports_configured_budget_and_unobserved_clock_backup_transport_and_credential_presence(self):
        body=self.observed('settings')['data']
        for key in ('resource_limits','clock_health','backup','transport_test','credential_presence'):
            with self.subTest(field=key):
                self.assertIn(key,body,'Required Settings observation is absent')
        if 'credential_presence' in body:
            self.assertEqual('UNAVAILABLE',body['credential_presence']['status'])
            self.assertIsNone(body['credential_presence']['as_of'])
        if 'backup' in body:self.assertEqual('NOT_CONFIGURED',body['backup']['status'])
        if 'transport_test' in body:self.assertEqual('NOT_RUN',body['transport_test']['status'])

    def test_observation_time_advances_without_changing_stored_configuration_commitment(self):
        first=self.observed('settings')
        self.clock[0]+=timedelta(seconds=1)
        second=self.observed('settings')
        self.assertNotEqual(first['metadata']['observed_at'],second['metadata']['observed_at'])
        self.assertEqual(first['metadata']['config_hash'],second['metadata']['config_hash'])
        self.assertEqual(first['data']['revision'],second['data']['revision'])
        self.assertEqual(first['data']['config_generation'],second['data']['config_generation'])
