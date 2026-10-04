# Privacy design

Owner-side SDK commitments use `keccak256(keccak256(field_name) || 128-bit random salt || keccak256(value))`. Up to six supported fields are padded to exactly eight leaves with random filler. Sorted-pair Keccak Merkle proofs are compatible with OpenZeppelin's proof helper. Only the root enters the signed event and chain.

The stateless disclosure endpoint receives a chosen field, value, salt and three proof siblings. It compares them with the root of an actually anchored event. It does not store requests. Validation errors omit submitted values. The UI clears the disclosed value after each attempt. The owner is responsible for protecting disclosure packages; losing the salts prevents later disclosure verification. The real-model wrapper can save only an age-encrypted package when explicitly requested.

Browser-only hashing avoids transmitting image bytes and supports B1 lookup only. Full image verification transmits the file for in-memory decoding, pixel hashes, perceptual discovery and C2PA inspection. The multipart spool threshold exceeds the hard upload limit to keep supported uploads in memory. nginx request buffering is disabled. Logs omit access requests and private request bodies. External reverse proxies must not log request bodies.

Opted-in history stores reports, not image bytes. Registration stores hashes and public evidence; a thumbnail is optional. EXIF and arbitrary C2PA assertions are not stored. Public event parameters use a closed schema and reject private fields such as prompt or seed. Model references are hashes, not prompts.

The privacy regression test uses a unique private prompt, registers an event with its commitment, anchors it on a real in-process EVM, verifies a correct disclosure and rejects a wrong salt. It inspects database rows, serialized report and response, and the transaction calldata for both literal and hex-encoded private text. This is not a proof against memory inspection, compromised operators or third-party infrastructure logging.

No zero-knowledge proof system is implemented. Selective disclosure reveals the disclosed value to the verifier; commitments are hiding only while salts remain secret and properly random.
