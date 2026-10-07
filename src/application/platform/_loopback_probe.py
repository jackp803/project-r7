"""Owned child for bounded public loopback auth-status facts, no credentials."""
import argparse
import json
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler,ProxyHandler,Request,build_opener

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate public status field')
        result[key]=value
    return result

def decode_status(raw,expected_namespace):
    if len(raw)>2048:raise ValueError('Bounded public status required')
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Finite public status required')))
    if (type(value) is not dict or set(value)!={'configured','namespace','enrollment'}
            or type(value['configured']) is not bool or value['namespace']!=expected_namespace
            or value['enrollment']!='LOCAL_CLI_ONLY'):
        raise ValueError('Exact public auth status required')
    return value

def fetch_status(port,expected_namespace):
    opener=build_opener(ProxyHandler({}),NoRedirect())
    request=Request(f'http://127.0.0.1:{port}/api/v1/auth/status',headers={'Accept':'application/json'})
    try:
        with opener.open(request,timeout=2) as response:
            if response.status!=200 or response.headers.get_content_type()!='application/json':
                raise ValueError('Public JSON endpoint required')
            value=decode_status(response.read(2049),expected_namespace)
    except HTTPError as error:
        error.close()
        return dict(status='UNAVAILABLE',reason_code='REDIRECT_FORBIDDEN' if 300<=error.code<400 else 'PUBLIC_STATUS_UNAVAILABLE'),2
    except ValueError:
        return dict(status='UNAVAILABLE',reason_code='PUBLIC_STATUS_INVALID'),2
    except Exception:
        return dict(status='UNAVAILABLE',reason_code='PUBLIC_STATUS_UNAVAILABLE'),2
    return dict(status='PUBLIC_AUTH_STATUS_AVAILABLE',public_auth_status=value),0

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,required=True)
    parser.add_argument('--expected-namespace',choices=('LOCAL_RESEARCH','FIXTURE'),required=True)
    args=parser.parse_args(argv)
    if not 1024<=args.port<=65535:raise ValueError('Nonprivileged local API port required')
    result,code=fetch_status(args.port,args.expected_namespace)
    print(json.dumps(result,separators=(',',':')))
    return code

if __name__=='__main__':raise SystemExit(main())
