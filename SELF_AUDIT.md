# Requirement self-audit

This matrix distinguishes implemented/tested functionality from configuration supplied but not executed and requested work that is not implemented. Raw output is kept in `reports/`. The build does not claim every master-prompt quality gate is green.

| Requirement | Implementation | Test / evidence | Result |
|---|---|---|---|
| Upload limits, sniffing, canonical pixels | `backend/app/core/pixelhash.py`, `api/services.py` | `tests/test_core.py`, `test_api.py` | Passed |
| SHA-256 and perceptual candidate-only retrieval | `core/hashing.py`, `core/perceptual.py` | Core tests; 6,600 transformation benchmark | Passed on generated fixtures |
| Signature and domain binding | `core/eip712.py`, `ModelLedgerRegistry.sol` | Hypothesis bit mutation; ethers/Python/EVM integration; replay tests | Passed |
| Salted commitments and disclosure | `core/commitments.py`, `core/merkle.py`, disclosure route | Property tests; correct proof/wrong salt; anchored root | Passed |
| Privacy leakage probe | Closed schemas, metadata minimization, in-memory processing | `test_privacy_migrations.py` checks DB/report/response/calldata | Passed; does not inspect every possible external infrastructure log |
| Actor approval, revocation, independent witnesses | Contract and fresh chain snapshot reads | 9 contract tests; real-EVM revocation of four-hop history | Passed |
| Batch Merkle anchor | Contract `anchorBatch`, `verifyInclusion` | Contract batch tests | Passed |
| Native C2PA validity and altered claim | `c2pa/reader.py` | Generated test certificates and signed C2PA fixture | Passed |
| C2PA ingredient reconstruction | Sanitized embedded summary; unresolved ingredient nodes | Policy implementation | Conservative gaps; full remote ingredient resolution not implemented |
| Pure deterministic trust engine | `engine/verdict.py`, policy YAML | 21 lab scenarios, golden/boundary tests | Passed |
| Append-only records / audit integrity | Alembic triggers and advisory-lock audit writer | Empty SQLite migration, trigger rejection, forced tamper detection | Passed locally; PostgreSQL trigger branch not executed here |
| Full backend suite | `backend/tests` | `reports/pytest-final.txt` | 44 passed; 94.33% aggregate core/engine coverage |
| Transform gateway | API transform route, ordered operations | Real EVM chain followed by fifth resize event | Passed |
| Signed JSON/PDF certificate | `certificate/builder.py` | Signature alteration rejected; PDF download in browser | Passed |
| Dashboard and graph evidence drawer | `frontend/src/main.tsx` | Browser upload → graph → certificate → history → lab | Passed |
| Mobile and browser-side hashing | Frontend and hash API | 390px browser flow with overflow assertion | Passed |
| Light/dark CSS and keyboard affordances | CSS themes, labelled controls, skip link | Source implementation; main browser flow | Implemented; full accessibility audit not performed |
| API types | Generated `api-types.ts` and OpenAPI schema | TypeScript strict build | Passed |
| Lint and strict Python typing | Ruff, ESLint, mypy | Saved lint/type output | Passed |
| Frontend unit tests | `src/api.test.ts` | Vitest output | 4 passed |
| Contract tests | `contracts/test/Registry.ts` | Hardhat output | 9 passed; not an exhaustive proof over every possible input |
| Provider SDKs | `sdk/python`, `sdk/ts` | Python SDK used in real-chain test; TypeScript SDK typecheck | Passed for tested paths |
| Real-model wrapper | `demo/real_model_example.py` | Complete configurable subprocess integration | Not executed with an actual AI model/provider |
| Demo ecosystem | `seed/demo.py`, `demo/samples` | Real EVM seeding and browser verification | Passed; providers/observations are SIMULATED |
| Binding design experiment | `bench/binding_bench.py` | 300/6,600/3,000 measured dataset | Executed; not natural-image population validation |
| Origin baseline experiment | `bench/origin_bench.py` | 7/20 baseline vs 20/20 policy | Executed |
| Full design tournament | `docs/DECISIONS.md` | Negative results and omitted alternative measurements | Incomplete |
| Watermark enablement | Experimental core module | 100/100 test and PSNR | Disabled; required statistical detection gate unproven |
| Production TEE/provider detector | No accredited adapters | Engine refuses unsupported adapters | Not implemented; never silently simulated as trusted |
| Dependency audit | Exact locks and saved audit JSON | Python/frontend zero findings; contract 10 low findings | Residual Hardhat 2 toolchain findings documented |
| Docker deployment and PostgreSQL 16 | Compose, Dockerfiles, production Caddy, CI | No local Docker/PostgreSQL runtime | Configuration supplied; execution not verified here |
| Public hosting / testnet deployment | Deployment guide | No public infrastructure or keys supplied | Not deployed |

## Known operational constraints

One backend worker is required for consistent temporary-report access. For multiple replicas, replace the temporary cache and rate limiter with shared services. A compromised database administrator can remove triggers and rewrite a local audit chain; external anchors are the independent reference. Certificate signatures report a historical verification result and do not freeze later revocation status.

Graph capacity was additionally exercised with a synthetic 200-node/199-edge fixture. The recorded test rendered in under one second and opened a node's evidence drawer in under 200 ms. `bench/results/graph.json` contains the latest measured timings. This fixture tests rendering performance only.
