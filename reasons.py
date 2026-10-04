from enum import StrEnum


class Code(StrEnum):
    SIG_INVALID = "SIG_INVALID"
    SIGNER_MISMATCH = "SIGNER_MISMATCH"
    EVENT_HASH_MISMATCH = "EVENT_HASH_MISMATCH"
    PARENT_REF_MISMATCH = "PARENT_REF_MISMATCH"
    PARENT_CYCLE = "PARENT_CYCLE"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    C2PA_SIGNATURE_INVALID = "C2PA_SIGNATURE_INVALID"
    DIMENSION_MISMATCH = "DIMENSION_MISMATCH"
    FORMAT_MISMATCH = "FORMAT_MISMATCH"
    TIME_PARADOX = "TIME_PARADOX"
    KEY_COMPROMISED_WINDOW = "KEY_COMPROMISED_WINDOW"
    DERIVATION_IMPLAUSIBLE = "DERIVATION_IMPLAUSIBLE"
    AUDIT_CHAIN_BROKEN = "AUDIT_CHAIN_BROKEN"
    PARENT_UNAVAILABLE = "PARENT_UNAVAILABLE"
    UNATTESTED_TRANSFORMATION = "UNATTESTED_TRANSFORMATION"
    CONFLICTING_ORIGIN = "CONFLICTING_ORIGIN"
    NOT_ANCHORED = "NOT_ANCHORED"
    NO_CORROBORATION = "NO_CORROBORATION"
    ACTOR_UNAPPROVED = "ACTOR_UNAPPROVED"
    SELF_DECLARED_METADATA = "SELF_DECLARED_METADATA"
    SIMILARITY_ONLY = "SIMILARITY_ONLY"
    C2PA_VALID_UNTRUSTED_SIGNER = "C2PA_VALID_UNTRUSTED_SIGNER"
    CORROBORATED_BY_WITNESS = "CORROBORATED_BY_WITNESS"
    CORROBORATED_BY_TEE = "CORROBORATED_BY_TEE"
    CORROBORATED_BY_WATERMARK = "CORROBORATED_BY_WATERMARK"
    CHAIN_UNAVAILABLE = "CHAIN_UNAVAILABLE"
    C2PA_UNAVAILABLE = "C2PA_UNAVAILABLE"
    C2PA_UNEVALUABLE = "C2PA_UNEVALUABLE"
    GRAPH_LIMIT = "GRAPH_LIMIT"


def reason(code: Code, subject: str = "", severity: str = "warning") -> dict[str, str]:
    remediations = {
        Code.NO_CORROBORATION: "Request evidence from an approved independent witness.",
        Code.PARENT_UNAVAILABLE: "Register the missing signed parent event.",
        Code.SIMILARITY_ONLY: "Obtain a signed transformation; visual resemblance is insufficient.",
        Code.NOT_ANCHORED: "Anchor this signed event on the configured chain.",
        Code.CHAIN_UNAVAILABLE: "Restore the configured RPC connection and verify again.",
    }
    return {
        "code": code.value,
        "subject": subject,
        "severity": severity,
        "message": code.value.replace("_", " ").capitalize(),
        "remediation": remediations.get(code, "Inspect the evidence and verify with the responsible provider."),
    }
