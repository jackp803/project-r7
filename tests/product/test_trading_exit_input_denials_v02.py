"""ONE genuine original EXIT input-denial case."""
import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from application.trading.admission import RuntimeAdmissionError
from tests.product import h01_original_exit_fixture as original_fixtures
from tests.product import h01_exit_failure_fixtures as helpers


class TradingExitInputDenialsV02Tests(unittest.TestCase):
    def test_copied_expired_and_genuinely_issued_mismatched_native_reads_cannot_create_exit(self):
        with original_fixtures.H01OriginalExitFixture(self) as c:
            f=c.f;entry_id=c.entry_decision.decision_id
            anchor=helpers.held_anchor(c)
            before_rows=helpers.exit_rows(f.dispatch,c.service.run_id,entry_id)
            before_graph=c.recover();before_calls=tuple(c.provider.calls)
            arguments=c.exit_arguments()
            with self.assertRaises(RuntimeAdmissionError) as caught:
                c.runner.evaluate_original_exit(f.bundle.boundary,
                    **dict(arguments,native_position=replace(c.native)))
            self.assertEqual(('CURRENT_ISSUER_NATIVE_POSITION_READ_REQUIRED',),caught.exception.reason_codes)
            self.assertEqual(before_calls,tuple(c.provider.calls))
            self.assertEqual(before_rows,helpers.exit_rows(f.dispatch,c.service.run_id,entry_id))

            c.clock[0]+=timedelta(seconds=6)  # Existing issuer-read lifetime is5s.
            with self.assertRaises(RuntimeAdmissionError) as caught:
                c.runner.evaluate_original_exit(f.bundle.boundary,**arguments)
            self.assertEqual(('CURRENT_ISSUER_NATIVE_POSITION_READ_REQUIRED',),caught.exception.reason_codes)
            self.assertEqual(before_calls,tuple(c.provider.calls))
            self.assertEqual(before_rows,helpers.exit_rows(f.dispatch,c.service.run_id,entry_id))

            # An actual new normal issued read, not a copied/mutated evidence
            # object. Its observed quantity disagrees with canonical full entry.
            c.metadata,c.read_proof=c.fresh()
            c.append(c.position_response('6'))
            call_count=len(c.provider.calls)
            c.native=c.service.read_position(metadata=c.metadata,proof=c.read_proof,
                expected_revision=c.revision,expected_provider_position_id='5678')
            self.assertEqual(['GET'],[row['method'] for row in c.provider.calls[call_count:]])
            self.assertEqual('/api/v5/account/positions',c.provider.calls[-1]['path'])
            self.assertNotEqual(c.native.canonical_net_quantity,
                Decimal(before_graph.current_position_projection.payload['actual_quantity']))
            after_read=len(c.provider.calls)
            with self.assertRaises(RuntimeAdmissionError) as caught:
                c.runner.evaluate_original_exit(f.bundle.boundary,**c.exit_arguments())
            self.assertEqual(('EXIT_ORIGINAL_CURRENT_NATIVE_SOURCE_REQUIRED',),caught.exception.reason_codes)
            self.assertEqual(after_read,len(c.provider.calls),'Exit denial must issue no extra provider request')
            self.assertEqual(anchor,f.dispatch.exit_anchor(c.service.run_id,entry_id))
            self.assertIsNone(f.dispatch.exit_decision(c.service.run_id,entry_id))
            self.assertEqual(before_rows,helpers.exit_rows(f.dispatch,c.service.run_id,entry_id))
            self.assertEqual(before_graph,c.assert_binding())
            self.assertEqual(2,len([row for row in c.provider.calls if row['method']=='POST']))
            self.assertFalse(any(row.payload.get('action')=='EXIT' for row in c.recover().position_actions))
            self.assertFalse(c.provider._responses)
