# Ubuntu CPython 3.12 build preparation

The adjacent lock contains hashes of 24 actual public Linux x86-64 wheels downloaded on Windows. Wheel ZIP metadata, package versions, platform tags and dependency closure were checked without executing the wheels. `wheel-preparation.json` preserves the artifact identities. Windows-only `pefile` and `pywin32-ctypes` are excluded from the Linux target.

This is dependency preparation. Ubuntu 24.04/26.04 installation, interpreter compatibility, glibc, licenses from the installed target, native PyInstaller builds, service sandbox and boot/reboot qualification remain **NOT_RUN**. No Windows result certifies either Ubuntu target.

On an explicitly authorized Ubuntu host, provision a separate CPython 3.12 environment, download these exact wheels using the hash lock, install with `--require-hashes --only-binary=:all:` and verify actual versions/licenses before `tools/build_product.py`. Preserve the system Python. Build from an exact clean committed revision. The builder refuses unsupported OS/interpreter/architecture, mismatched dependencies and unlicensed artifacts. Never build a Linux executable on Windows.

`pip download` supports explicit target interpreter/platform/ABI selection; this resolves downloadable wheel bytes and does not execute or qualify a target application. [Official pip download documentation](https://pip.pypa.io/en/stable/cli/pip_download/).
