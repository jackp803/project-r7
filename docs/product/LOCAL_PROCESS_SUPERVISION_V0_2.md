# Local process supervision v0.2

Control and research entrypoints hold separate host process scopes for their
entire lifetime. Windows uses a Global named mutex keyed by role and configured
product identity; different local data directories cannot bypass the mutex.
An in-process guard also denies Win32 same-thread mutex recursion. Process death
releases the kernel lock. Acquisition never clears a financial/reconciliation
lock or grants permission. [Win32 object namespaces](https://learn.microsoft.com/en-us/windows/win32/sync/object-names).

The POSIX implementation uses nonblocking flock on regular, non-linked local
files. Operational entrypoints require the shared `/run/r7/scopes` directory,
provisioned for one dedicated service user; there is no per-profile fallback.
Locks are never unlinked on release. Native Ubuntu execution remains NOT_RUN;
Windows results do not qualify this path. These are single-host locks, without
multi-host fencing. Trading provider/account/instrument exclusion and explicit
deployment identity remain part of the pending runtime composition.

The local `process-supervision.sqlite` store records independently fenced control
and research generations, exact validated configuration hash, actual process ID,
source implementation/build provenance, UTC timestamps, heartbeat sequence and
history. Every start has a fresh random process generation plus a durable counter.
Source Git status and frozen build identity remain distinct. All records state
financial_authority=NONE and restart_admission=RECONCILIATION_REQUIRED. These
application facts cannot substitute for E6 consent, E7 compatibility/currentness,
E4 observations or E5 position authority.

Heartbeat uses a separate thread and short SQLite transactions. Owner work never
holds a supervision transaction. Generation replacement, invalid storage, clock
regression and selected configuration drift inhibit the original process. A clock
returning to normal does not automatically revive a failed generation. Health
distinguishes recent heartbeat, stale/future timestamps, an observed dead PID,
configuration change, clean stop and failure. Recent heartbeat is a bounded
process observation, not financial authority or proof against PID reuse.

The control process stops its actual Uvicorn server on loss of currentness. The
desktop browser opens only after actual server readiness. IPv6 loopback URLs use
brackets. API health includes actual supervised control/worker states while an
absent research selection remains NOT_CONFIGURED. [Uvicorn programmatic server
lifecycle](https://www.uvicorn.org/).

Research admission and each bounded wait recheck the actual process/config
generation. Loss of currentness terminates and reaps the owned child tree before
recording the exact claim's disposition. The worker holds its scope while idle
as well as during replay. It never kills by process name, resets sealed OOS or
overwrites a successor claim. Memory enforcement remains SOFT_LIMIT_ONLY.

Actual source Windows tests execute independent control processes, deny a second
process, kill/reap an owned process, observe a new successor generation, stop on
configuration change and cancel/reap a real research child. These tests do not
qualify native packaging, Linux/systemd, host reboot/sleep, backup restore, real
cloud/dataset/forward observation or a trading runtime. Those remain S13/S15 work.
