# Dependency constraints and canonical build entrypoint

`requirements.txt` is the only dependency-install entrypoint used by the Docker build. It includes `requirements-lock.txt` using pip's `-r` directive so local and Docker builds consume the same direct-dependency constraints.

`requirements-lock.txt` currently pins these direct runtime dependencies exactly: `ccxt==4.5.81`, `python-dotenv==1.2.4`, `numpy==2.3.5`, `pandas==2.2.3`, `aiohttp==3.14.3`, and `aiosqlite==0.22.1`. `python-dotenv` is used by the project-root `.env` bootstrap loader. aiohttp is pinned to 3.14.3 for compatibility with CCXT's async runtime and the previously reported Railway dependency-resolution issue.

**Important limit:** this is not a complete deterministic lock. It does not pin every transitive dependency to an exact version with hashes, so it is not suitable for `pip --require-hashes` and cannot guarantee byte-for-byte reproducible dependency resolution. That work was not completed in this environment because the package resolver/index was unavailable during the original audit. Do not describe this file as a full lockfile; it is a direct-dependency constraints file.

Offline tests and `--validate-only` do not prove a production host build succeeds. No actual Docker image build or Railway deployment was performed as part of the A7 audit. Live MEXC requests, real Telegram delivery, exchange-native stop verification and profitability are likewise unverified.


## A44 release disposition (2026-10-18)

The A44 review attempted to establish a full transitive, hash-locked dependency graph. The resolver/index and wheel cache were unavailable in this working environment, so no complete transitive lock was generated and no hashes were invented. `requirements-lock.txt` remains an exact-version constraints file for direct runtime dependencies only. A live/reproducible release build remains **NO-GO** until a connected, controlled CI job resolves the graph for the Docker target (`linux/amd64`, Python 3.12), emits all transitive package hashes, installs using `pip --require-hashes`, and records the successful build artifact digest.

Recommended controlled build procedure on a connected release runner:

```bash
uv pip compile requirements.txt --python-version 3.12 --generate-hashes --output-file requirements-hashed.lock
python -m pip install --require-hashes -r requirements-hashed.lock
python -m pip check
```

The result must be committed only after verifying that the generated graph matches the target platform and all packages resolve successfully. The above commands are a procedure, not evidence that the lock was generated in this session.


## A48 release recheck (2026-10-19)

The A48 attempt was repeated using `uv 0.10.0` with `uv pip compile requirements.txt --python-version 3.12 --generate-hashes --output-file /tmp/requirements-hashed-a48.lock`. It did not complete: the resolver could not resolve `pypi.org` / fetch `aiohttp` due to unavailable DNS/network access. No hashed lock was generated, and no package hashes were fabricated. The runtime therefore still uses exact direct-package constraints but does **not** meet the complete transitive `--require-hashes` release gate.

Docker CLI was unavailable in this environment, so a Docker image or Railway deployment was not built. The Dockerfile has been updated to copy the flat `v702_core__*.py` helper modules, but this packaging correction is not a substitute for a connected Python 3.12 target build. Keep unattended live trading **NO-GO** until a connected CI runner creates and verifies the transitive hash lock and builds the target image.


## A56 final package status (2026-11-06)

The six direct dependencies remain pinned exactly as listed above. A full transitive lock with hashes was **not generated** in this session: no resolver/index proof or target-platform wheel resolution is available. The manifest records `transitive_dependencies_hash_locked=false`; do not use `pip --require-hashes` with the current `requirements-lock.txt`. The connected CI procedure above is still required. No Docker build or Railway deployment success is claimed.
