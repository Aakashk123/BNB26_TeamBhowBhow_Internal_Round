# ModelLedger

**A digital passport for AI images.** Verify registered origin claims, inspect signed transformation history, expose missing evidence, and export a signed verification report.

![ModelLedger dashboard](docs/screenshots/verify.png)

This repository combines the supplied master build prompt's blockchain trust model with the reference blueprint's dashboard and version graph. It contains a working React frontend, FastAPI backend, PostgreSQL schema/migrations, Solidity registry, provider SDKs, simulated demo integrations, adversarial tests and deployment configuration.

## Start the local application

Use Python 3.12, Node.js 22+, npm, GNU Make and Docker Compose v2. On Windows, use Ubuntu in WSL2 with Docker Desktop integration.

```sh
make bootstrap
make configure
make up
```

Open **http://localhost:8080**. Choose the final demo export to see a four-stage verified lineage. All procedural providers and demo observations are explicitly labelled **SIMULATED**. Cryptographic signatures, deployed EVM contract execution and witness records are real.

`make configure` creates private development configuration without overwriting an existing `.env`. `make demo` reseeds examples; `make down` stops services. For HTTPS hosting and an external EVM chain, follow [DEPLOY.md](docs/DEPLOY.md). The application has not been publicly deployed by this build.

## What is included

- Static PNG, JPEG and WebP validation; 25 MiB/25-million-pixel limits.
- Exact file and canonical pixel bindings; calibrated perceptual candidate discovery.
- Embedded C2PA validation using the native library, with explicit unavailable/unevaluable states.
- EIP-712 signed, parent-linked export events; on-chain actor approval, retroactive revocation, independent witnesses and batch anchors.
- Deterministic four-state verdict engine with reason codes, counts and policy hashes.
- Interactive lineage graph, comparison, evidence viewer, session-scoped history and asset registry.
- Signed transform gateway for resize, crop, blur, contrast, compression and reencoding.
- Owner-side salted private commitments and stateless selective disclosure verification.
- EIP-191 signed JSON certificates and downloadable PDF reports with QR links.
- Append-only evidence tables, hash-chained audit trail, strict public request schemas and bounded temporary report storage.
- Python/TypeScript provider SDKs, a real-model command wrapper, and 21 executable adversarial scenarios.

## What verification means

| Verdict | Meaning |
|---|---|
| VERIFIED | Exact bound artifact, supported origin and trusted evaluated history without unexplained gaps |
| PARTIALLY_VERIFIED | Some trusted path evidence exists, but the complete history is not established |
| PROVENANCE_INVALID | Relevant evidence exists and fails integrity or consistency checks |
| UNVERIFIABLE | Evidence is absent or insufficient, including self-asserted claims without required corroboration |

A signature proves who controls a key. A blockchain anchor proves a claim was recorded. Neither proves that a particular model produced the pixels. An AI origin reaches A3 only with an approved actor, an anchor, temporal priority and independent approved corroboration. Similarity alone never proves origin or a transformation. There is no invented percentage trust score.

## Executed checks

See [BUILD_LOG.md](docs/BUILD_LOG.md), [SELF_AUDIT.md](docs/SELF_AUDIT.md) and `reports/` for actual command output and limitations.

| Check | Recorded result |
|---|---|
| Backend, properties, real EVM integration, C2PA and privacy | 44 tests passed; 94.33% core/engine coverage |
| Smart contract | 9 tests passed |
| Frontend unit tests | 4 tests passed |
| Browser workflow and mobile privacy flow | 3 tests passed; no browser console errors in the main flow |
| Adversarial lab | 21 / 21 passed |
| Strict Python/TypeScript checks and lint | Passed |
| Production frontend build | Passed |
| Python and frontend dependency audits | No known vulnerabilities in the recorded scan |
| Contract development dependencies | 10 low-severity findings through Hardhat 2 / elliptic; no moderate/high/critical findings |
| Docker/PostgreSQL production startup | Not executed in this environment; CI jobs supplied, results not yet observed |

```sh
make test
make lint
make typecheck
make adversarial
make bench
make audit
```

`make test-web` uses an isolated temporary SQLite database and actual EVM bytecode execution, solely for tests. The deployed application requires PostgreSQL. Test browser extraction uses a pinned Chromium package; production ships static frontend files, not that browser.

## Benchmark evidence

The dataset contains 300 generated images, 6,600 transformations and 3,000 unrelated pairs. Half the negatives calibrate thresholds; half are held out. These are test-set results, not population guarantees.

| Candidate method | Recall across tested transforms | Held-out false-positive rate |
|---|---:|---:|
| aHash | 91.41% | 0.067% |
| dHash | 90.26% | 0.067% |
| pHash | 90.00% | 0% observed |
| wHash | 90.30% | 0% observed |
| Median dHash/pHash/wHash vote | 91.32% | 0% observed |
| ORB thresholded local matches | 89.26% | 0.133% |

The deployed candidate threshold is calibrated from these data. Rotation failed and large crops had poor recall; these failures are retained in [BENCHMARKS.md](docs/BENCHMARKS.md). Heavily degraded images remain unverifiable when evidence is insufficient.

| Origin evidence experiment | Scenarios classified correctly |
|---|---:|
| Naive approved-signature-only baseline | 7 / 20 |
| Full policy engine | 20 / 20 |

The baseline incorrectly trusts the “authorized signer lies” case. The production engine returns UNVERIFIABLE / SELF_ASSERTED with NO_CORROBORATION. The separate privacy proof check brings the adversarial UI total to 21.

## Deliberate limits and unfinished blueprint items

- Watermark code is experimental and disabled. Its experiment does not establish the required 1e-6 false-positive bound.
- No real TEE quote verifier or accredited provider watermark detector is shipped. Unsupported attestation kinds cannot grant trust.
- The complete multi-platform design tournament was not executed. No fabricated scores are presented for untested Fabric, Solana, OpenTimestamps, COSE, Cytoscape or D3 alternatives.
- C2PA is embedded-only and read/verify-only. Unresolved ingredients are visible gaps; remote retrieval and credential writing are not product features.
- No account-based multi-tenant login, distributed cache/rate limiter or HSM integration is included. Saved history uses an anonymous browser capability cookie; unsaved reports expire after 30 minutes.
- PDF QR links require the report owner's session. Share signed JSON for independent certificate signature checking.
- The local development chain is ephemeral and uses public test accounts. Production must use a persistent externally operated EVM network.
- No implementation can guarantee zero bugs. This repository has not received an independent security audit; Docker/PostgreSQL deployment still needs the supplied environment checks.

## Repository map

| Directory | Contents |
|---|---|
| `backend/app/core`, `engine` | Cryptographic functions and pure verdict policy |
| `backend/app/api`, `db`, `chain`, `c2pa` | API services, storage, registry reads and native validation |
| `contracts` | Solidity registry and Hardhat tests |
| `frontend` | Responsive dashboard, generated API types and browser tests |
| `sdk` | Provider-side Python and TypeScript signing/commitment libraries |
| `bench` | Reproducible binding, origin and experimental watermark benchmarks |
| `demo` | Procedural sample files and real-model wrapper |
| `docs`, `reports` | Architecture, threat/privacy model, deployment, evidence and self-audit |

License: MIT. Third-party components retain their respective licences.
