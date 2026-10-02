"""Loopback-only ASGI boundary; no trusting forwarded Host/Origin or CORS."""
import asyncio
import ipaddress
from application.datasets.catalog import decode, DatasetError
from application.control_api.errors import error_response


class LocalSecurityMiddleware:
    def __init__(self, app, *, host, port):
        self.app = app
        literal = '[' + host + ']' if ':' in host else host
        self.hosts = {literal + ':' + str(port), 'localhost:' + str(port)}
        self.origins = {'http://' + item for item in self.hosts}

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            await send({'type': 'websocket.close', 'code': 1008}); return
        if scope['type'] != 'http':
            await self.app(scope, receive, send); return
        headers = {}
        duplicates = set()
        for key, value in scope.get('headers', []):
            key = key.decode('latin1').lower()
            if key in headers: duplicates.add(key)
            headers[key] = value.decode('latin1')
        async def guarded_send(message):
            if message['type'] == 'http.response.start':
                message['headers'] = list(message.get('headers', [])) + [
                    (b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff'),
                    (b'x-frame-options', b'DENY'), (b'referrer-policy', b'no-referrer'),
                    (b'content-security-policy', b"default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")]
            await send(message)
        async def reject(category, reason, status):
            await error_response(category, reason, status)(scope, receive, guarded_send)
        try:
            client = scope.get('client')
            if client is None or not ipaddress.ip_address(client[0]).is_loopback:
                await reject('AUTHORIZATION_REQUIRED', 'LOOPBACK_REQUIRED', 403); return
        except ValueError:
            await reject('AUTHORIZATION_REQUIRED', 'LOOPBACK_REQUIRED', 403); return
        if duplicates & {'host', 'origin', 'cookie', 'content-length', 'content-type', 'x-r7-csrf'} or headers.get('host') not in self.hosts:
            await reject('INVALID_INPUT', 'HOST_NOT_ALLOWED', 400); return
        if headers.get('sec-fetch-site') == 'cross-site':
            await reject('AUTHORIZATION_REQUIRED', 'CROSS_SITE_FORBIDDEN', 403); return
        origin = headers.get('origin')
        if origin is not None and origin not in self.origins:
            await reject('AUTHORIZATION_REQUIRED', 'ORIGIN_NOT_ALLOWED', 403); return
        if scope['method'] not in ('GET', 'HEAD', 'POST', 'PUT'):
            await reject('INVALID_INPUT', 'METHOD_NOT_ALLOWED', 405); return
        replay_receive = receive
        if scope['method'] in ('POST', 'PUT'):
            if origin not in self.origins:
                await reject('AUTHORIZATION_REQUIRED', 'SAME_ORIGIN_REQUIRED', 403); return
            if headers.get('content-type', '').lower().split(';')[0].strip() != 'application/json':
                await reject('INVALID_INPUT', 'JSON_CONTENT_TYPE_REQUIRED', 415); return
            length = headers.get('content-length')
            if length is not None:
                if not length.isdigit():
                    await reject('INVALID_INPUT', 'BODY_LENGTH_INVALID', 422); return
                if int(length) > 65536:
                    await reject('INVALID_INPUT', 'BODY_SIZE_LIMIT', 413); return
            body = bytearray()
            while True:
                try: message = await asyncio.wait_for(receive(), 5)
                except TimeoutError:
                    await reject('INVALID_INPUT', 'BODY_TIMEOUT', 408); return
                if message['type'] != 'http.request':
                    await reject('INVALID_INPUT', 'BODY_INCOMPLETE', 422); return
                body.extend(message.get('body', b''))
                if len(body) > 65536:
                    await reject('INVALID_INPUT', 'BODY_SIZE_LIMIT', 413); return
                if not message.get('more_body', False): break
            try:
                parsed = decode(bytes(body))
                if not isinstance(parsed, dict): raise DatasetError('OBJECT_REQUIRED')
            except DatasetError:
                await reject('INVALID_INPUT', 'STRICT_JSON_REQUIRED', 422); return
            delivered = False
            async def replay_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()
        try: await self.app(scope, replay_receive, guarded_send)
        except Exception:
            # No exception text, request body, stack, local path or credential.
            await reject('INTERNAL_ERROR', 'CONTROL_OPERATION_FAILED', 500)
