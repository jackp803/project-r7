# Private database backup implementation plan

> For agentic workers: use `superpowers:executing-plans` inline in the existing worktree. Continue the authorized master task after this bounded component; no new task or milestone-only stop.

Goal: produce and verify a versioned, owner-private local SQLite backup without copying active database/WAL files or granting any runtime authority.

Architecture: acquire the configured native control/research and reserved runtime process scopes, then hold short bounded SQLite write reservations on every existing allowlisted database. Separate read-only SQLite connections use `Connection.backup()` while those reservations remain held. The manifest is published last, after all destination databases pass integrity checking and hashing. Canonical database content and schemas are not modified by backup.

Spec: `docs/product/v0_2/01_PLATFORM_DEPLOYMENT.md` PLAT-03/09 and `06_EXECUTION_PLAN.md` S13. Python 3.12 remains the selected minor; no new dependencies, network/provider calls, credentials, cloud publication or destructive cleanup.

Scope: consistent database snapshots for the current native control/research composition. This component is not a whole-data-root backup, restoration, migration, upgrade, pending-position management handoff, or qualification of an installed runtime/systemd service. These remain subsequent S12/S13 work. Arbitrary tools that bypass configured ownership are outside the supervised product model; all present databases are additionally fenced against ordinary SQLite writers. New unexpected database inventory or configuration drift causes failure, never a ready manifest.

Files:

- `src/application/platform/private_files.py`: create a fresh local owner-private directory; POSIX 0700 or a protected Windows DACL for the creating user. Reject links/reparse ancestors and existing targets.
- `src/application/platform/backup.py`: `create_database_backup(config, destination, *, config_path=None, timeout_seconds=30)` and `verify_database_backup(config, destination)`. Fixed inventory contains canonical, intake, queue, research, control-command, local-auth and supervision stores. Artifact filenames are fixed logical IDs; manifest records source relative paths, schema and byte hashes, versions, absent stores, config/provenance, and PRIVATE_LOCAL / cloud FORBIDDEN classification.
- `tests/application/test_database_backup.py`: actual SQLite/WAL, process-scope exclusion, write contention, corruption, preservation, cloud/path restrictions, manifest validation and real filesystem permission tests.
- `src/application/cli.py`: trusted local `backup-databases` / `verify-database-backup` commands with sanitized output; no HTTP backup endpoint.
- `docs/product/PRIVATE_DATABASE_BACKUP_V0_2.md`: exact scope, commands, private data handling, timeout/failure behavior and restoration gaps.

Review focus: committed WAL content is included; uncommitted writes cannot leak; contention cannot hang indefinitely; a corrupt/partial artifact cannot be ready; local session/password hashes never enter cloud feedback. Backup manifests are untrusted on read: exact keys/types, fixed filenames, bounded size, unique logical IDs, hashes, schema/integrity and private permissions are checked.

## Task 1: snapshot and verifier

- [x] Write actual integration tests; observe the intended missing-feature failure.
- [x] Implement private destination creation and bounded SQLite backup under owned scopes/write reservations.
- [x] Implement read-only strict verification and no-overwrite behavior. Preserve failure artifacts without a ready manifest.
- [x] Pass the new tests and existing supervision/native/CLI/application regressions: 158 source application tests, including 15 new snapshot cases. Whole-source and frozen acceptance remain Task 2.

## Task 2: local commands and qualification

- [x] Write actual CLI success/rejection tests before adding the command.
- [x] Add commands and documentation; source/provenance and financial authority remain distinct.
- [ ] Commit the candidate, run exact-clean complete source qualification and fresh native snapshot/verification smoke, retain sanitized evidence, verify Git blob hashes and push the existing bounded branch.
- [ ] Continue restore generation/fencing, S12 runtime, service/SSH and S14-S16. Ubuntu targets remain NOT_RUN until actually attached and tested.
