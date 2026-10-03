"""Versioned strict HTTP DTOs. Domain payloads retain owning contract identity."""
from typing import Annotated, Generic, Literal, TypeVar
from pydantic import BaseModel, ConfigDict, Field, JsonValue

Identifier = Annotated[str, Field(min_length=1, max_length=96, pattern=r'^[A-Za-z0-9][A-Za-z0-9_.:-]*$')]
Hash = Annotated[str, Field(pattern=r'^sha256:[0-9a-f]{64}$')]
Revision = Annotated[int, Field(ge=0, le=2**53-1)]


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class CommandDTO(StrictDTO):
    command_id: Identifier
    expected_revision: Revision


class LoginDTO(CommandDTO):
    username: Identifier
    password: Annotated[str, Field(min_length=1, max_length=256, repr=False, json_schema_extra={'writeOnly':True})]


class ReauthenticationDTO(CommandDTO):
    password: Annotated[str, Field(min_length=1, max_length=256, repr=False, json_schema_extra={'writeOnly':True})]


class AuthStatusView(StrictDTO):
    configured: bool
    namespace: Literal['FIXTURE','LOCAL_RESEARCH']
    enrollment: Literal['LOCAL_CLI_ONLY']


class LoginView(StrictDTO):
    actor: Identifier
    revision: int
    expires_at: str
    csrf_token: str
    namespace: Literal['FIXTURE','LOCAL_RESEARCH']


class SessionView(StrictDTO):
    actor: Identifier
    roles: list[Literal['ProductOwner']]
    revision: int
    expires_at: str
    reauthenticated_until: str | None
    namespace: Literal['FIXTURE','LOCAL_RESEARCH']


class LogoutView(StrictDTO):
    status: Literal['LOGGED_OUT']


class ResearchEnqueueDTO(CommandDTO):
    submission_id: Identifier
    policy_id: Identifier


class PaperStartDTO(CommandDTO):
    strategy_id: Identifier
    strategy_version: Identifier
    policy_id: Identifier


class ApprovalDTO(CommandDTO):
    strategy_id: Identifier
    strategy_version: Identifier
    envelope_ref: Identifier
    decision: Literal['APPROVE', 'REJECT']
    reason_code: Literal['USER_CONFIRMED', 'USER_REJECTED']
    expected_strategy_hash: Hash
    expected_envelope_hash: Hash


class DeploymentActivateDTO(CommandDTO):
    strategy_id: Identifier
    strategy_version: Identifier
    evidence_ref: Identifier


class DeploymentPauseDTO(CommandDTO):
    strategy_id: Identifier
    strategy_version: Identifier


class SettingsDTO(CommandDTO):
    display_timezone: Literal['UTC', 'Asia/Taipei']
    scan_interval: Annotated[int, Field(ge=1, le=86400)]


class PageQuery(StrictDTO):
    # Query text is parsed by FastAPI; bounds remain explicit and unknown keys fail.
    model_config = ConfigDict(extra='forbid', strict=False)
    limit: Annotated[int, Field(ge=1, le=200)] = 50
    offset: Annotated[int, Field(ge=0, le=100000)] = 0


class ApprovalPreviewQuery(StrictDTO):
    model_config = ConfigDict(extra='forbid', strict=False)
    envelope_ref: Identifier
    expected_revision: Revision


class ApprovalPreviewView(StrictDTO):
    strategy_id: Identifier
    strategy_version: Identifier
    strategy_content_hash: Hash
    registry_revision: Revision
    namespace: Literal['FIXTURE','LOCAL_RESEARCH']
    envelope_ref: Identifier
    envelope_hash: Hash
    envelope: dict[str, JsonValue]
    release: dict[str, JsonValue]
    risk_policy: dict[str, JsonValue]
    risk_policy_hash: Hash
    product_assessment: dict[str, JsonValue]
    product_assessment_hash: Hash
    evidence_ref: str
    observed_at: str
    financial_confirmation_available: bool
    reason_codes: list[str]


class ViewMetadata(StrictDTO):
    source: str
    observed_at: str
    as_of: str | None
    freshness: Literal['CURRENT', 'STALE', 'UNKNOWN', 'NOT_CONFIGURED']
    current_or_last_known: Literal['CURRENT', 'LAST_KNOWN_GOOD', 'UNAVAILABLE']
    implementation_hash: Hash
    executable_revision: str | None
    worktree: Literal['CLEAN', 'DIRTY', 'UNAVAILABLE']
    config_hash: Hash
    config_generation: int
    namespace: Literal['FIXTURE', 'LOCAL_RESEARCH']


class OverviewView(StrictDTO):
    mode: Literal['RESEARCH', 'PAPER_FIXTURE', 'PAPER_REAL_TIME', 'LIVE']
    live_authorized: bool
    queued_jobs: int | None
    running_jobs: int | None
    scan_revision: Revision | None = None
    lifecycle_counts: dict[str, int] | None
    exposure_quantity: str | None
    realized_pnl_usdt: str | None
    unrealized_pnl_usdt: str | None
    runtime_status: str
    cloud_status: str
    reason_codes: list[str]


class HealthView(StrictDTO):
    control: str
    research: str
    runtime: str
    storage: str
    cloud: str
    market: str
    provider: str
    live_authorized: bool
    provider_requests: int
    runtime_llm_calls: int
    reason_codes: list[str]


class SettingsView(StrictDTO):
    revision: int
    config_generation: int
    display_timezone: Literal['UTC', 'Asia/Taipei']
    scan_interval: int
    local_data_root: str
    cloud_root: str | None
    database_path: str
    control_api_host: str
    control_api_port: int
    diagnostic_only: bool
    paper_runtime_enabled: bool


class PageView(StrictDTO):
    items: list[JsonValue]
    limit: int
    offset: int
    total: int | None
    status: str
    reason_codes: list[str]


class OwnerObjectView(StrictDTO):
    status: str
    revision: int | None
    contract: str | None
    payload: dict[str, JsonValue] | None
    reason_codes: list[str]


class TradingView(StrictDTO):
    mode: str
    status: str
    broker_observed_at: str | None
    position: dict[str, JsonValue] | None
    protection: dict[str, JsonValue] | None
    reconciliation: str
    realized_pnl_usdt: str | None
    unrealized_pnl_usdt: str | None
    reason_codes: list[str]


class CapabilitiesView(StrictDTO):
    snapshot_hash: Hash
    snapshot: dict[str, JsonValue]


class CommandReceipt(StrictDTO):
    command_id: Identifier
    actor: Identifier
    resource: str
    expected_revision: int
    resource_revision: int
    status: Literal['COMPLETE', 'QUEUED', 'PAUSED']
    effect_ref: str | None
    reason_codes: list[str]
    observed_at: str


class ErrorDetail(StrictDTO):
    category: Literal['INVALID_INPUT', 'INCOMPLETE_SYNC', 'CONFLICT', 'INSUFFICIENT_EVIDENCE', 'POLICY_FAIL',
                      'NOT_CONFIGURED', 'AUTHORIZATION_REQUIRED', 'UNAVAILABLE', 'INTERNAL_ERROR']
    reason_codes: list[str]
    correlation_id: str


class ErrorResponse(StrictDTO):
    error: ErrorDetail


T = TypeVar('T')
class ViewEnvelope(StrictDTO, Generic[T]):
    metadata: ViewMetadata
    data: T
