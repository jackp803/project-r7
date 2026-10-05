# Windows atomic cloud handoff paths

Native candidate `30915c6ebc599ad6562a748d754bdf515fa67ba0` completed full
source, browser and private recovery qualification but was not accepted: one
mandatory offline bridge receipt could not be staged. The final receipt path
was 228 characters; the randomly named atomic sibling was 261 characters.
Public pre-stage validation passed. The owning outbox retained UNAVAILABLE and
never claimed an acknowledgement for that receipt.

The bounded correction passes explicit absolute extended Unicode paths to the
existing Win32 read, directory/create and atomic-finalize calls. It preserves
the original component traversal, pinned ancestor handles, reparse rejection,
opened-byte size bounds, immutable conflict checks and copy-only publication.
No machine-wide registry, service or credential setting is changed. UNC paths
use the corresponding extended UNC representation when already authorized by
the configured transport; this helper grants no additional filesystem access.

Three real filesystem regressions cover a final name below MAX_PATH with a
longer temporary sibling, opened bytes beyond MAX_PATH, and bounded atomic
replacement of author inbox data. All three failed before the correction.
The affected 40 cloud tests passed afterward. A controlled source-owner retry
published the exact previously unavailable synthetic receipt through the local
fake transport and obtained CLOUD_ACKNOWLEDGED. That diagnostic is separate
from a fresh native qualification.

A new exact-clean executable/native/browser qualification remains required.
The old candidate's passing subsets and failed bridge result remain retained
under `status/codex/productization/S13/unaccepted-recovery-30915c6/`.

Windows path behavior reference:
[Microsoft maximum path length documentation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation).
