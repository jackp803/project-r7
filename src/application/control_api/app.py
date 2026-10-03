"""Authenticated loopback FastAPI adapter; only trusted owners perform effects."""
import ipaddress
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse
from application.config import ProductConfig
from application.control_api.auth import LocalAuth, AuthenticationError
from application.control_api.commands import CommandLedger, CommandError, CommandClaim
from application.control_api.dto import (
    ApprovalDTO, ApprovalPreviewQuery, ApprovalPreviewView, CapabilitiesView, CommandDTO, CommandReceipt, DeploymentActivateDTO, DeploymentPauseDTO,
    ErrorResponse, HealthView, LoginDTO, OverviewView, OwnerObjectView, PageQuery, PageView,
    PaperStartDTO, ReauthenticationDTO, ResearchEnqueueDTO, SettingsDTO, SettingsView, TradingView, ViewEnvelope,
    AuthStatusView, LoginView, SessionView, LogoutView,
)
from application.control_api.errors import APIError, error_response
from application.control_api.security import LocalSecurityMiddleware
from application.control_api.services import LocalControlServices
from registry.operational_authority import HumanAuthenticator


def create_app(config: ProductConfig, *, auth: LocalAuth, commands: CommandLedger, services=None):
    if not isinstance(config, ProductConfig) or not ipaddress.ip_address(config.control_api_host).is_loopback:
        raise ValueError('Explicit loopback product configuration required')
    if not isinstance(auth, LocalAuth) or not isinstance(commands, CommandLedger) or auth.namespace != commands.namespace:
        raise ValueError('Same namespace local authentication and command store required')
    if any(not path.is_relative_to(config.local_data_root) or path == config.database_path for path in (auth.path, commands.path)):
        raise ValueError('Isolated authentication/command stores inside configured local root required')
    owners = services if services is not None else LocalControlServices(config, namespace=auth.namespace, clock=auth.clock)
    if owners.namespace != auth.namespace: raise ValueError('Same namespace service composition required')
    issuer = HumanAuthenticator(namespace=auth.namespace, verifier=auth.verify_reauthentication,
        current_verifier=auth.verify_reauthentication, reauth_seconds=300, clock=auth.clock)
    if hasattr(owners,'install_authenticator'): owners.install_authenticator(issuer)
    app = FastAPI(title='R7 Local Control API', version='0.2.0', docs_url=None, redoc_url=None,
                  openapi_url=None, strict_content_type=True,
                  responses={code:dict(model=ErrorResponse) for code in (400,401,403,409,413,415,422,429,500,503)})
    app.state.owners, app.state.authenticator = owners, issuer
    app.add_middleware(LocalSecurityMiddleware, host=config.control_api_host, port=config.control_api_port)

    @app.exception_handler(RequestValidationError)
    async def invalid_dto(request, error):
        return error_response('INVALID_INPUT', 'DTO_VALIDATION_FAILED', 422)

    @app.exception_handler(AuthenticationError)
    async def invalid_auth(request, error):
        status = 409 if error.code == 'CONFLICT' else 403 if error.code == 'CSRF_REQUIRED' else 429 if error.code == 'AUTHENTICATION_THROTTLED' else 401
        return error_response('CONFLICT' if status == 409 else 'AUTHORIZATION_REQUIRED', error.code, status)

    @app.exception_handler(CommandError)
    async def invalid_command(request, error):
        category, status = ('INVALID_INPUT', 422) if error.code == 'INVALID_INPUT' else ('UNAVAILABLE', 503) if error.code.endswith('CORRUPT') or error.code.endswith('CAPACITY_REACHED') else ('CONFLICT', 409)
        return error_response(category, error.reason, status)

    @app.exception_handler(APIError)
    async def owner_error(request, error):
        return error_response(error.category, error.reason, error.status_code)

    def signed(request):
        return auth.authenticate(request.cookies.get('r7_session'))

    def write_session(request):
        actor = signed(request)
        auth.require_csrf(request.cookies.get('r7_session'), request.headers.get('x-r7-csrf'))
        return actor

    def view(request, name, *, subject=None, limit=50, offset=0):
        signed(request)
        data = owners.view(name, subject=subject, limit=limit, offset=offset)
        return dict(metadata=owners.metadata('application:'+name,data=data), data=data)

    def dispatch(request, body, operation, resource, *, financial=False):
        identity = write_session(request); human = None
        if financial:
            if auth.namespace == 'FIXTURE': raise APIError('AUTHORIZATION_REQUIRED', 'FIXTURE_FINANCIAL_AUTHORITY_FORBIDDEN', 403)
            human = issuer.authenticate(auth.current_reauthentication(request.cookies.get('r7_session')))
        arguments = body.model_dump(exclude={'command_id', 'expected_revision'})
        actual = owners.revision(operation, resource, arguments)
        claim = commands.prepare(command_id=body.command_id, operation=operation, resource=resource,
            actor=identity.actor, expected_revision=body.expected_revision, actual_revision=actual, arguments=arguments)
        if isinstance(claim, dict):
            if 'error_response' in claim: return JSONResponse(claim['error_response'], status_code=claim['status_code'])
            return JSONResponse(claim, status_code=202 if claim['status'] == 'QUEUED' else 200)
        try:
            receipt = owners.execute(operation, resource, arguments, actor=identity.actor, human=human,
                command_id=body.command_id, expected_revision=body.expected_revision)
            receipt = CommandReceipt.model_validate(receipt).model_dump()
        except APIError as error:
            response = error_response(error.category, error.reason, error.status_code)
            import json
            if error.terminal: commands.complete(claim, dict(error_response=json.loads(response.body), status_code=error.status_code))
            return response
        # Unknown outcomes remain PREPARED for owner reconciliation under the same
        # command ID. An internal error is never proof that the owner did nothing.
        commands.complete(claim, receipt)
        return JSONResponse(receipt, status_code=202 if receipt['status'] == 'QUEUED' else 200)

    @app.get('/api/v1/auth/status',response_model=AuthStatusView)
    async def authentication_status():
        return dict(configured=auth.configured(), namespace=auth.namespace, enrollment='LOCAL_CLI_ONLY')

    @app.post('/api/v1/auth/login',response_model=LoginView)
    async def login(body: LoginDTO):
        grant = auth.login(body.username, body.password, command_id=body.command_id, expected_revision=body.expected_revision)
        response = JSONResponse(dict(actor=grant.actor, revision=grant.revision, expires_at=grant.expires_at,
            csrf_token=grant.csrf_token, namespace=auth.namespace))
        response.set_cookie('r7_session', grant.token, httponly=True, samesite='strict', secure=False,
                            path='/api/v1', max_age=auth.duration)
        response.set_cookie('r7_csrf', grant.csrf_token, httponly=False, samesite='strict', secure=False,
                            path='/', max_age=auth.duration)
        return response

    @app.get('/api/v1/auth/session',response_model=SessionView)
    async def session(request: Request):
        signed(request)
        return auth.session_view(request.cookies.get('r7_session'))

    @app.post('/api/v1/auth/reauthenticate',response_model=SessionView)
    async def reauthenticate(request: Request, body: ReauthenticationDTO):
        write_session(request)
        auth.reauthenticate(request.cookies.get('r7_session'), body.password, expected_revision=body.expected_revision)
        return auth.session_view(request.cookies.get('r7_session'))

    @app.post('/api/v1/auth/logout',response_model=LogoutView)
    async def logout(request: Request, body: CommandDTO):
        write_session(request)
        auth.logout(request.cookies.get('r7_session'), expected_revision=body.expected_revision)
        response = JSONResponse(dict(status='LOGGED_OUT'))
        response.delete_cookie('r7_session', path='/api/v1'); response.delete_cookie('r7_csrf', path='/')
        return response

    @app.get('/api/v1/openapi')
    async def openapi(request: Request):
        signed(request); return app.openapi()

    @app.get('/api/v1/overview', response_model=ViewEnvelope[OverviewView])
    async def overview(request: Request): return view(request, 'overview')

    @app.get('/api/v1/health', response_model=ViewEnvelope[HealthView])
    async def health(request: Request): return view(request, 'health')

    @app.get('/api/v1/capabilities', response_model=ViewEnvelope[CapabilitiesView])
    async def capabilities(request: Request): return view(request, 'capabilities')

    @app.get('/api/v1/trading', response_model=ViewEnvelope[TradingView])
    async def trading(request: Request): return view(request, 'trading')

    @app.get('/api/v1/settings', response_model=ViewEnvelope[SettingsView])
    async def settings(request: Request): return view(request, 'settings')

    def page_route(name):
        async def page(request: Request, query: Annotated[PageQuery, Query()]):
            return view(request, name, limit=query.limit, offset=query.offset)
        return page
    for path, name in (('submissions', 'submissions'), ('research/runs', 'research_runs'), ('strategies', 'strategies'),
                       ('datasets', 'datasets'), ('policies', 'policies'), ('alerts', 'alerts'), ('paper/runs','paper_runs')):
        app.add_api_route('/api/v1/'+path, page_route(name), methods=['GET'], name=name, response_model=ViewEnvelope[PageView])

    @app.get('/api/v1/submissions/{submission_id}', response_model=ViewEnvelope[OwnerObjectView])
    async def submission(request: Request, submission_id: str): return view(request, 'submissions', subject=submission_id)

    @app.get('/api/v1/research/runs/{run_id}', response_model=ViewEnvelope[OwnerObjectView])
    async def research_run(request: Request, run_id: str): return view(request, 'research_runs', subject=run_id)

    @app.get('/api/v1/strategies/{strategy_id}/{strategy_version}', response_model=ViewEnvelope[OwnerObjectView])
    async def strategy(request: Request, strategy_id: str, strategy_version: str):
        return view(request, 'strategies', subject=(strategy_id, strategy_version))

    @app.get('/api/v1/strategies/{strategy_id}/{strategy_version}/approval-preview',response_model=ViewEnvelope[ApprovalPreviewView])
    async def approval_preview(request: Request,strategy_id: str,strategy_version: str,query: Annotated[ApprovalPreviewQuery,Query()]):
        return view(request,'approval_preview',subject=(strategy_id,strategy_version,query.envelope_ref,query.expected_revision))

    @app.get('/api/v1/paper/runs/{run_id}', response_model=ViewEnvelope[OwnerObjectView])
    async def paper_run(request: Request, run_id: str): return view(request, 'paper_runs', subject=run_id)

    responses = {status: dict(model=ErrorResponse) for status in (401, 403, 409, 422, 503)}

    @app.post('/api/v1/research/scan', response_model=CommandReceipt, responses=responses)
    async def research_scan(request: Request, body: CommandDTO): return dispatch(request, body, 'INBOX_SCAN', 'inbox')

    @app.post('/api/v1/research/runs', response_model=CommandReceipt, responses=responses, status_code=202)
    async def enqueue(request: Request, body: ResearchEnqueueDTO): return dispatch(request, body, 'RESEARCH_ENQUEUE', 'submission:'+body.submission_id)

    @app.post('/api/v1/research/runs/{run_id}/cancel', response_model=CommandReceipt, responses=responses)
    async def cancel(request: Request, run_id: str, body: CommandDTO): return dispatch(request, body, 'RESEARCH_CANCEL', 'research:'+run_id)

    @app.post('/api/v1/paper/runs', response_model=CommandReceipt, responses=responses)
    async def paper_start(request: Request, body: PaperStartDTO):
        return dispatch(request, body, 'PAPER_START', 'strategy:'+body.strategy_id+':'+body.strategy_version)

    @app.post('/api/v1/paper/runs/{run_id}/pause', response_model=CommandReceipt, responses=responses)
    async def paper_pause(request: Request, run_id: str, body: CommandDTO): return dispatch(request, body, 'PAPER_PAUSE', 'paper:'+run_id)

    @app.put('/api/v1/settings/non-secret', response_model=CommandReceipt, responses=responses)
    async def settings_update(request: Request, body: SettingsDTO): return dispatch(request, body, 'SETTINGS_UPDATE', 'settings')

    @app.post('/api/v1/approvals', response_model=CommandReceipt, responses=responses)
    async def approve(request: Request, body: ApprovalDTO):
        return dispatch(request, body, 'APPROVAL', 'strategy:'+body.strategy_id+':'+body.strategy_version, financial=True)

    @app.post('/api/v1/deployments/{deployment_id}/activate', response_model=CommandReceipt, responses=responses)
    async def activate(request: Request, deployment_id: str, body: DeploymentActivateDTO):
        return dispatch(request, body, 'DEPLOYMENT_ACTIVATE', 'deployment:'+deployment_id, financial=True)

    @app.post('/api/v1/deployments/{deployment_id}/pause', response_model=CommandReceipt, responses=responses)
    async def pause(request: Request, deployment_id: str, body: DeploymentPauseDTO):
        return dispatch(request, body, 'DEPLOYMENT_PAUSE', 'deployment:'+deployment_id)

    def documented_openapi():
        if app.openapi_schema is not None: return app.openapi_schema
        document=get_openapi(title=app.title,version=app.version,routes=app.routes)
        document['components']['securitySchemes']={
            'r7_session':dict(type='apiKey',**{'in':'cookie'},name='r7_session',description='Opaque local server session; HttpOnly/SameSite=strict'),
            'r7_csrf':dict(type='apiKey',**{'in':'header'},name='X-R7-CSRF',description='Session-bound CSRF proof; exact same Origin is also required'),
        }
        for path,methods in document['paths'].items():
            for method,operation in methods.items():
                if path in ('/api/v1/auth/login','/api/v1/auth/status'): continue
                operation['security']=[dict(r7_session=[],**({'r7_csrf':[]} if method in ('post','put') else {}))]
        document['servers']=[dict(url='/')]
        app.openapi_schema=document
        return document
    app.openapi=documented_openapi
    return app
