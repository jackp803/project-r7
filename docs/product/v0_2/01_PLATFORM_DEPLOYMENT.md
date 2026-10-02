# R7 v0.2 platform and deployment specification

Spec state: required behavior, not a portability/benchmark PASS.
Authority: `00_EXECUTION_BASELINE.md`.

## PLAT-01 Supported targets

Required release targets: Windows 11 x86-64 desktop and Ubuntu Server 24.04 LTS / 26.04 LTS x86-64. Ubuntu Desktop may use the same headless backend and browser UI. Other distributions, ARM, 32-bit, Wine and Windows 10 are not claimed qualified by this release. Existing supported Windows development installations may still run source tests, labeled with their actual OS.

One Python domain codebase and one static UI build. Select and pin a supported common CPython minor (3.12 is the initial baseline), all Python/JavaScript dependencies and build tools. Resolve platform wheels and licenses before freezing the build lock. Do not require a GPU, GPU driver, CUDA, ROCm or Node runtime on the installed product. Publish exact interpreter/build versions in each package's provenance.

Existing Windows evidence does not certify Linux. WSL2 or an Ubuntu VM may provide local development evidence, explicitly labeled. Full boot/service/reboot qualification requires systemd functioning in that environment; a mocked `systemctl` call or ordinary container is not such evidence. Final deployment-machine suitability remains a separately labeled smoke/soak result.

## PLAT-02 Portable core

Use pathlib and explicit UTF-8/newline handling; never embed user-specific drive letters or assume the shell/current directory. Use timezone-aware UTC values and monotonic elapsed time for process deadlines. Locale must not change JSON, Decimal, timestamp or CSV interpretation. Test Chinese/spaced paths and case-sensitive Linux filesystems.

Use argv process invocation with `shell=False`. Platform-specific service/process-tree code belongs in `application/platform/`, not E1-E6. Spawn-safe workers must operate on both platforms. Parent timeout/cancel must terminate owned child processes and reap them; test a grandchild process, not only the direct child. Never kill unrelated processes by name. Linux uses owned process groups and systemd control groups; Windows uses Job Objects or a verified equivalent process-tree mechanism.

## PLAT-03 Processes and databases

Ship separately supervised processes for control/API, research workers and trading runtime. The trading process never waits on a backtest, Monte Carlo, cloud upload or chart render. UI reads bounded projections with pagination. IPC uses versioned bounded messages with correlation IDs and backpressure, never arbitrary Python pickle from external clients.

E6 remains the canonical store owner. SQLite stays on a local supported filesystem, not cloud sync/FUSE/SMB/NFS. Keep transactions short; configure busy timeouts; journal mode and durability settings must be tested. Application job/outbox tables may have their own database to prevent long research writes blocking the trade journal. There is still only one canonical strategy lifecycle store. Coordinate cross-database actions with idempotency keys and transactional outboxes, not an imaginary distributed transaction.

The supervisor prevents a second trading writer for the same configured provider/account/instrument scope. V0.2 is single-host/single-trading-writer. A second machine must not start LIVE against the same scope; process startup requires a locally provisioned exclusive deployment identity. No claim of multi-host fencing is permitted without a real separate design.

## PLAT-04 Older-computer resource profile

User input: 24 GB RAM, GPU exists, all other specifications unknown. This is a design target, not measured capacity. `r7 doctor --hardware` shall show CPU model/logical cores, measured memory, architecture, disk free space, filesystem, OS and optional GPU inventory without requiring GPU activation. Never print credential/environment contents.

Initial conservative engineering settings, not financial limits:
- research workers = 1; operator may raise after the benchmark.
- research aggregate memory soft budget = min(8 GiB, 40% of measured physical memory).
- do not start another research job if available memory is below max(2 GiB, 15% of physical memory).
- chunk dataset scans and Monte Carlo batches; bound caches and never copy the complete dataset into every worker unnecessarily.
- one active trading runtime; research process priority below trading/control.
- pause admission of research work on memory pressure or disk free space below max(2 GiB, 5% of the data volume).
- low disk space in the canonical trade journal causes a fail-closed operational alert and blocks new exposure; do not delete audit rows to recover automatically.

Linux research service must expose tested CPUQuota, MemoryHigh and MemoryMax configuration. CPUQuota is expressed relative to one CPU (100% = one CPU), not a misleading percentage of the whole machine. Windows uses verified process resource controls; where a hard cap is unavailable, show SOFT_LIMIT_ONLY, bound worker count and memory admission, and do not claim kernel enforcement.

Benchmark on the actual machine: representative 4h/1h jobs, a paginated 1m dataset, bounded Monte Carlo and simultaneous PAPER health probes. Record input counts, algorithms, wall time, peak RSS, CPU, page faults, disk use and API/heartbeat latency. No forecast of jobs/hour is accepted as a benchmark. GPU acceleration is deferred and must never block core delivery.

## PLAT-05 Ubuntu cloud bridge

Google's desktop sync application is not assumed to exist on Linux. Deliver a supported Ubuntu synchronization path, not merely an abstract folder adapter.

Required transport base: `SyncedFolderCloudTransport`. Provide an operator-configured rclone bridge that feeds an ordinary local staging directory:
- cloud inbox/dataset references -> local inbox staging: read/copy only;
- finalized local result outbox -> cloud result paths: copy only;
- separate author-owned and runtime-owned namespaces;
- no destructive `sync`, `bisync`, automatic delete/dedupe, whole-drive mirroring or remote shell expressions;
- payloads are transferred before readiness manifests where possible, and consumer-side full hash checks remain mandatory regardless of upload order.

Rclone argv/executable/remote alias are local allowlisted configuration; package data can never supply flags or commands. Credentials/OAuth setup is performed by the operator outside Git, shared drive trees and logs. The normal R7 process receives at most a protected config reference. The bridge must detect duplicate remote names/conflicts instead of choosing a random object. Missing OAuth/cloud setup produces CLOUD_NOT_CONNECTED, not a fake connection PASS.

Provide local fake-transport tests and an operator commissioning screen/test for a real round-trip. Do not read the user's entire drive or obtain authorization silently during development. Native Drive API support remains optional; no paid sync client is required.

## PLAT-06 Packaging

Use PyInstaller native builds as the baseline; a documented bounded deviation is allowed only if native smoke evidence shows it is necessary. PyInstaller is not treated as a cross-compiler. Build Windows packages on Windows, Linux packages on Linux; record OS/architecture/glibc/interpreter and dependency locks. Verify both Ubuntu targets, not just the build host.

Windows deliverable: versioned ZIP or installer including `R7.exe`, backend, static UI, licenses, checksums, migrations, CLI diagnostics and first-run instructions. Normal start requires neither manually installed Python/Node nor PYTHONPATH. Start the browser only in desktop mode. Do not write user data inside a protected installation directory.

Ubuntu deliverable: versioned x86-64 archive/package containing `r7`, static UI, migrations, licenses, checksums, `install-service.sh`, uninstall instructions and systemd units. Installation scripts must show intended changes, validate configurable local roots, and avoid curl-pipe-shell. Admin privilege may install a service but the service runs as a dedicated unprivileged user. Do not replace system Python or install GPU drivers.

## PLAT-07 Service semantics

Provide `r7-control.service`, `r7-research.service` and `r7-runtime.service` or equivalently isolated units. They bind exact binary/config generation and have bounded restart backoff/start limits. Research/control may restart on failure. A runtime process restart always starts with trading inhibited; it rechecks durable mode, deployment identity, financial authority, process generation, E4 observations, E5 state and reconciliation before permitting exposure. Systemd restarting a process does not grant trading resumption.

Use restrictive service filesystem permissions, explicit writable roots, `NoNewPrivileges`, owned process-group shutdown and a documented security sandbox compatible with SQLite/cloud staging. Hardware reboot, sleep/resume, clock jump, missing mount and network loss must produce visible diagnostic states. A kill switch or reconciliation lock cannot be reset by restart. PAUSED blocks new entries, not monitoring/protective management of existing exposure.

## PLAT-08 Browser access

Default API bind: `127.0.0.1`; no automatic port forwarding, firewall opening or `0.0.0.0`. For viewing the Ubuntu host from the user's Windows browser, first supported remote route is an explicitly configured SSH tunnel. Provide a tested setup guide and a health check.

Optional direct LAN mode requires operator opt-in, TLS, locally provisioned authentication, role checks, CSRF protection, strict Origin/Host validation, bounded session expiry, login rate limiting and audit. Never send approval credentials over plaintext LAN HTTP. Refuse LAN write controls if any prerequisite is absent. No unauthenticated remote approval, LIVE activation or risk-limit change. No public-internet exposure in v0.2.

## PLAT-09 Upgrade, backup and retention

Never auto-upgrade code while a position is open. Upgrade requires a maintenance workflow, no new entries, correct position-management handoff, consistent DB backup, migration preflight and startup reconciliation. Refuse unverified schema downgrade. Installation and rollback must preserve user data and use a versioned backup manifest.

Use SQLite's consistent backup API or an equivalently documented stopped-database procedure; copying an actively written database/WAL into a sync folder is forbidden. Restore changes the runtime generation and invalidates stale leases/preflight/activation caches; require reconciliation and explicit re-authorization where applicable. Sanitize/encrypt backups according to their data class; live credentials are never in backup artifacts intended for cloud feedback.

## Reference basis checked 2026-10-02

These sources establish external platform facts, not R7 qualification:
- Canonical releases/lifecycle: https://ubuntu.com/about/release-cycle and https://ubuntu.com/project/docs/release-team/list-of-releases/
- systemd resource controls: https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html (executor must use installed-version manual for actual settings).
- rclone non-deleting copy: https://rclone.org/commands/rclone_copy/
- Drive backend and duplicate/shortcut behavior: https://rclone.org/drive/
- PyInstaller platform/build constraints: https://pyinstaller.org/en/stable/operating-mode.html
- SQLite backup: https://www.sqlite.org/backup.html (executor must verify the selected backup implementation).

No OS, filesystem or dependency property substitutes for a native product acceptance test.
