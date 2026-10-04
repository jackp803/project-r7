# Local native research composition

The native/source control process composes the existing E6 registry, sealed
intake ledger, ResearchRequestResolver and ResearchQueue. Long research work runs
in a separate owned process using the actual ResearchService. No second strategy,
risk, lifecycle or replay implementation is introduced.

Operator-selected non-secret settings live in local_data_root/owner-selections.json,
outside cloud staging and the frozen installation. The exact envelope has:

```json
{
  "schema_version": "r7-owner-selections-v0.2",
  "cloud_root_id": null,
  "research_policies": {}
}
```

An absent file or empty policies leaves research NOT_CONFIGURED. A non-null
cloud_root_id additionally requires an explicit disjoint configured cloud_root;
the existing transport verifies its marker on discovery. This local staging setup
does not certify a real cloud connection or remote acknowledgment.

Each selected policy uses the existing ResearchRequestResolver's exact fields:
dataset_ref, split_policy_ref, cost_policy_ref, research_policy_ref,
robustness_policy_ref, risk_policy_ref, family_id, seed,
requested_dataset_profile, requested_validation_profile and
requested_robustness_profile. References remain bounded local relative paths.
They must match the accepted package's requested profiles and actual selected
file hashes. Package/HTTP data cannot supply this file, executable commands,
provider credentials or arbitrary replay arguments. No financial defaults are
generated. Policy or source drift blocks queued work.

Start research supervision separately:

```text
r7 research-worker --config <absolute-local-config>
r7 research-worker --config <absolute-local-config> --once
```

Each admitted job is claimed transactionally, executed through the owned process
bootstrap/Job Object or process group, and checked through the same actual queue
generation. Research children inherit below-normal priority on Windows and the
existing lower priority/process group on Linux. Admission uses measured memory
and disk availability; Windows memory enforcement remains SOFT_LIMIT_ONLY.
The parent never performs heavy E2/E3 replay. Fixture executable overrides are
restricted to trusted explicit FIXTURE verification and have no CLI switch.

Timeout/crash disposition requires an actual reaped owned process and exact
job/owner/generation. It cannot overwrite a successor claim, renew an expired
lease, erase sealed holdout observations or grant financial permission. A zero
exit code without actual owner publication is FAILED, not completed research.
Cancellation preserves the existing queue/owner cooperative checkpoint semantics.
Worker logs stay in the configured local data root and are not cloud feedback.

The private _research-job command is the trusted local worker bootstrap, not an
HTTP control or trading capability. Public startup always uses LOCAL_RESEARCH.
PAPER, runtime, provider credentials and capital remain separate unconfigured
owners. Process exclusivity, supervisor heartbeat/service restart and backup
generation recovery are remaining S13 work; this document does not claim them.

Platform reference: [Microsoft CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)
documents inherited below-normal priority. Actual native worker/Linux qualification
must be recorded separately; source tests and reference documentation are not a
native/platform PASS.
