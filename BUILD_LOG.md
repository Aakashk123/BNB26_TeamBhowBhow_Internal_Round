# Build log

Commands below were actually executed in the supplied workspace. Final consolidated results are recorded in the self-audit and corresponding report files. This is not a claim of zero defects or an independent security audit.

## Environment and installation

- Python 3.12.14; Node 24.19.0; npm 11.9.0.
- Installed FastAPI, SQLAlchemy, Alembic, Pillow, eth-account, web3, c2pa-python, native EVM tester, cryptographic and test libraries. Exact package versions are in `backend/requirements.lock`.
- Installed contract, frontend and SDK packages with exact direct dependency versions and npm lockfiles.
- Inspected installed `c2pa.Reader`, `Context.from_dict`, `Builder.sign`, `Signer.from_callback`, eth-account typed message APIs, Web3 HTTP provider signature and React Flow declarations before using them.

## Initial checks and fixes

| Command | Observed outcome | Action |
|---|---|---|
| `npx hardhat --help` before configuration | HH24: no initialized Hardhat project | Added pinned-solc config; no remote compiler download needed |
| `npm run compile` | 16 Solidity files compiled, EVM target paris | Exported identical ABI/bytecode for backend integration |
| Initial backend pytest | 32 passed, 3 errors; 93% core/engine coverage | Corrected EVM fixture key byte serialization |
| Second pytest | 34 passed, 1 failure | Corrected corroboration digest validation order |
| Native C2PA fixture test | Valid signature verified; initial mutation string was not present | Mutated a real signed `c2pa.actions` assertion instead |
| Real EVM lineage/gateway/C2PA tests | 2 passed | Verified four-hop lineage, fifth gateway step and revoked origin |
| Full backend suite before final hardening | 40 passed, core/engine 90.93% | Detailed output in `reports/pytest-final.txt` |
| `npm test` in contracts | 9 passed | Covers roles, anchor/witness/batch operations and signature replay |
| Frontend build | Initial strict TypeScript + Vite build passed | Repeated after dependency upgrades |
| Binding benchmark | 300 originals, 6,600 transforms, 3,000 negatives | Corrected raw-container baseline; remeasured and calibrated policy |
| Watermark benchmark | 100 positives, 100 negatives; about 44 dB mean PSNR | Insufficient evidence for 1e-6 FPR; verification remains disabled |
| Adversarial runner | 21 of 21 passed | Production engine with explicitly simulated evidence snapshots |

## Tooling limitations and fallback record

- Docker is not installed. PostgreSQL installation failed because the host disallows the package manager's user/group privilege changes. No permissions were broadened; isolated SQLite tests are used only with ENV=test. PostgreSQL and Compose jobs are supplied in CI and have not been executed in this environment.
- Playwright's normal Chromium CDN repeatedly returned invalid ZIP archives. An npm-packaged Chromium was extracted without ownership changes. The first packaged browser crashed with SIGSEGV during a full launch despite reporting its version correctly. Browser outcomes are recorded from the final attempt without converting crashes into passes.
- The initial Vite preview tried to enumerate host network interfaces, which this environment rejects. The test server now binds directly to 127.0.0.1.
- mypy 2.4.0 intermittently failed internally while checking external numerical-library annotations. After repeated internal failures, the fallback is pinned mypy 1.19.1; source typing errors are still corrected and strict checks rerun.
- Dependency audits initially found vulnerable frontend and development-tool transitive packages. Supported patches and explicit transitive fixes were applied and tests rerun. Hardhat 2 is retained as required; remaining low-severity elliptic advisories are disclosed in the saved contract audit.

## Final consolidated checks

- `pytest --cov=app/core --cov=app/engine --cov-fail-under=85`: **44 passed**, **94.33%** aggregate core/engine coverage. Native C2PA fixture validation and the real EVM privacy/gateway tests executed; none were silently skipped.
- `mypy app/core app/engine --strict --no-incremental`: **Success: no issues found in 13 source files** after pinning mypy 1.19.1 and installing YAML type stubs.
- `npm test` in contracts: **9 passing** after dependency hardening.
- `npm run build` in frontend: **passed**, 1,971 modules transformed.
- `npm test` in frontend: **4 tests passed**.
- `npm run e2e`: **3 tests passed** with Chromium 153. The main flow asserts no page/console errors, inspects an actual four-node EVM-backed lineage, downloads the PDF, checks saved history and executes all 21 adversarial scenarios. The mobile hash-only flow checks overflow and absent unsaved history.
- Frontend and Python audits: **zero known findings** in the saved scans. Contract development dependencies: **10 low-severity findings**, all inherited through the required Hardhat 2/elliptic toolchain; zero moderate/high/critical findings.
- Latest browser fallback succeeded after upgrading the packaged Chromium to 153 and using a minimal loopback test configuration. Screenshots were opened and visually inspected.

Remaining execution gap: PostgreSQL/Compose cannot run here; neither production hosting nor a public testnet deployment was performed. Full alternative-platform design tournament measurements and production TEE/provider-detector integrations are not implemented and are called out in SELF_AUDIT.md.
