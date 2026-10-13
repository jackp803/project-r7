"""Execute the committed fixed PQR inventory locally; no imported PASS input."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.paper.producer import qualify


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--package-root',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=qualify(args.config,ROOT,args.package_root);print(json.dumps(result))
        return 0 if result['status']=='NATIVE_PAPER_SOFTWARE_QUALIFIED' else 2
    except Exception:
        print('PQR local exact-clean qualification failed; preserve this attempt and inspect its retained sanitized evidence',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
