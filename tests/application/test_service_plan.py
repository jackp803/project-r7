"""Portable service rendering; no claim of Ubuntu/systemd execution."""
from dataclasses import replace
import importlib
import unittest

class ServicePlanTests(unittest.TestCase):
    def module(self):
        return importlib.import_module('application.platform.service_plan')

    def settings(self, **changes):
        subject=self.module().ServiceSettings(
            binary_root='/opt/R7 中文/releases/v0.2', config_path='/etc/r7/settings/product.json',
            data_root='/var/lib/r7-data', cloud_root='/srv/r7-staging', service_user='r7-worker',
            executable_revision='a'*40, build_hash='sha256:'+'b'*64, config_hash='sha256:'+'c'*64,
            physical_memory_bytes=24*1024**3)
        return replace(subject,**changes)

    def test_two_existing_roles_are_isolated_and_missing_runtime_is_explicit(self):
        plan=self.module().render_service_plan(self.settings())
        self.assertEqual(plan['status'],'RENDERED_ONLY')
        self.assertEqual(set(plan['units']),{'r7-control.service','r7-research.service'})
        self.assertEqual(plan['runtime'],'NOT_DELIVERED_CONTINUOUS_COMPOSITION_REQUIRED')
        self.assertEqual(plan['native_service_acceptance'],'NOT_RUN')
        self.assertEqual(plan['financial_authority'],'NONE')

    def test_actual_existing_cli_roles_are_bound_to_exact_build_and_configuration(self):
        plan=self.module().render_service_plan(self.settings())
        for role in ('control','research'):
            unit=plan['units'][f'r7-{role}.service']
            self.assertIn('guarded-service',unit)
            for flag,value in (('--role',role),('--expected-revision','a'*40),('--expected-build-hash','sha256:'+'b'*64),('--expected-config-hash','sha256:'+'c'*64)):
                self.assertIn(f'"{flag}" "{value}"',unit)
            self.assertNotIn('/bin/sh',unit)
            self.assertNotIn('ExecStartPre=',unit)

    def test_research_uses_measured_budget_one_cpu_and_owned_group_shutdown(self):
        plan=self.module().render_service_plan(self.settings())
        research=plan['units']['r7-research.service']; control=plan['units']['r7-control.service']
        maximum=8*1024**3
        self.assertIn(f'MemoryMax={maximum}',research)
        self.assertIn(f'MemoryHigh={maximum*9//10}',research)
        self.assertIn('CPUQuota=100%',research)
        self.assertIn('Nice=10',research)
        self.assertNotIn('CPUQuota=',control)
        for unit in plan['units'].values():
            for expected in ('KillMode=control-group','TimeoutStopSec=30','Restart=on-failure','RestartSec=5','StartLimitIntervalSec=120','StartLimitBurst=3','NoNewPrivileges=yes','ProtectSystem=strict','UMask=0077','User=r7-worker','CapabilityBoundingSet='):
                self.assertIn(expected,unit)

    def test_config_and_binary_are_read_only_with_only_explicit_writable_roots(self):
        plan=self.module().render_service_plan(self.settings())
        for unit in plan['units'].values():
            line=next(row for row in unit.splitlines() if row.startswith('ReadWritePaths='))
            self.assertEqual(line,'ReadWritePaths="/var/lib/r7-data" "/srv/r7-staging" "/run/r7/scopes"')
            self.assertNotIn('/etc/',line)
            self.assertNotIn('/opt/',line)
        self.assertEqual(plan['mutations'],[])

    def test_absent_cloud_has_no_invented_writable_staging_root(self):
        plan=self.module().render_service_plan(self.settings(cloud_root=None))
        self.assertIn('ReadWritePaths="/var/lib/r7-data" "/run/r7/scopes"\n',plan['units']['r7-control.service'])
        self.assertEqual(plan['writable_roots'],['/var/lib/r7-data','/run/r7/scopes'])

    def test_literal_percent_dollar_quotes_and_chinese_paths_cannot_expand_directives(self):
        value='/opt/R7 中文 $HOME %n "quoted"/release'
        plan=self.module().render_service_plan(self.settings(binary_root=value))
        unit=plan['units']['r7-control.service']
        self.assertIn('ExecStart=:"/opt/R7 中文 $HOME %%n \\"quoted\\"/release/r7"',unit)
        self.assertEqual(sum(row.startswith('ExecStart=') for row in unit.splitlines()),1)

    def test_noncanonical_paths_directive_injection_and_hidden_home_roots_are_denied(self):
        for value in ('relative','/','/opt/../etc/r7','//host/share','/opt/r7/','/opt/r7\nUser=root','/opt/r7\\windows','/home/r7/release','/root/release','/run/user/1000/r7'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.module().render_service_plan(self.settings(binary_root=value))

    def test_equal_nested_or_parent_roots_are_denied(self):
        for changes in ({'data_root':'/opt/R7 中文/releases/v0.2/data'}, {'binary_root':'/var/lib'},
                        {'cloud_root':'/var/lib/r7-data'}, {'cloud_root':'/var/lib/r7-data/staging'},
                        {'config_path':'/var/lib/r7-data/product.json'}, {'config_path':'/opt/R7 中文/releases/v0.2/product.json'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.module().render_service_plan(self.settings(**changes))

    def test_unknown_and_unsupported_runtime_roles_are_denied(self):
        for roles in (('runtime',),('control','runtime'),('control','control'),(),('cloud',)):
            with self.subTest(roles=roles),self.assertRaises(ValueError):
                self.module().render_service_plan(self.settings(),roles=roles)

    def test_privileged_or_injected_identity_is_denied(self):
        for user in ('root','nobody','r7\nUser=root','r7 worker','r7-worker;evil','-r7','r7'+'x'*40):
            with self.subTest(user=user),self.assertRaises(ValueError):
                self.module().render_service_plan(self.settings(service_user=user))

    def test_bad_commitments_and_unmeasured_memory_are_denied(self):
        for changes in ({'executable_revision':'main'},{'build_hash':'caller-pass'},{'config_hash':'sha256:'+'z'*64},
                        {'physical_memory_bytes':True},{'physical_memory_bytes':0},{'physical_memory_bytes':1024**3}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.module().render_service_plan(self.settings(**changes))

    def test_plan_identity_changes_with_config_build_and_root_without_financial_claim(self):
        render=self.module().render_service_plan
        original=render(self.settings())
        for changes in ({'config_hash':'sha256:'+'d'*64},{'build_hash':'sha256:'+'e'*64},{'data_root':'/var/lib/r7-other'}):
            altered=render(self.settings(**changes))
            self.assertNotEqual(original['plan_hash'],altered['plan_hash'])
            self.assertEqual(altered['financial_authority'],'NONE')

    def test_actual_shared_scope_root_is_explicitly_writable_and_never_removed_on_unit_stop(self):
        plan=self.module().render_service_plan(self.settings())
        for unit in plan['units'].values():
            writable=next(row for row in unit.splitlines() if row.startswith('ReadWritePaths='))
            self.assertIn('"/run/r7/scopes"',writable)
            self.assertNotIn('RuntimeDirectory=',unit)
            self.assertNotIn('ExecStopPost=',unit)
        self.assertEqual(plan['scope_lock_provisioning']['rule'],'d /run/r7/scopes 0700 r7-worker r7-worker -')
        self.assertEqual(plan['scope_lock_provisioning']['existing_owner_mismatch'],'REFUSE_BEFORE_INSTALLATION')

if __name__=='__main__':unittest.main()
