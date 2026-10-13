"""Receipt admission boundary with retained local artifacts; synthetic unit subjects."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from storage import open_sqlite_platform
from storage.qualification import QualificationSubject,QualificationCheck,_open_qualification_receipt_owner


class PaperQualificationProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='r7-pqr-boundary-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'canonical.sqlite3'
        with open_sqlite_platform(self.path,research_namespace='LOCAL_RESEARCH'):pass
        self.measured=dict(executable_revision='1'*40,implementation_hash='sha256:'+'2'*64,
            build_hash='sha256:'+'3'*64,platform_id='windows-11-x86_64',capability_hash='sha256:'+'4'*64)
        self.profile=dict(schema_version='r7-qualified-paper-inventory-v0.2',
            profile_id='r7-qualified-paper-release-v0.2',decision_ref='PM_PAPER_RELEASE_MAPPING_DECISION_20261013',
            decision_hash='sha256:'+'5'*64,platform_id=self.measured['platform_id'],
            capability_hash=self.measured['capability_hash'],groups=[])
        self.evidence=dict(schema_version='r7-qualified-paper-execution-evidence-v0.2',
            provenance='FIXTURE_SOFTWARE_CHECKS_ONLY',members=[])
        self.checks=[]
        for number in range(1,8):
            group=f'PQR-{number:02d}';member=f'{group}-unit-boundary'
            raw=f'retained synthetic unit log {number}\n'.encode();ref=f'{number:02d}.log'
            (self.root/ref).write_bytes(raw);h='sha256:'+hashlib.sha256(raw).hexdigest()
            self.profile['groups'].append(dict(check_id=group,members=[dict(member_id=member,kind='UNITTEST',
                command_ref='fixed-unit-command',tool_hash='sha256:'+'6'*64,
                test_cases=['synthetic_boundary.Test.case'],assertions=[],target_predicate='ALL')]))
            self.checks.append(QualificationCheck(member,'fixed-unit-command',ref,h,0,True,1,0,0,0,0,0,1))
            self.evidence['members'].append(dict(member_id=member,group_id=group,
                test_cases=['synthetic_boundary.Test.case'],artifacts=[dict(ref=ref,hash=h)],assertions=[]))

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.paper.qualification'),
            'Fixed inventory validation cannot be replaced with generic receipt.passed')
        return importlib.import_module('application.paper.qualification')

    def receipt(self,**changes):
        fields=dict(execution_id='synthetic-boundary',subject=QualificationSubject(namespace='LOCAL_RESEARCH',
            **{key:self.measured[key] for key in ('executable_revision','implementation_hash','build_hash','platform_id')}),
            profile_id=self.profile['profile_id'],profile_hash='sha256:'+hashlib.sha256(
                json.dumps(self.profile,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            checks=tuple(self.checks),profile_manifest=self.profile,execution_evidence=self.evidence,
            started_at=datetime(2026,10,13,tzinfo=timezone.utc),finished_at=datetime(2026,10,13,tzinfo=timezone.utc)+timedelta(seconds=1))
        fields.update(changes)
        with _open_qualification_receipt_owner(self.path,namespace='LOCAL_RESEARCH') as owner:
            return owner._append(**fields)

    def validate(self,m,receipt):
        return m.validate_qualified_receipt(receipt,self.profile,artifact_root=self.root,measured=self.measured)

    def test_exact_ordered_complete_retained_subject_is_software_eligible_only(self):
        m=self.module();receipt=self.receipt();self.validate(m,receipt)
        self.assertEqual(receipt.scope,'SOFTWARE_CHECK_EXECUTION_ONLY')

    def test_missing_reordered_zero_skipped_or_unreaped_member_denies(self):
        m=self.module()
        from dataclasses import replace
        for index,changes in enumerate(({'checks':tuple(self.checks[:-1])},{'checks':tuple(reversed(self.checks))},
                {'checks':(replace(self.checks[0],tests_run=0),*self.checks[1:])},
                {'checks':(replace(self.checks[0],skipped=1),*self.checks[1:])},
                {'checks':(replace(self.checks[0],tree_reaped=False),*self.checks[1:])})):
            with self.subTest(index=index),self.assertRaises(ValueError):
                self.validate(m,self.receipt(execution_id=f'negative-{index}',**changes))

    def test_modified_artifact_missing_test_and_wrong_subject_denies(self):
        m=self.module();receipt=self.receipt()
        for key in ('executable_revision','implementation_hash','build_hash','platform_id','capability_hash'):
            original=self.measured[key];self.measured[key]='mismatched'
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(m,receipt)
            self.measured[key]=original
        (self.root/'01.log').write_bytes(b'mutated')
        with self.assertRaises(ValueError):self.validate(m,receipt)

    def test_generic_legacy_pass_and_caller_assertion_are_not_inventory_completeness(self):
        m=self.module()
        legacy=self.receipt(profile_manifest=None,execution_evidence=None)
        self.assertTrue(legacy.passed)
        with self.assertRaises(ValueError):self.validate(m,legacy)
        evidence=deepcopy(self.evidence);evidence['members'][0]['test_cases']=[]
        with self.assertRaises(ValueError):
            self.validate(m,self.receipt(execution_id='missing-case',execution_evidence=evidence))

    def test_zero_test_artifact_command_needs_all_fixed_assertions_and_actual_bytes(self):
        m=self.module()
        from dataclasses import replace
        member=self.profile['groups'][1]['members'][0]
        member.update(kind='NATIVE_ASSERTIONS',test_cases=[],assertions=['measured-native-identity'])
        self.checks[1]=replace(self.checks[1],tests_run=0)
        result=self.evidence['members'][1];result['test_cases']=[]
        with self.assertRaises(ValueError):self.validate(m,self.receipt(execution_id='missing-native-assertion'))
        result['assertions']=[dict(assertion_id='measured-native-identity',status='PASS',evidence_ref='02.log',
            evidence_hash=self.checks[1].log_hash)]
        self.validate(m,self.receipt(execution_id='synthetic-native-assertion'))


if __name__=='__main__':unittest.main()
