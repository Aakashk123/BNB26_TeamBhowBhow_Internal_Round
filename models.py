import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid(prefix):
    return prefix + "-" + uuid.uuid4().hex[:16].upper()


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Lineage(Base):
    __tablename__ = "lineages"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: uid("LG"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Version(Base):
    __tablename__ = "versions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: uid("IMG"))
    lineage_id: Mapped[str] = mapped_column(ForeignKey("lineages.id"), index=True)
    sha256: Mapped[str] = mapped_column(String(66), unique=True, index=True)
    pixel_sha256: Mapped[str] = mapped_column(String(66), index=True)
    phash: Mapped[dict] = mapped_column(JSON)
    mime: Mapped[str] = mapped_column(String(32))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    bytes: Mapped[int] = mapped_column(Integer)
    c2pa: Mapped[dict] = mapped_column(JSON)
    declared_origin: Mapped[str | None] = mapped_column(String(120), nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Actor(Base):
    __tablename__ = "actors"
    actor_id: Mapped[str] = mapped_column(String(66), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(32))
    org_id: Mapped[str] = mapped_column(String(66))
    signer_address: Mapped[str] = mapped_column(String(42))
    status: Mapped[int] = mapped_column(Integer)
    approved_at: Mapped[int] = mapped_column(BigInteger, default=0)
    revoked_from: Mapped[int] = mapped_column(BigInteger, default=0)
    model_measurement: Mapped[str] = mapped_column(String(66))


class Event(Base):
    __tablename__ = "events"
    event_hash: Mapped[str] = mapped_column(String(66), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(66), index=True)
    output_version: Mapped[str] = mapped_column(ForeignKey("versions.id"), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    params: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(String(132))
    gateway_replay: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EventParent(Base):
    __tablename__ = "event_parents"
    child_event: Mapped[str] = mapped_column(ForeignKey("events.event_hash"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_event: Mapped[str] = mapped_column(String(66), index=True)
    input_sha256: Mapped[str] = mapped_column(String(66))


class Corroboration(Base):
    __tablename__ = "corroborations"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: uid("COR"))
    event_hash: Mapped[str] = mapped_column(ForeignKey("events.event_hash"), index=True)
    kind: Mapped[int] = mapped_column(Integer)
    evidence_hash: Mapped[str] = mapped_column(String(66))
    evidence: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(String(132))


class VerificationReport(Base):
    __tablename__ = "verification_reports"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner: Mapped[str] = mapped_column(String(66), index=True)
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Certificate(Base):
    __tablename__ = "certificates"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    report_id: Mapped[str] = mapped_column(String(40), index=True)
    envelope: Mapped[dict] = mapped_column(JSON)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prev_hash: Mapped[str] = mapped_column(String(66))
    row_hash: Mapped[str] = mapped_column(String(66))
    body: Mapped[dict] = mapped_column(JSON)
