# Fresh executable-source inventory remediation

The S12 candidate `4ea0f61c62984eaca1cbfae8b745cffb9cdec901` did not pass clean
qualification: the unchanged900-second product-suite limit terminated the owned
process after193 of194 individual cases. There was no completed unittest summary,
so the runner correctly recorded product tests_run0/returncode124 and overall
1701 completed source tests/32 commands/FAIL. The source remained exact and CLEAN.
Its unchanged Windows native regression stages had passed; no browser stage ran.

An owned cProfile execution of the final unchanged protection case passed1 test.
It captured883 implementation inventories, consuming31.7 of37.2 profiled seconds.
The product tests do not instantiate the new runtime/cloud supervisor. This
identifies repeated fresh-source traversal as a measured contributor; it does
not prove all variation in the failed suite came from that contributor.

`strategy.v02.capabilities._source_revision` now keeps fresh `os.scandir` entries
during each invocation, avoiding repeated path metadata queries. Every invocation
still enumerates the complete source, sorts root-relative names and reads every
selected Python/SQL file's latest bytes through `Path.read_bytes`. ASCII names,
LF normalization, NUL-delimited commitments, directory-link exclusion and file
link handling retain the same identity on identical readable inputs. There is no
cross-call inventory, metadata or content cache and no owner/admission check was
removed. Directory read errors now fail closed instead of silently yielding a
partial source commitment.

The new unreadable-directory regression failed on the old implementation:
21 focused tests/1 failure/0 errors/0 skips. After remediation the same21 tests
passed, including native identity, fresh SQL/owner changes and CRLF/LF binding.
An additional same-size/same-mtime Python/SQL replacement and renamed-path test
protects against unsafe caching shortcuts; it also passed before remediation.
The unchanged final product case passed separately after remediation. These
focused results do not substitute for the complete clean qualification.

Forty interleaved old/new calls each read the identical actual source and produced
identical hashes. Observed medians were16.920ms and14.241ms respectively. This is
a local diagnostic timing, not a24GB benchmark, cross-platform result or acceptance
threshold. cProfile timing and unprofiled case timing are not directly compared.

A new exact-clean source and separately rebuilt native distribution require the
unchanged complete33-command source and browser/native pipeline. At this source
checkpoint that qualification remains PENDING. Source-identity changes grant no
software-release, financial, provider or restoration authority. Normal S12 runtime
composition, production qualification-profile acceptance, native Ubuntu and real
commissioning remain separate outstanding work.
