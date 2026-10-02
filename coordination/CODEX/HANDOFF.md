# CODEX-R7-PRODUCTIZATION-MASTER-20261002

Spec: r7-product-v0.2 at `9fd277798b1c51d1bc79b29a61bec81b552efeb1`.
Branch: `codex/r7-productization-master-20261002`.

No existing master implementation was present. All prior LF/P0 worktrees and
evidence were preserved and relocated under the user's project folder; worktree
backlinks, revisions and working contents were verified. New work/artifacts must
also stay under that project folder, never the desktop root.

Active step: S01, portable configuration/resource/process foundation. Next: S02.
Read PROGRESS.json and the v0.2 execution plan before resuming. Preserve the
same branch/task and continue S01-S16 / M1-M11 automatically. Do not treat this
startup checkpoint as milestone completion.

Actual local environment: Windows 11 x86-64 build 26200, Python 3.14.3 source
interpreter, Node 24.19.0. Current hardware has 20 logical cores and approximately
32 GiB memory; it does not qualify the separately reported older 24 GB Ubuntu
machine. WSL reports no installed environment. Ubuntu qualification is NOT_RUN.

S01 source implementation now exists: strict non-secret configuration, local
database/cloud root checks, measured hardware doctor, conservative research
admission, Windows Job Object / Linux process-group ownership and bounded
termination, and an inventory-aware local qualification runner. Initial TDD
failures were observed; all 19 new application tests now pass on Windows with
zero failure/error/skip. Actual automatic timeout and unrelated-process survival
are tested. Memory enforcement remains SOFT_LIMIT_ONLY.

The first clean qualification failed in the application suite because job
accounting zero preceded descendant exit. Remediation now waits on stable
owned process handles and covers repr-escaped path redaction. Preserve this
failed evidence; never transplant its earlier passes to the repaired candidate.

Next action: qualify the new exact clean revision
with the complete legacy focused sequence and all inventory directories, persist
sanitized evidence in a separate commit, then advance to S02. Product Python
minor is selected as 3.12; current 3.14.3 source results do not certify frozen
3.12 packages. Build/dependency locks remain pending native verification.
Use canonical packages and preserve every legacy LF/FP test. Keep code/evidence
revisions separate at each clean qualification.

All v0.2 specifications/authorizations were read. Prior v0.1 provisions are
consumed only where not superseded; read relevant owner implementations and
remaining detailed legacy acceptance sections before their owning packages.
No real cloud/private provider/credentials/capital/hosted compute is authorized.

Antigravity's guard refused this untrusted workspace before advisory dispatch.
Continue locally without adding trust, paid fallback, or a second Codex runner.
