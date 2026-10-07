# Native Ubuntu control and research service increment

This implementation exports guarded control/research units. It does not install
or start systemd services. S13 remains in progress: native Ubuntu installation,
uninstallation, kernel enforcement, restart/reboot and SSH commissioning require
separate implementation and actual target evidence. Continuous trading runtime
composition is still an explicit S12 dependency; no inert runtime unit is emitted.

`r7 plan-services` requires a native Ubuntu 24.04/26.04 x86-64 executable, exact
revision/build/config commitments, measured physical memory, and an existing
dedicated unprivileged R7 identity. The installed files must be root-owned,
protected and readable/executable by that identity. Configuration must be
root-owned, readable through the dedicated group and inaccessible to other users.
Binary/configuration/private data/optional local cloud staging roots are disjoint.
Private writable roots require exact owner/group and owner read/write/traversal.
Original configuration paths are inspected before normalized roots can hide links.

`r7 guarded-service --role control|research` repeats these checks under the exact
service identity before opening owner stores. It rejects source execution,
Windows, unsupported targets, changed subject/hardware, multiple workers,
non-loopback API binding and invalid restoration state. It composes the existing
control/research owners. Research transfers the configuration commitment into its
actual native child argv and checks it before constructing `LocalOwners`.

Generated units use direct literal argv, explicit writable paths, bounded restart
backoff/start limits, unprivileged users, a restrictive filesystem sandbox and
owned control-group shutdown. Research has one-worker resource limits calculated
from measured memory; CPUQuota=100% means one CPU. Rendering proves configuration
bytes only; it does not prove that a Linux kernel enforces those settings.

The shared host lock root is `/run/r7/scopes`, also used by actual POSIX process
scope locks. It must already exist with the dedicated owner, group and mode 0700.
The export includes `r7-scopes.conf` for explicit operator provisioning. Its
creation-only mode/user/group fields preserve existing inode facts; startup must
reject mismatches instead of boot-time normalization masking them. Refuse an
existing owner mismatch before installation. Service shutdown never deletes lock
files or inodes. Do not replace the root with per-profile locks or use automatic
RuntimeDirectory cleanup/chown to bypass this boundary.

Exports use a fresh private destination outside all protected roots, write two
units and the scope rule, then write the complete manifest last. They perform no
systemctl, account, installation, database migration or financial action.

The adjacent Windows asset fix rejects UI roots, ancestors and descendants that
are symlinks or reparse points. Actual root/nested junction regressions preserve
their target bytes. It closes a build-root escape before mounting static files.

Development verification: 36 service tests and 3 asset-link tests pass, with
fail-first evidence for ordinary defects. Existing native entrypoints (10),
process supervision/locks (17), research worker (11) and product assets (3) pass.
Independent read-only source/assertion review has no remaining Critical/Important
findings within this bounded increment. Linux permission facts in unit tests are
controlled mocks; these are not Ubuntu or systemd acceptance.

A new exact-clean source/native/browser qualification is required before this
increment can replace the previously accepted Windows recovery executable.

Creation-only tmpfiles syntax was checked against the
[upstream systemd v255 manual](https://raw.githubusercontent.com/systemd/systemd/v255/man/tmpfiles.d.xml).
This source check does not substitute for installed-version native acceptance.
