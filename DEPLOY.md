# Deployment

## Local, offline-capable demonstration

Prerequisites: Python 3.12, Node.js 22+, npm, GNU Make and Docker Compose v2. Use Linux/macOS or Ubuntu under WSL2 on Windows. Initial bootstrap needs network access to dependency and container registries; after images and packages are cached the demo runs offline.

```sh
make bootstrap
make configure
make up
```

Open `http://localhost:8080`. The generated development environment enables explicitly SIMULATED providers and witness observations. Startup migrates PostgreSQL, deploys a registry if needed, registers the transform gateway and issuer, and seeds the four-hop demo. `make demo` reruns the demo initializer. `make down` stops services without deleting PostgreSQL data.

`make configure` preserves an existing `.env`. It generates fresh issuer/gateway/API keys and a random PostgreSQL password. The registrar uses Hardhat's publicly documented test mnemonic only for local development. Never use these test accounts on a funded public chain. Never expose port 8545 outside localhost.

If the local chain is restarted, its state disappears. Existing evidence may become unanchored until its events are reanchored. Demonstration startup can re-register demo actors, but do not treat the local chain as durable audit storage. For a fresh demo, explicitly back up any desired data before `docker compose down -v`. That command deletes local database volumes.

## Run source code without frontend containers

Start PostgreSQL and Hardhat with `docker compose up -d postgres chain`, then:

```sh
export PYTHONPATH="$PWD/backend:$PWD/sdk/python:$PWD"
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/python ../scripts/init_chain.py
../.venv/bin/python -m app.seed.demo
../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In a second terminal: `cd frontend && npm run dev`. Vite proxies the backend. SQLite is rejected unless ENV=test. The Playwright suite starts its own isolated SQLite/in-process-EVM test server; that server is never the deployment command.

## Production with an external EVM chain and HTTPS

1. Copy `.env.production.example` to `.env.production` and provide a domain, random database password, HTTPS PUBLIC_URL/CORS origin, external RPC endpoint, chain ID, fresh issuer key and funded gateway/registrar keys. Keep `ENABLE_DEMO=false`, `ALLOW_SIMULATED=false` and `DEV_API_KEY` empty. `.env.production` is ignored by git and package exports.
2. Run `make bootstrap`. Load production secrets into the shell without printing them. Set `TESTNET_RPC_URL` to the chosen RPC and `DEPLOYER_KEY` to the registrar's deployment key. In `contracts/`, run `npx hardhat run scripts/deploy.ts --network testnet`. Read the deployed address from `.runtime/deployment.json` and set `CONTRACT_ADDRESS` in `.env.production`.
3. Point the domain's DNS to the server. Open only TCP 80/443 publicly. Do not expose PostgreSQL or any development Hardhat RPC.
4. Start PostgreSQL, migrate the schema and provision the gateway/issuer:

```sh
docker compose --env-file .env.production -f compose.production.yml up -d postgres
docker compose --env-file .env.production -f compose.production.yml run --rm backend sh -c 'cd /app/backend && alembic upgrade head && python /app/scripts/provision_production.py'
```

5. Remove `REGISTRAR_KEY` from the service environment after provisioning; routine production admin operations accept registrar-signed transactions rather than keeping that key online. Start the stack:

```sh
docker compose --env-file .env.production -f compose.production.yml up --build -d
```

Caddy obtains TLS certificates for the domain and proxies nginx. The backend validates production configuration at startup. Keep the issuer and gateway private keys in a managed secret store for a real deployment; consider HSM signing as a subsequent custody integration. The contract and issuer address should be published independently so third parties can compare them.

## Render, Fly or Railway backend

Deploy the repository using `backend/Dockerfile`, provide PostgreSQL 16 and the production environment variables above, and expose port 8000 internally. Run Alembic before serving; the image start command does this. Registry/gateway provisioning is a one-time trusted admin action. Use one application worker while unsaved report caching and rate limiting remain in-process. Use a stable HTTPS custom domain and include its origin in CORS.

## Vercel or Netlify frontend

Build command: `npm ci && npm run build` in `frontend/`; output directory: `dist`. Configure same-origin reverse-proxy rewrites for `/api/*`, `/.well-known/*` and optionally `/openapi.json` to the backend, plus SPA fallback for non-API routes. Preserve cookies and do not cache API responses. A separate cross-origin backend without a proxy requires explicit cookie/CORS redesign; the supplied frontend intentionally uses same-origin fetches.

## Verification and operations

`/api/v1/health` reports healthy only when both database and configured registry are available. Back up PostgreSQL and the operator-managed keys. Run `make test`, `make lint`, `make typecheck`, `make adversarial` and `make audit` after dependency/policy changes. Preserve dependency locks and archive the exact policy with reports. Container image major tags are intentionally maintained tags, not claimed immutable digests; pin audited image digests in a controlled deployment pipeline.

The local build environment did not provide Docker or PostgreSQL, so Compose startup and external hosting were not executed here. GitHub Actions includes PostgreSQL-backed tests and a Compose smoke job, but those remote jobs have not yet run for this package. Do not interpret the included configuration as a completed public deployment.
