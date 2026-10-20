"""Source-fixture exception locations/codes only; no DB or provider payload dump."""
import sys,unittest
def trace(frame,event,arg):
    if event=='exception' and frame.f_code.co_filename.replace('\\','/').endswith('storage/trading_feedback.py'):
        kind,error,unused=arg
        print('READER_EXCEPTION',frame.f_lineno,kind.__name__,repr(error.args[0]) if kind is KeyError else getattr(error,'code','NO_CODE'),flush=True)
    return trace
sys.settrace(trace)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName(
    'tests.product.test_k05_readonly_history.K05ActualOpenOwnerHistoryTests.test_actual_ack_and_pending_order_are_not_closed_performance'))
sys.settrace(None)
raise SystemExit(not result.wasSuccessful())
