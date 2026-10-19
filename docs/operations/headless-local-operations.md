# One headless local product launcher

Task CODEX-R7-PRODUCTIZATION-MASTER-20261002. This entrypoint does not install a
Windows startup item, system service, sleep exception or security change.
Run it from the installed package after first setup. It needs no open Chat,
Codex session or browser. A browser is optional for the loopback Control Center.

Keep `config.json` and this explicit machine-local `operations.json` outside
the installation, cloud staging **and** portable product data. Sample for an
already configured diagnostic research profile:

```json
{
  "schema_version": "r7-local-operations-v0.2",
  "workflow_authorized": true,
  "actor": "local-operator",
  "roles": ["control", "research"],
  "scan_inbox": true,
  "research_policy_ids": ["engineering-development-only"],
  "queue_reports": true,
  "interval_seconds": 30,
  "restart_budget": 2,
  "restart_backoff_seconds": 5
}
```

The policy ID must already exist in the normal `configure-research` selection.
No financial, promotion or risk defaults are selected by this operations file.
Replace the actor and selections consciously. Set scan/report switches false
and use an empty research policy list when these operations are not wanted.

```powershell
R7.exe run-product --config C:\R7\config.json --operations-profile C:\R7\operations.json
R7.exe product-status --config C:\R7\config.json
R7.exe stop-product --config C:\R7\config.json --role coordinator
```

The first command runs continuously. The stop command can be run from another
terminal. It requests cooperative stops only for actual child incarnations
belonging to this coordinator's kernel process scopes, then checks reaping.
Forced cleanup is disclosed separately. Stop does not assert flat exposure.
Already running externally owned workers stay externally owned and are not
stopped. Repeated coordinator launch is denied by the existing process lock.

The coordinator uses the existing independent research worker, intake ledger,
revision checks, immutable job identities and durable feedback outbox. It does
not synthesize research results or human authentication. Feedback performance
sharing stays off. Remote publication remains separately configured cloud work;
a queued local report is not a remote acknowledgment.

`runtime` may be added to roles only after ordinary Paper setup and complete
native software qualification. The actual Paper child retains all selection,
financial policy, E6 consent, restore, currentness and reconciliation gates.
The coordinator never issues PaperStart or approval. Changed config at child
handoff is denied before composition; changed operations stop this coordinator.
Long-lived service children have no research job timeout; research jobs keep
their finite timeout and lower scheduling priority. Memory enforcement remains
SOFT_LIMIT_ONLY; measured capacity is a separate native qualification item.

Unexpected exits receive bounded retries with the selected backoff and budget.
After a coordinator crash, its owned kernel groups are closed; run the same
command to start a new coordinator generation and recover existing product
state through the original owners. Automatic host-boot recovery would require
a separately approved startup registration, which this command does not create.
Private diagnostics are under the product data's `worker-logs` directory.

After moving or restoring data, do not copy old machine authority. Restored
data remains inhibited; select and authorize local operation on the new machine
only after its own qualification. Recreate this machine-local operations file.
`--maximum-cycles` is a bounded verification aid; omit it for daily operation.

Scope: source integration and native acceptance are reported independently.
The presence of this command does not certify ordinary Paper eligibility,
market connectivity, enough real-time samples, old target hardware or Ubuntu.

## Explicit ordinary Paper public market setup

After ordinary software qualification and the separately selected research,
simulation, promotion and risk policies, save this local operator selection
outside the installation and cloud. Stop all product owners before configuring:

```json
{
  "schema_version": "r7-public-market-v0.2",
  "namespace": "LOCAL_RESEARCH",
  "provider": "OKX_PUBLIC",
  "symbol": "BTC_USDT_PERP",
  "source_kind": "PUBLIC_MARKET",
  "read_only": true,
  "workflow_authorized": true,
  "poll_interval_seconds": 5
}
```

```powershell
R7.exe configure-market-data --config C:\R7\config.json --selection-profile C:\R7\market-selection.json
```

This immutable selection permits keyless public reads; it neither grants
PaperStart nor replaces qualification or financial policy selection. Add the
already configured `runtime` role to the existing operations file and use the
same `run-product` launcher. Only actual attached ordinary E6 runs request data.
Absent selection or no accepted run means no public request. FIXTURE retains
its synthetic source and cannot subscribe to public market data.

The independent owned acquisition child uses fixed GET-only BTC ticker and
historical candle endpoints, no account, trading, transfer, keys or environment
proxy. It normalizes finalized E1 history with documented base BTC volume and
fetches an actual ticker after warmup. Gaps, unconfirmed data, stale/future quotes,
malformed fields and changed runtime/E6 identities deny event ingestion. Receipt
times are actual times; persisted candle identities are never restamped. These
reads run outside protective management; canceled or unreaped children cannot
silently become a successful observation or restart over an unconfirmed tree.

Public request/response counters appear in the worker's final structured log.
They are separate from zero-call offline qualification. Interrupted accounting
is explicitly INCOMPLETE with null totals and known completed-batch counts;
prepared receipts alone do not prove dispatch. Private raw attempts are under
`data/public-market-observations/<runtime-token>/`. This transient diagnostic
tree is excluded from product backups; selection and actual durable financial
journals remain included. Backup/restore reports the exclusion and restoration
still inhibits execution. Archive raw diagnostics separately when required.

Acquisition refuses new batches after 86,400 retained attempts or 1 GiB per
runtime generation; it never deletes old evidence. Local capture archival and
storage monitoring are operational requirements for continuous use. Protection
continues independently, and existing freshness gates reject old market data.
This bounded local retention is not an infinite-duration capacity claim.

Source integration tests use controlled HTTP and no real provider requests.
Installed/native integration, actual host capacity and complete PQR remain
separate acceptance work. Do not start real-time forward observation until
ordinary software, actual market inputs and formal local policies are all
qualified and consciously selected. Insufficient samples remain unfinished.
