# Adversarial results

Evidence snapshots use SIMULATED providers and real cryptography. Tests run the production policy engine.

| Scenario | Result | Actual status |
|---|---|---|
| honest-chain | PASS | VERIFIED |
| authorized-lie | PASS | UNVERIFIABLE |
| unapproved-key | PASS | UNVERIFIABLE |
| impersonation | PASS | PROVENANCE_INVALID |
| field-tampering | PASS | PROVENANCE_INVALID |
| parent-swap | PASS | PROVENANCE_INVALID |
| wrong-binding | PASS | PROVENANCE_INVALID |
| metadata-strip | PASS | VERIFIED |
| missing-middle | PASS | PARTIALLY_VERIFIED |
| time-travel | PASS | PROVENANCE_INVALID |
| revoked-window | PASS | PROVENANCE_INVALID |
| before-revocation | PASS | VERIFIED |
| conflicting-origin | PASS | UNVERIFIABLE |
| sybil-witness | PASS | UNVERIFIABLE |
| laundering | PASS | UNVERIFIABLE |
| fake-exif | PASS | UNVERIFIABLE |
| parent-cycle | PASS | PROVENANCE_INVALID |
| c2pa-tamper | PASS | PROVENANCE_INVALID |
| audit-tamper | PASS | PROVENANCE_INVALID |
| unknown-image | PASS | UNVERIFIABLE |
| privacy-proof | PASS | PASS |
