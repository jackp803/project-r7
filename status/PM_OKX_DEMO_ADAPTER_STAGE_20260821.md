# PM Stage Record — OKX Demo Adapter Construction

- date: `2026-08-21`
- prior accepted merge: PR #11 / `9679a224da3764ecbab7161e6c6f256ca46aecf7`
- next task: `E4-20260821-008`
- next branch: `agent/e4-okx-demo-adapter-20260821`
- executable verification: `NOT_RUN`
- release gates: `A/B/C/D BLOCKED`

E7 accepted the E4 canonical entry translation and deterministic OKX sizing layer at static/source level and classified the 300-second metadata freshness policy as non-blocking for PR #11, with hardening required before future Demo/private adapter acceptance.

The next stage is source construction only for a Demo-first OKX provider adapter. No Demo order is authorized from GitHub; no real-money/live path is authorized. The adapter must enforce Demo mode, preserve fail-closed reconciliation/idempotency, validate account/position prerequisites instead of silently mutating them, address metadata freshness hardening, and expose no asset-movement capability.
