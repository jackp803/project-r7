"""Source-only driver boundary checks; mocked flows earn no native credit."""
import importlib
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


class PaperNativeDriverTests(unittest.TestCase):
    def module(self):
        root=Path(__file__).resolve().parents[2]
        with patch.object(sys,'path',[str(root/'tools'),*sys.path]):
            return importlib.import_module('tools.verify_paper_product')

    def verify(self,module,package,output):
        progress=io.StringIO()
        with redirect_stdout(progress):
            code=module.verify(package,output,'PQR-03')
        self.assertEqual(json.loads(progress.getvalue())['passed'],False)
        return code

    def test_every_scenario_and_final_distribution_match_original_group_subject(self):
        m=self.module();a=dict(build_hash='a');b=dict(build_hash='b')
        for identities in ([a,b,a,a,a],[a,a,a,a,b]):
            with self.subTest(identities=identities),TemporaryDirectory() as temp:
                root=Path(temp);output=root/'result'
                with patch.object(m,'verify_distribution',side_effect=identities), \
                     patch.object(m.PublicFixture,'run',lambda self:dict(passed=True,identity=self.identity)):
                    (root/'package').mkdir()
                    (root/'package/distribution.json').write_text('{"entrypoint":"R7.exe"}')
                    self.assertEqual(self.verify(m,root/'package',output),2)
                report=json.loads((output/'native-observations.json').read_bytes())
                self.assertFalse(report['passed'])
                self.assertEqual(report['reason'],'ACTUAL_NATIVE_GROUP_FAILED')

    def test_artifact_alias_is_rejected_before_reading_external_sentinel(self):
        m=self.module()
        with TemporaryDirectory() as temp:
            root=Path(temp);output=root/'result';sentinel=root/'external.log'
            sentinel.write_bytes(b'OWNED_EXTERNAL_SENTINEL')
            def observation(fixture):
                if fixture.scenario=='positive':os.link(sentinel,fixture.output/'aliased.log')
                return dict(passed=True,identity=fixture.identity)
            package=root/'package';package.mkdir();(package/'distribution.json').write_text('{"entrypoint":"R7.exe"}')
            with patch.object(m,'verify_distribution',return_value=dict(build_hash='a')), \
                 patch.object(m.PublicFixture,'run',observation):
                self.assertEqual(self.verify(m,package,output),2)
            self.assertFalse(json.loads((output/'native-observations.json').read_bytes())['passed'])
            self.assertEqual(sentinel.read_bytes(),b'OWNED_EXTERNAL_SENTINEL')


if __name__=='__main__':unittest.main()
