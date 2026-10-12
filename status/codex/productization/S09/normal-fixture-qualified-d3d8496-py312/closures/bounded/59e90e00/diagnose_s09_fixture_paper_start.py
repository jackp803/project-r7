"""Observe a sanitized exception from the real source start; diagnosis only."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO));sys.path.insert(0,str(REPO/'src'))
from application.paper.service import PaperService
from tests.application.test_normal_fixture_paper import NormalFixturePaperTests
original=PaperService.start
def observed(*args,**kwargs):
    try:return original(*args,**kwargs)
    except Exception as error:
        print('SANITIZED_FIXTURE_START_EXCEPTION',type(error).__name__,str(error),flush=True)
        raise
with patch.object(PaperService,'start',observed):
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
        NormalFixturePaperTests('test_normal_candidate_selects_paper_and_api_prepares_generation_zero')]))
raise SystemExit(0 if result.wasSuccessful() else 1)
