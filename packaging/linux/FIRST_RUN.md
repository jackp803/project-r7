# Ubuntu first run and native qualification

Target: Ubuntu 24.04/26.04 x86-64. Neither target is qualified yet. The prepared wheel lock is not a native build. Produce and verify the exact native package on an authorized Ubuntu host first; preserve its OS/glibc/interpreter/source/build identities and licenses.

Keep installation, owner configuration, local data and optional cloud staging disjoint. Use an unprivileged account and a supported local filesystem for SQLite. Never place the data root on a cloud mount, share or installation directory.

After verifying the native package's checksums, run the bundled executable from a normal terminal:

```sh
./r7 doctor --hardware --data-root /srv/r7/data --json
./r7 init-profile --config /srv/r7/config/product.json --data-root /srv/r7/data --instance-id selected-local-instance
./r7 enroll-owner --config /srv/r7/config/product.json --username selected-local-owner
./r7 serve --config /srv/r7/config/product.json
```

Create the indicated parent directories with permissions for the selected owner before initialization. Enrollment requests hidden local password input. First run binds loopback, diagnostic mode and PAPER disabled; market/provider/cloud are unconfigured. Normal product execution uses neither Python/Node nor PYTHONPATH.

Select actual owner-compatible datasets and local research policies before starting the separately supervised `research-worker --config <profile>` process. Cloud OAuth and rclone commissioning belong to an explicitly selected test root and operator-controlled private configuration outside the data/feedback tree. Never copy OAuth credentials or active SQLite into cloud staging.

For maintenance, stop all owner processes and use `backup-product-data`, `verify-product-backup`, then `restore-product-data` into a fresh private generation. The original profile/data remain preserved. Restore requires a new login, reconciliation and explicit fresh authorization; a process restart cannot resume exposure. Database-only recovery is explicitly incomplete for datasets/policies/snapshots.

Service installation, sandbox/boot/reboot and SSH-tunnel qualification are pending delivery work. No system service, firewall rule, OS, Python package or provider connection is installed automatically by this guide. Keep native acceptance and deployment-machine commissioning separate from code preparation.
