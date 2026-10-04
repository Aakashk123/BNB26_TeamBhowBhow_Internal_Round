# C2PA trust anchors

Place approved public CA certificate chains in PEM files in this directory before deployment. Never put private keys here. The native C2PA reader loads these anchors for signer trust validation, and remote manifest fetching remains disabled.

With no configured trust anchors, a cryptographically valid credential can remain an untrusted A1 claim. Adding a certificate does not establish A3 model-origin evidence: independent corroboration is still required.
