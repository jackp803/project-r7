"""No workload execution: reject arbitrary public-proof references before reading."""
import ast, copy, unittest
from pathlib import Path

DRIVER=Path(__file__).with_name('s09_forward_ui_serial_browser.py')
tree=ast.parse(DRIVER.read_text(encoding='utf-8'))
node=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require_prefix_inventory'),None)
scope={}
if node is not None:exec(compile(ast.Module(body=[node],type_ignores=[]),str(DRIVER),'exec'),scope)

class PrefixGuards(unittest.TestCase):
    def setUp(self):
        self.assertIn('require_prefix_inventory',scope,'Prefix inventory guard missing')
        self.guard=scope['require_prefix_inventory']
        self.helpers={'known-driver','known-interpreter'}
        self.proof=dict(helper_hashes={p:'bound' for p in self.helpers},commands=[
            dict(label=label,log=label+'.log') for label in ['contract','typecheck','unit','build','browser']])
    def test_exact_known_inventory_allowed(self):
        self.guard(self.proof,self.helpers)
    def test_private_absolute_helper_rejected(self):
        self.proof['helper_hashes']['C:/private/secret-file']='untrusted'
        with self.assertRaises(ValueError):self.guard(self.proof,self.helpers)
    def test_escaping_log_rejected(self):
        self.proof['commands'][0]['log']='../../private/secret-file'
        with self.assertRaises(ValueError):self.guard(self.proof,self.helpers)
    def test_changed_command_inventory_rejected(self):
        self.proof['commands'][0]['label']='arbitrary'
        with self.assertRaises(ValueError):self.guard(self.proof,self.helpers)
    def test_omitted_helper_rejected(self):
        self.proof['helper_hashes'].pop('known-interpreter')
        with self.assertRaises(ValueError):self.guard(self.proof,self.helpers)

if __name__=='__main__':unittest.main(verbosity=2)
