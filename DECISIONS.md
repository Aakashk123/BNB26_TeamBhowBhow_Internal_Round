# Engineering decisions and negative results

## Source precedence

The user supplied a Master Build Prompt and a product blueprint. The master explicitly calls its trust model non-negotiable and locks a blockchain architecture. It takes precedence over the earlier blueprint's no-blockchain MVP and signature-only verification language. The blueprint supplies the dashboard information architecture, version-as-node graph, comparison view and careful certificate wording.

## Trial-and-error record

| Axis | Implemented measurement | Decision | Remaining limitation |
|---|---|---|---|
| T1 binding | 300 procedural images, 6,600 transformations, 3,000 negative pairs; file/pixel hashes, a/d/p/w hashes and ORB | File and pixel hashes establish exact bindings; signed events establish relationships; median d/p/w votes discover candidates | Procedural test set is not representative of all natural or generated images; 1,500 held-out negatives cannot establish a population FPR bound |
| T2 chain | Solidity compiled with local solc; Hardhat and in-process EVM contract tests, EIP-712 digest agreement and batch inclusion | EVM registry with an offline local Hardhat development chain; external persistent chain for production | Fabric, Solana and OpenTimestamps were not installed or benchmarked; the full six-platform tournament is incomplete |
| T3 signature | EIP-712 signatures checked in Python, ethers and deployed contract tests; chain/contract replay tests | EIP-712, secp256k1, RFC 8785 public parameter hashing | Ed25519 JWS/COSE interoperability tournament is not implemented |
| T4 origin | Signature-only baseline versus the production engine across deterministic adversarial snapshots | Independent witness plus actual anchor and temporal/authority checks | Real TEE/provider-detector attestation adapters are not implemented or accredited; their evidence never counts merely because a client labels it valid |
| T5 graph | React Flow, dagre layout, browser flow, graph selection and a 200-node rendering test | Versions are nodes; signed exports are edges; missing relationships are dashed | Comparative Cytoscape/D3 timings are not collected |
| T6 watermark | Keyed pattern, JPEG quality 75 plus 50% resize experiment; 100 positives/100 negatives, PSNR | Disabled in verification; experimental code and benchmark only | A sample of 100 negatives cannot justify a 1e-6 false-positive threshold, regardless of a promising score separation |

The weighted design rubric in the master prompt is not presented as measured data: unexecuted alternatives have no invented scores. The locked stack was retained. This is an explicit incomplete design-exploration requirement, not an implementation success claim.

## Corrections made during the build

- Fixed test-account key conversion after real EVM integration exposed a variable-width byte conversion.
- Added pre-broadcast validation of registrar-signed transaction destination, calldata, value and chain ID. A signed transaction for another action is never broadcast by the admin endpoint.
- Corrected a benchmark error that reconstructed WebP input as PNG before file hashing. Container-sensitive B1 is now measured on actual output bytes.
- Reordered corroboration checks so an altered evidence blob is an integrity failure even if the changed blob says no observation occurred.
- Separated embedded C2PA signer trust from approval of an AI model origin. Valid untrusted certificates remain A1.
- Upgraded vulnerable frontend dependencies, moved Tailwind to v4 and pinned transitive fixes for development tooling. Hardhat remains major version 2 as requested; any residual advisories are enumerated in the audit outputs.
- Browser CDN downloads repeatedly returned invalid archives. The successful fallback is pinned Chromium 153 from npm, extracted locally without changing filesystem ownership. The earlier Chromium 143 binary crashed on this host. No browser authentication or external account is involved.
- This environment has no Docker daemon or PostgreSQL binaries, and its package installation blocked privilege changes. PostgreSQL execution and Compose health checks therefore remain unexecuted locally. The repository contains CI jobs for both; CI results have not been observed here.

## Practical boundaries

Public actor registration requires a real on-chain identity and an owner-signed profile. Production administration requires a registrar-signed raw transaction. Development API-key authorization is accepted only in ENV=dev. Production startup rejects simulated evidence and demo/API-key flags.

Unsigned manual claims are recorded as A0. Unsupported TEE or watermark corroborations cannot reach A3. Watermarks and visual similarity cannot bind an uploaded artifact or establish a lineage edge. Remote C2PA fetching is disabled to avoid SSRF and unrequested network disclosure.

The local Hardhat chain is ephemeral. Its accounts are publicly known development fixtures. It must never hold valuable assets or be exposed publicly. Production uses an externally managed persistent EVM chain.

Single-worker operation is intentional: unsaved reports and rate counters are bounded in-process data. Saved history is scoped to an anonymous browser capability cookie. This is not an enterprise identity or account-recovery implementation.
