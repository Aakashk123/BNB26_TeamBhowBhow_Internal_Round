# Trust policy

`config/trust_policy.yaml` is hashed byte-for-byte with SHA-256 and stamped into each report. Reports include the engine version and verification timestamp. Changing a threshold or rule creates a distinguishable policy snapshot.

| Level | Evidence | Origin classification |
|---|---|---|
| A0 | User declaration or unsigned metadata | SELF_ASSERTED |
| A1 | Valid signature from an unapproved identity or untrusted C2PA signer | SELF_ASSERTED |
| A2 | Signature from an actor approved at the relevant chain time | SELF_ASSERTED for generation |
| A3 | A2 plus an anchor, temporal priority and at least one approved independent witness | TRUSTED, subject to integrity checks |

Deterministic resize, crop, compression and reencoding records can be trusted at A2 when output metadata and plausibility checks pass. Gateway records are trusted because the gateway actually computed the output from a bound input. This does not upgrade an unsupported origin elsewhere in the path.

Ordered verdicts:

1. Invalid evidence on the evaluated path produces PROVENANCE_INVALID.
2. A B1/B2/B3-bound image whose evaluated events are all trusted, without gaps or conflicts, produces VERIFIED.
3. At least one trusted path event produces PARTIALLY_VERIFIED when the full path cannot verify.
4. Bound A0–A2 origin claims produce UNVERIFIABLE with SELF_ASSERTED origin.
5. Absent evidence produces UNVERIFIABLE with unknown origin. Similarity candidates remain visible and unverified.

An RPC outage removes cached actor approval from the snapshot. The application cannot grant fresh trust using an old database mirror. Revocation is checked against anchor time: earlier records survive; records in the compromise interval are invalid. An unanchored event cannot prove it predates compromise.

Witness independence is an organization-level policy, not a mathematical guarantee. Registry administrators decide which organizations and keys are acceptable. Multiple witnesses from one organization count once. TEE and detector kinds cannot count without a server-side validated adapter; these adapters are intentionally unavailable in this release.

Valid C2PA content credentials alone cannot establish A3. Unknown ingredients appear as unknown relationships. C2PA names describe credential signers; the product does not infer a model from their pixels or signer display name.
