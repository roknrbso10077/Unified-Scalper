# Dependency inputs and release lock policy — A61 current packaging boundary

`requirements.in` is the sole source of direct runtime dependencies. It keeps the six declared package pins:

- `ccxt==4.5.81`
- `python-dotenv==1.2.4`
- `numpy==2.3.5`
- `pandas==2.2.3`
- `aiohttp==3.14.3`
- `aiosqlite==0.22.1`

`requirements.txt` is a compatibility entry point that includes `requirements.in`. The checked-in `requirements-lock.txt` is a direct-pin seed only; it is intentionally **not** a transitive lock and contains no fabricated hashes. Do not pass this checked-in seed to `pip --require-hashes`.

## Connected CI release path

`.github/workflows/a58-production-audit.yml` resolves a platform-specific lock for Python 3.12 / Linux amd64:

```bash
uv pip compile requirements.in \
  --python-version 3.12 \
  --python-platform x86_64-unknown-linux-gnu \
  --generate-hashes \
  --output-file requirements-lock.txt
python -m pip install --require-hashes -r requirements-lock.txt
python -m pip check
docker build --build-arg STRICT_HASH_LOCK=1 .
```

The workflow publishes the generated lock as the `a58-python312-linux-amd64-hash-lock` artifact. It currently does not commit generated resolver output back into the repository. CI can therefore prove a strict ephemeral build, while Railway's normal build uses Docker's default `STRICT_HASH_LOCK=0` path and installs the direct pins from `requirements.in`. This avoids the previous deterministic build failure but does not make Railway's transitive resolver bit-for-bit reproducible. The checked-in lock should only be replaced with a generated, verified lock artifact from the target platform.

## Deployment boundaries

- Build target: Python 3.12, Linux amd64.
- Docker strict build: `STRICT_HASH_LOCK=1` (CI only after resolution).
- Railway default: `STRICT_HASH_LOCK=0`, direct pins from `requirements.in`.
- Docker installs a fixed `pip==24.3.1`; it does not run `pip --upgrade`.
- Docker/CI build success does not prove a Railway rollout, exchange authentication, order placement, Telegram delivery, software-stop supervision or profitability.

No package hashes are inferred or invented in this source package.
