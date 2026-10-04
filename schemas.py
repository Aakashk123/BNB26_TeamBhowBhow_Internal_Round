from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Hash = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{64}$")]
Address = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{40}$")]
Signature = Annotated[str, Field(pattern=r"^0x[0-9a-fA-F]{130}$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Op(Strict):
    action: Literal[
        "RESIZE",
        "CROP",
        "COMPRESS",
        "REENCODE",
        "FILTER",
        "BLUR",
        "AI_GENERATION",
        "AI_EDIT",
        "AI_UPSCALE",
        "HUMAN_EDIT",
        "COMPOSITE",
        "PUBLISH",
        "OTHER",
    ]
    width: int | None = Field(None, ge=1, le=8192)
    height: int | None = Field(None, ge=1, le=8192)
    box: list[int] | None = Field(None, min_length=4, max_length=4)
    quality: int | None = Field(None, ge=10, le=100)
    format: Literal["PNG", "JPEG", "WEBP"] | None = None
    radius: float | None = Field(None, ge=0, le=30)
    factor: float | None = Field(None, ge=0.2, le=3)


class Params(Strict):
    width: int = Field(ge=1, le=25000)
    height: int = Field(ge=1, le=25000)
    mime: Literal["image/png", "image/jpeg", "image/webp"]
    ops: list[Op] = Field(min_length=1, max_length=16)
    simulated: bool = False


class Payload(Strict):
    actorId: Hash
    action: int = Field(ge=1, le=13)
    modelRef: Hash
    parentEventIds: list[Hash] = Field(max_length=16)
    inputSha256: list[Hash] = Field(max_length=16)
    outputSha256: Hash
    outputPixelSha256: Hash
    outputPHash: int = Field(ge=0, lt=2**64)
    paramsHash: Hash
    privateRoot: Hash
    claimedAt: int = Field(ge=0, lt=2**64)
    nonce: Hash

    @field_validator("actorId", "modelRef", "outputSha256", "outputPixelSha256", "paramsHash", "privateRoot", "nonce")
    @classmethod
    def normalize_hash(cls, value):
        return value.lower()

    @field_validator("parentEventIds", "inputSha256")
    @classmethod
    def normalize_hashes(cls, values):
        return [value.lower() for value in values]

    @model_validator(mode="after")
    def alignment(self):
        if len(self.parentEventIds) != len(self.inputSha256):
            raise ValueError("Parent events and consumed hashes must align")
        return self


class EventIn(Strict):
    payload: Payload
    params: Params
    signature: Signature


class ActorIn(Strict):
    actor_id: Hash
    name: str = Field(min_length=1, max_length=120)
    provider: str = Field(min_length=1, max_length=120)
    kind: Literal["MODEL", "TOOL", "HUMAN", "PLATFORM"]
    signature: Signature


class Evidence(Strict):
    observed: bool
    method: Literal["direct_observation", "tee", "provider_detector"]
    simulated: bool = False
    measurement: Hash | None = None


class CorroborationIn(Strict):
    kind: int = Field(ge=1, le=3)
    evidence: Evidence
    signature: Signature


class HashRequest(Strict):
    sha256: Hash
    save_history: bool = False


class DisclosureIn(Strict):
    event_hash: Hash
    field: str = Field(max_length=40)
    value: str = Field(max_length=16384)
    salt: str = Field(pattern=r"^0x[0-9a-fA-F]{32}$")
    proof: list[Hash] = Field(min_length=3, max_length=3)


class AdminIn(Strict):
    effective_from: int | None = Field(None, gt=0)
    raw_transaction: str | None = Field(None, max_length=8192, pattern=r"^0x[0-9a-fA-F]+$")


class Reason(BaseModel):
    code: str
    subject: str
    severity: str
    message: str
    remediation: str


class Counts(BaseModel):
    verified: int
    unverified: int
    gaps: int
    conflicts: int
    tamper_warnings: int


class Report(BaseModel):
    report_id: str
    engine_version: str
    policy_hash: str
    timestamp: str
    input: dict
    status: Literal["VERIFIED", "PARTIALLY_VERIFIED", "PROVENANCE_INVALID", "UNVERIFIABLE"]
    origin_trust: Literal["TRUSTED", "SELF_ASSERTED", "UNVERIFIABLE"]
    binding: dict
    origin: dict
    graph: dict
    counts: Counts
    reasons: list[Reason]
    candidates: list[dict]
    privacy: dict
    simulated: bool
    saved: bool
    chain: dict
