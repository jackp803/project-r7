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
