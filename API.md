# API

The generated `openapi.json` is authoritative. Interactive docs are at backend `/docs` (direct local port 8000); frontend routing proxies `/openapi.json`. nginx's restrictive CSP may prevent CDN-hosted Swagger assets, so direct backend docs are intended for local development. Production consumers should use the generated schema.

All API routes start with `/api/v1`. JSON failures use `{ "error": { "code": "INVALID_EVIDENCE", "message": "Invalid image" } }` and validation failures list field paths without echoing values.

| Method / route | Purpose |
|---|---|
| POST `/verify` | Multipart file plus optional `save_history` |
| POST `/verify/by-hash` | Browser SHA-256 exact lookup; no image transmitted |
| POST `/register` | Register a version, optional declaration, opt-in thumbnail and signed event JSON |
| POST `/events` | Validate and store a provider-signed event |
| GET `/events/{hash}` | Inspect the signed payload, public parameters, signature and anchor |
| POST `/events/{hash}/corroborations` | Store public evidence that already matches an approved on-chain witness record |
| POST `/transform` | Multipart image and ordered operations; returns image and signed event in a ZIP |
| GET `/versions`, `/versions/{id}` | Public registered fingerprints and opted-in previews |
| GET `/lineages/{id}/graph` | Merge known version histories into a graph |
| GET `/reports/{id}` | Retrieve an owned saved or unexpired report |
| GET `/reports/{id}/certificate?format=json\|pdf` | Signed JSON envelope or printable report with QR |
| POST `/certificates/verify` | Verify issuer signature; returns whether issuer is configured on chain |
| GET/POST `/actors` | Read identities or register an owner-signed profile for an existing on-chain actor |
| POST `/actors/{id}/approve`, `/revoke` | Registrar-signed raw transaction; dev API key only when ENV=dev |
| POST `/disclosures/verify` | Stateless verification of one private-field proof |
| GET `/history` | Up to 100 saved reports owned by the current cookie |
| GET `/adversarial/scenarios` | Deterministic scenario catalog |
| POST `/adversarial/run/{id}` | Execute a scenario using real cryptography and simulated snapshots |
| GET `/audit/verify` | Recompute the database audit chain |
| GET `/health` | Database and chain availability |

Issuer identity is at `/.well-known/modelledger-issuer.json`. Certificate routes deliberately require the owner's cookie; a PDF QR opens the report in that session. Share the signed JSON for independent offline signature verification. This release does not silently publish private report history.

The API never receives provider private keys. The Python and TypeScript SDKs sign on the provider's side. Providers submit chain transactions through their own wallets or the Python `Chain.send` helper in trusted integration code. Witness approval/revocation and batch anchoring are contract operations available through its ABI.
