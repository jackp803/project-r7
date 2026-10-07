"""Run only five approved source-created accelerated owner mechanics cases."""
import sys,unittest
from unittest.mock import patch
from s15_tactical_owner_acceptance_cases import TacticalOwnerAcceptanceTests
mode=sys.argv[1]
if mode not in ('NORMAL','MUTATION_CONTROL'):raise ValueError('Fixed local fixture mode required')
suite=unittest.defaultTestLoader.loadTestsFromTestCase(TacticalOwnerAcceptanceTests)
assert suite.countTestCases()==5
if mode=='MUTATION_CONTROL':
    from application.paper.engine import PaperEngine
    original=PaperEngine._entry_allowed
    def bypass_temporal_only(self,runtime,now):
        allowed,reason=original(self,runtime,now)
        return (True,None) if not allowed and reason in ('SUBMISSION_EXPIRED','SUBMISSION_NOT_YET_VALID') else (allowed,reason)
    with patch.object(PaperEngine,'_entry_allowed',bypass_temporal_only):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
else:result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
