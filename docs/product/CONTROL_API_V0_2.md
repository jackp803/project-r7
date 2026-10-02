# Local Control API v0.2

The actual contract is `contracts/control_api_v0_2.openapi.json`. Regenerate it with `python tools/export_control_openapi.py --scratch-root <project-artifacts> --output contracts/control_api_v0_2.openapi.json`. The API drift test compares it with the actual app. Source uses FastAPI with strict DTOs and bounded JSON; no remote documentation/CDN, telemetry exporter or runtime LLM is configured.

## Local authentication

Composition supplies `ProductConfig`, separate local authentication/command stores and trusted owner service factories. All stores stay inside the configured local data root. The default is loopback HTTP, accessed remotely only through an operator-established SSH tunnel. Forwarded headers cannot establish a local principal. Direct LAN/TLS commissioning is unavailable.

First enrollment is a trusted local operation, `LocalAuth.create_owner`, with a chosen password; it is never an HTTP endpoint. Native first-run CLI wiring follows in S13. There is no default password. Passwords use independently salted Argon2id hashes. Session/CSRF tokens are random and persisted only as hashes. Authentication material is excluded from command history, reports and cloud outbox.

Login includes a fresh command ID and initial revision zero. A successful login ID cannot mint another session. The opaque session is an HttpOnly/SameSite=strict cookie; the session-bound CSRF proof is returned at login and in a SameSite cookie for browser reload. Writes require the exact allowed Host and Origin plus the CSRF header. Sessions expire, revoke on logout and reject backwards clocks. Failed logins are durably throttled. Expired/revoked reauthentication cannot mint or reuse an E6 human principal.

Authentication commands use session revisions. Product commands use resource revisions. API revisions are bounded to JavaScript safe integers. Financial approval additionally requires fresh server-issued reauthentication, exact strategy/version/content hash, a locally registered immutable envelope and the actual E6 guards. FIXTURE HTTP sessions cannot approve or activate real financial operations. Activation remains uncommissioned.

## Commands and recovery

Each product command binds ID, operation, resource, authenticated actor, expected revision and exact DTO content. Identical completed retries return the immutable original receipt. Changed content/actor/subject or stale revisions conflict. A short lease reserves the resource before effects; the owner runs outside the command store's write transaction and enforces its own CAS/idempotency.

An uncertain owner response remains PREPARED. Retry the same command ID and body after its lease expires; the actual owner reconciles its original effect. Do not replace the ID to infer that nothing happened. Old lease generations cannot overwrite a recovered receipt. HTTP202 means QUEUED, never computation complete. Errors carry stable categories/reasons and sanitized correlation IDs.

Research enqueue freezes selected local configuration, verified intake, strategy and implementation hashes, then persists a job. A separate worker calls the actual ResearchService. Cancellation is cooperative and retains completed stages/consumed OOS. Missing or changed selected configuration blocks work before replay. No request supplies code, filesystem roots, SQL or executable evidence PASS.

PAPER start calls actual E6/PaperService; acceptance alone does not attach a runtime. Pause durably denies new entry admission without creating another process generation. The existing protective worker consumes the request and retains management. An already admitted/in-flight broker effect can still require reconciliation; pause is no assertion of flatness or cancellation of protection. Browser reads never attach or take over a runtime.

## Views and known commissioning gaps

Views carry source, observation/as-of clocks, freshness, namespace and exact code/config identities. PAPER uses persisted broker time and a last-known label until current worker health is supplied. Metrics come from published E5 trade results and the existing E3 calculation; fill-price slippage is not subtracted again. Unavailable metrics are null, unknown exposure remains unknown, and missing owners return NOT_CONFIGURED. Dataset listing proves configured manifest inventory only; it does not claim a successful decode or research result.

Default first run has no enrolled owner, remote cloud, selected real dataset/policies, active market feed or provider authority. Global trading and alerts remain unconfigured until those actual owner projections are composed. Native process supervision, unattended worker/runtime composition and current production admission belong to S12/S13. Accelerated fixtures do not qualify real forward duration or native Ubuntu packaging.
