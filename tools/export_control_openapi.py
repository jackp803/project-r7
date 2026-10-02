"""Generate the actual local API contract without enrolling a user or runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from application.config import ProductConfig
from application.control_api.app import create_app
from application.control_api.auth import LocalAuth
from application.control_api.commands import CommandLedger


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scratch-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    scratch=args.scratch_root.absolute(); scratch.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='openapi-',dir=scratch) as folder:
        root=Path(folder)
        config=ProductConfig('r7-product-config-v0.2','openapi-uncommissioned',root,None,root/'canonical.sqlite')
        auth=LocalAuth(root/'auth.sqlite',namespace='FIXTURE')
        app=create_app(config,auth=auth,commands=CommandLedger(root/'commands.sqlite',namespace='FIXTURE'))
        raw=(json.dumps(app.openapi(),ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    output=args.output.absolute(); output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(raw)
    print(json.dumps(dict(openapi_bytes=len(raw),sha256='sha256:'+hashlib.sha256(raw).hexdigest())))


if __name__=='__main__': main()
