# Managed control and research stop

Trusted local control/research entrypoints install a scoped SIGINT/SIGTERM
handler, plus SIGBREAK where Windows exposes it. The handler only records a
stop request. It raises no asynchronous exception through SQLite or an owner
operation. Previous handlers are restored on exit; installation requires the
main thread. Uvicorn retains its own server signal lifecycle inside this scope.
The handler acquires no Event/coordination lock. Idle waits observe its flag
between at most100ms monotonic wait segments, rather than taking an interrupted
non-reentrant Event lock from the signal handler.
[Python3.12 signal behavior](https://docs.python.org/3.12/library/signal.html).

Control waits for the actual server loop to stop, then records a clean STOPPED
process generation. Config/currentness/storage failure remains a failure; a
stop request cannot make that failed generation healthy. Research stops idle
waiting promptly, rejects new admission after observing a stop request and
checks it between bounded child waits. An active owned tree is terminated and
reaped before its exact durable job receives disposition. A completed, blocked
or canceled owner result is retained. Otherwise an interrupted job is FAILED
with OWNED_WORKER_STOPPED, rather than reporting research completion or blindly
replaying its sealed/partial owner work. A new process does not revive that job.
Timeout and cancellation retain their own distinct reason codes.

This is control/research behavior only. No trading worker, pending-position
handoff, financial authorization, exposure or provider operation is introduced.
Future runtime shutdown must preserve its separate E4/E5 reconciliation and
management rules. Hard kill, host OOM, reboot and unavailable native systemd
are not a clean-stop claim.

Windows source verification executes actual in-process signals with restored
handlers, an actual loopback server, and a stopped actual research child plus
grandchild. It also retains configuration-drift, process-exclusion, timeout and
stale-generation regressions. Real external POSIX SIGTERM and Ubuntu systemd
stop/restart remain NOT_RUN until an approved Ubuntu environment is attached.
Do not transfer Windows evidence to those targets.

Health UI labels now distinguish a reachable interface, observed process
heartbeat, an available queue without an active worker, stopped/failed process,
unknown state and unconfigured owner. Recent heartbeat is no financial permit.
The browser fixture uses an actual supervised process with its explicitly
synthetic clock; it does not qualify actual forward duration.
