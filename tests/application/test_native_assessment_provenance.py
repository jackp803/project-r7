import importlib
import sys
import unittest
from unittest.mock import patch

from registry import EvidenceGateError
from application.research.evidence import capture_provenance
from tests.application import test_native_distribution as fixtures


class NativeAssessmentProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.NativeDistributionTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.seal()

    def require(self, provenance):
        module = importlib.import_module('application.research.product_assessment')
        module.require_promotable_provenance(provenance)

    def native_context(self):
        return (patch.object(sys, 'frozen', True, create=True),
                patch.object(sys, '_MEIPASS', str(self.fixture.root / '_internal'), create=True),
                patch.object(sys, 'executable', str(self.fixture.root / 'R7.exe')))

    def test_actual_sealed_frozen_identity_is_accepted_without_relabelling_git_clean(self):
        frozen, resources, executable = self.native_context()
        with frozen, resources, executable:
            provenance = capture_provenance()
            self.require(provenance)
            self.assertEqual(provenance['worktree'], 'UNAVAILABLE')
            self.assertEqual(provenance['financial_authority'], 'NONE')

    def test_source_process_cannot_promote_caller_native_identity_strings(self):
        frozen, resources, executable = self.native_context()
        with frozen, resources, executable: provenance = capture_provenance()
        with self.assertRaises(EvidenceGateError): self.require(provenance)

    def test_current_native_tamper_or_recorded_build_drift_is_rejected(self):
        frozen, resources, executable = self.native_context()
        with frozen, resources, executable:
            provenance = capture_provenance()
            changed = dict(provenance, build_hash='sha256:' + '0' * 64)
            with self.assertRaises(EvidenceGateError): self.require(changed)
            (self.fixture.root / '_internal' / 'native-code.bin').write_bytes(b'ACTUAL_TAMPER')
            with self.assertRaises(EvidenceGateError): self.require(provenance)

    def test_dirty_missing_revision_and_unavailable_source_provenance_stay_denied(self):
        for status, revision in (('DIRTY', 'a' * 40), ('UNAVAILABLE', 'a' * 40), ('CLEAN', None)):
            provenance = dict(execution='LOCAL', worktree=status, executable_revision=revision)
            with self.subTest(status=status, revision=revision), self.assertRaises(EvidenceGateError):
                self.require(provenance)
