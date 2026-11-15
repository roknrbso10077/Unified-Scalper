# Dependency lock policy — A69

`requirements.in` is the source of direct runtime dependency pins. `requirements.txt` is a compatibility entry point that includes it. The checked-in `requirements-lock.txt` is a direct-pin seed only: it is **not** a complete transitive lock and contains no fabricated hashes. Do not pass it to `pip --require-hashes`.

## CI resolution contract

The workflow `.github/workflows/a65-production-audit.yml` is configured to resolve a platform-specific dependency set for Python 3.12 / Linux amd64 using `uv pip compile --generate-hashes`, verify hashes with `pip --require-hashes`, and build Docker with `STRICT_HASH_LOCK=1`. It also resolves the development dependency lock. Generated lock files are workflow artifacts, not checked-in release evidence until the workflow actually runs.

## Deployment boundary

- Target: Python 3.12, Linux amd64.
- CI strict Docker build: `STRICT_HASH_LOCK=1` only after fresh hash-lock resolution.
- Default Docker path: `STRICT_HASH_LOCK=0`, direct dependencies from `requirements.in`.
- Docker pins pip separately; this does not make transitive dependencies reproducible.
- CI/build configuration is not proof of a successful remote build, exchange authentication, Telegram delivery, stop protection, or profitable trading.

No package hashes are inferred or invented in this A69 merged package. The Python 3.12/Linux amd64 CI resolution and Docker build remain unverified until the workflow actually runs.
