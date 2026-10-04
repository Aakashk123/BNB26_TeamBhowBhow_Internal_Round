# Threat model

ModelLedger verifies signed claims, exact file/pixel bindings, authority and corroboration according to an explicit policy. A signature proves control of a key, not that an AI model executed. Anchoring proves a claim was recorded by a time, not that the claim is true.

## Adversaries and mitigations

| Threat | Mitigation | Residual risk |
|---|---|---|
| Approved signer lies | A3 requires an independent approved witness and temporal priority | Provider and witness collusion can still deceive the system |
| Impersonation | EIP-712 recovery must match the actor's immutable signer | Compromised approved keys remain dangerous before compromise is known |
| Replay | Domain contains chain and contract; duplicate digests rejected | Wrong deployment configuration can lead the operator to a different registry |
| Signature or ancestry tampering | Recompute every event digest, params hash and parent binding | Malicious database operators can delete evidence; missing ancestry is a gap |
| Key compromise | On-chain retroactive revocation; time-window evaluation | The actual compromise time is an administrative judgment |
| Witness Sybils | Approved witness registry and organization deduplication | Organization independence cannot be established purely cryptographically |
| Unsigned image edits | New file/pixel fingerprint; similarity cannot transfer signatures | Severe crop, rotation or degradation can remove all recoverable evidence |
| Metadata forgery | Manual declarations remain A0; C2PA requires native validation | Certificate trust configuration and its operators are trusted |
| Database mutation | Immutable-event triggers; hash-chained audit records | A database superuser can remove triggers and rebuild a chain; external anchors are the independent evidence |
| SSRF | C2PA remote fetching disabled; no user-supplied retrieval URLs | Operators choose the RPC endpoint and must secure that configuration |
| Upload abuse | 25 MiB, 25 million pixels, static PNG/JPEG/WebP only, request caps and rate limiting | Native decoder vulnerabilities remain possible; update dependencies and isolate processes |
| Private data leakage | Closed public schemas, salted commitments, no source storage or body logs | Runtime memory and infrastructure operators can observe uploaded or disclosed data |
| Certificate forgery | EIP-191 signature on canonical report digest; issuer address checked | A historical certificate does not reflect later revocations without fresh verification |

## Not claimed

The system cannot identify an unknown AI model from an arbitrary image, prove truthfulness of colluding approved witnesses, restore missing information from irrecoverable blur, or certify philosophical originality. There is no production TEE verifier or accredited provider watermark detector. The experimental watermark is not a trust signal.

The development chain has public test accounts and must remain loopback-only. No contract or backend has received an independent professional security audit. Use the production configuration with a persistent external chain, fresh keys and HTTPS. Account-based multi-tenant authorization, distributed rate limiting and key custody through an HSM are deployment extensions, not features silently simulated here.
