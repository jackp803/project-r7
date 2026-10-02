# Local Control Center

Traditional-Chinese React/TypeScript UI for the actual authenticated control API.
Requires Node 24 and the pinned lockfile; all build and browser commands run locally.

```powershell
npm --prefix ui ci --ignore-scripts --no-fund
npm --prefix ui run types:check
npm --prefix ui run typecheck
npm --prefix ui test
npm --prefix ui run build
npm --prefix ui run test:browser
```

The generated TypeScript contract comes only from
`contracts/control_api_v0_2.openapi.json`. Regenerate with `npm --prefix ui run types`
after an intentional API change. Remote references are rejected. Production assets
are `ui/dist`; the trusted server composition calls `mount_control_center` with
that root. The API retains authentication, CSRF, Host/Origin and loopback guards;
the static asset mount adds no API fallback. Native installation/composition is S13.

Browser QA starts five isolated real local service compositions using explicit
synthetic fixture identities and the installed headless Edge on Windows. Fixtures
call actual intake, E6, research queue and PAPER owners. They do not use private
provider APIs or the user's browser profile. Set `R7_BROWSER_CHANNEL` only to an
installed Playwright-supported browser on another authorized native platform.
Windows browser results do not qualify Ubuntu.

The first production account must be enrolled through the trusted local CLI using
a user-selected password. There is no default password or browser enrollment.
Session revocation returns the UI to login; it does not imply a runtime shutdown.
Passwords and session/CSRF values are never stored in localStorage or logs.

Commands carry an ID and expected resource revision. On an uncertain response the
UI retains the exact request in memory and offers an explicit same-ID retry;
reloading loses that browser state, so inspect the server command receipt before
making a replacement command. Conflicts require refresh and deliberate resubmission.
Stopping research and stopping new PAPER entries are separate operations. PAPER
pause preserves existing exposure/protection management and requires reconciliation
of already in-flight effects. Closing a browser does not flatten a position.

Every screen preserves source namespace, as-of clock, revisions and hashes.
Unavailable metrics remain null, ACK differs from fill, process health differs from
last broker facts, and accelerated fixtures do not count as real forward evidence.
Author hypotheses are labeled with their verified immutable submission source.
No illustrative profit or global SAFE status is displayed.

S11 provides functional owner-backed UI controls and isolated acceptance. Financial
approval remains visibly denied in FIXTURE and uncommissioned until a trusted exact
envelope is available. Production provider/admission surfaces are S12; native
process/backup/service composition is S13; cloud copy-only commissioning is S14.
Real provider, credentials, capital, cloud and forward commissioning are separate
acceptance gaps and are not implied by successful browser tests.
