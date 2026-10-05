import ast
import email.message
import io
from pathlib import Path
import unittest
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

path=Path(__file__).with_name('s13_native_recovery_probe.py')
tree=ast.parse(path.read_text(encoding='utf-8'))
classes=[node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='NoRedirect']
assert len(classes)==1
namespace={'HTTPRedirectHandler':HTTPRedirectHandler,'HTTPError':HTTPError}
exec(compile(ast.Module(body=classes,type_ignores=[]),'qualification-harness-redirect','exec'),namespace)

class LoopbackHarnessRegression(unittest.TestCase):
    def test_explicit_empty_proxy_has_no_default_environment_or_system_proxy(self):
        proxy=ProxyHandler({})
        self.assertEqual(proxy.proxies,{})
        opener=build_opener(proxy,namespace['NoRedirect']())
        self.assertFalse(any(isinstance(handler,ProxyHandler) and handler.proxies for handler in opener.handlers))
        # The actual harness must use the exact explicit empty handler.
        calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='build_opener']
        self.assertEqual(len(calls),1)
        self.assertTrue(any(isinstance(argument,ast.Call) and isinstance(argument.func,ast.Name)
            and argument.func.id=='ProxyHandler' and len(argument.args)==1 and isinstance(argument.args[0],ast.Dict)
            and not argument.args[0].keys for argument in calls[0].args))
    def test_redirect_cannot_replay_a_synthetic_private_request_outside_loopback(self):
        request=Request('http://127.0.0.1:8765/api/v1/auth/login',data=b'SYNTHETIC_TEST_BODY',headers={'Cookie':'SYNTHETIC_TEST_COOKIE'})
        handler=namespace['NoRedirect']()
        for target in ('https://outside.invalid/private','http://127.0.0.1:9999/other'):
            with self.subTest(target=target),self.assertRaises(HTTPError) as caught:
                handler.redirect_request(request,io.BytesIO(),302,'redirect',email.message.Message(),target)
            self.assertEqual(caught.exception.code,302)
            self.assertEqual(caught.exception.reason,'NATIVE_QUALIFICATION_REDIRECT_DENIED')

if __name__=='__main__':
    unittest.main(verbosity=2)
