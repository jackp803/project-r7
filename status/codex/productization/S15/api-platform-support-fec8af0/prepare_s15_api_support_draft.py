"""Three bounded API source selections; no API/network acceptance issuance."""
from pathlib import Path
import json
base=Path(__file__).resolve().parent
def select(source,*methods):return [[source,method] for method in methods]
api='tests/product/test_api_authority.py';csrf='tests/product/test_api_csrf.py'
commands='tests/product/test_control_commands.py';approval='tests/product/test_api_approval_binding.py'
rows=[dict(id='API-01',supported_behavior='Actual ASGI FIXTURE API rejects actor/PASS injection, bounded-page SQL/unknown query input, and unknown command fields in strict committed OpenAPI schemas. Durable settings use CAS and identical retry; changed request conflicts. Separate actual command ledger retains completed receipts across revision changes, rejects changed actor/subject/revision, fences pending effects and recovers expired claims without accepting old completion.',
    selectors=select(api,'test_actor_and_executable_evidence_cannot_be_injected',
        'test_page_bounds_and_unknown_query_fields_are_enforced','test_openapi_has_all_required_routes_and_strict_command_schemas',
        'test_settings_are_actual_durable_cas_commands_with_identical_retry')+
      select(commands,'test_completed_retry_returns_identical_historical_receipt_after_revision_changes',
        'test_changed_request_actor_subject_or_expected_revision_conflicts_under_same_id',
        'test_pending_effect_fences_other_commands_without_holding_sql_transaction',
        'test_expired_crash_claim_reuses_same_owner_command_and_fences_old_completion'),
    remaining=['Source ASGI/SQLite mechanics, not ordinary native worker API or full command surface/whole-product acceptance.']),
  dict(id='API-02',supported_behavior='Actual ASGI FIXTURE rejects DNS rebinding/wrong or missing Origin, cross-site reads/forwarded Host bypass, missing or wrong CSRF, invalid content types and duplicate/nonfinite/oversized JSON. Authenticated responses have no wildcard CORS and required security headers. Login returns opaque HttpOnly/SameSite cookie without password/token echo; logout/expiry denies subsequent session reads. Separate actual E6 FIXTURE approval stores the verified local session actor; logout revokes its capability before approval effect.',
    selectors=select(csrf,'test_dns_rebinding_and_wrong_origin_cannot_login',
        'test_cross_site_get_and_forwarded_headers_cannot_bypass_loopback_rules',
        'test_product_write_requires_matching_csrf_even_with_valid_session',
        'test_form_and_missing_content_type_cannot_bypass_strict_json',
        'test_duplicate_json_keys_nonfinite_and_oversize_body_are_rejected',
        'test_no_wildcard_cors_and_security_headers_on_authenticated_response')+
      select(api,'test_login_sets_opaque_http_only_same_site_cookie_without_password_echo',
        'test_expired_session_cannot_read_or_write_and_logout_revokes_cookie')+
      select(approval,'test_actual_e6_approval_actor_is_verified_local_session_identity',
        'test_logout_revokes_actual_e6_capability_before_any_owner_approval_effect'),
    remaining=['Public fixture passwords/session/human identity only. E6 FIXTURE mechanics and stored APPROVED label confer no real financial authority; production/native and whole-product acceptance remain pending.']),
  dict(id='API-03',supported_behavior='SSH planner emits exact loopback-only forwarding argv without remote command or connection and binds destination/port deterministically. Product config rejects0.0.0.0 host; actual ASGI rejects forwarded hostile Host and cross-site read. These are local source planner/config/security assertions.',
    selectors=select('tests/application/test_ssh_access.py','test_exact_loopback_forward_has_no_remote_command_or_connection',
        'test_deterministic_plan_binds_destination_and_exact_port')+
      select('tests/application/test_platform.py','test_rejects_relative_paths_bad_resources_unknown_and_secret_fields')+
      select(csrf,'test_cross_site_get_and_forwarded_headers_cannot_bypass_loopback_rules'),
    remaining=['No real SSH connection or remote view was started. Native controlled loopback probes remain separate evidence; real SSH/network commissioning and Ubuntu tests NOT_RUN.'])]
policy=dict(document_kind='MANUALLY_CURATED_SCOPED_SOURCE_SUPPORT_DRAFT;NOT_REQUIREMENT_ACCEPTANCE',
    candidate_revision='fec8af0f70d787deea720b1e7f952c4fca9487b5',scope='API01-03;WINDOWS_SOURCE_SUPPORT_ONLY',requirements=rows,
    common_limits=['Original1953-case exact-clean source qualification only; no new per-result21-field acceptance execution.',
      'Repeated source references deduplicated; no new real session enrollment, credentials or external connection.',
      'Normal native/runtime/Ubuntu/whole-product requirement acceptance remains pending; requirementPASS0.'])
target=base/'S15-api-support-selection-fec8af0.json';assert not target.exists()
target.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
source=(base/'build_s15_strategy_support_draft.py').read_text(encoding='utf-8')
source=source.replace('S15-strategy-support-selection','S15-api-support-selection').replace('S15-strategy-support-draft','S15-api-support-draft')
source=source.replace("[f'STR-{number:02d}' for number in range(1,9)]","[f'API-{number:02d}' for number in range(1,4)]")
source=source.replace('selected_requirement_drafts=8','selected_requirement_drafts=3').replace('unselected_v02_requirements=58','unselected_v02_requirements=63')
builder=base/'build_s15_api_support_draft.py';assert not builder.exists();builder.write_text(source,encoding='utf-8',newline='\n')
print('Prepared three API partial source support rows; requirementPASS0.')
