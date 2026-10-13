"""Startup denial retains fixed diagnostic facts without echoing user material."""
from contextlib import redirect_stderr
import io,json,unittest
from unittest.mock import patch
from application import cli
from application.cloud.protocol import CloudError


class CliStartupDiagnosticTests(unittest.TestCase):
    def denied(self,error):
        with patch.object(cli,'main',side_effect=error),patch('sys.frozen',False,create=True),redirect_stderr(io.StringIO()) as output:
            self.assertEqual(cli.run(),2)
        text=output.getvalue()
        self.assertIn('R7: local configuration or startup validation failed',text)
        self.assertNotIn('SYNTHETIC_SECRET',text)
        return json.loads(text.splitlines()[-1])

    def test_validation_denial_emits_category_without_exception_message(self):
        result=self.denied(ValueError('SYNTHETIC_SECRET profile/path/password'))
        self.assertEqual(result['schema_version'],'r7-startup-diagnostic-v0.2')
        self.assertEqual(result['error_kind'],'VALIDATION')
        self.assertEqual(result['reason_code'],'LOCAL_STARTUP_VALIDATION_FAILED')

    def test_wrapped_publication_failure_retains_only_known_reason_and_errno(self):
        low=OSError(13,'SYNTHETIC_SECRET',r'C:\SYNTHETIC_SECRET\config.json')
        middle=CloudError('UNAVAILABLE','PUBLICATION_FINALIZE_FAILED');middle.__cause__=low
        high=ValueError('SYNTHETIC_SECRET');high.__cause__=middle
        result=self.denied(high)
        self.assertEqual(result['reason_code'],'PUBLICATION_FINALIZE_FAILED')
        self.assertEqual(result['os_error'],13)
        self.assertNotIn('message',result)
        self.assertNotIn('path',result)

    def test_unknown_reason_and_long_cyclic_cause_chain_cannot_echo_or_hang(self):
        error=CloudError('BLOCKED','SYNTHETIC_SECRET');error.__cause__=error
        result=self.denied(error)
        self.assertEqual(result['reason_code'],'LOCAL_STARTUP_VALIDATION_FAILED')
        self.assertIsNone(result['os_error'])


if __name__=='__main__':unittest.main()
