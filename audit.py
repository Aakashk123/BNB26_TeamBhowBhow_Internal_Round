from sqlalchemy import select, text

from app.core.canonical import digest
from app.core.eip712 import ZERO
from app.db.models import AuditLog


def append(db, operation, subject):
    # Serialize writers for the full transaction, not just the last row read.
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(731428590)"))
    last = db.scalar(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    previous = last.row_hash if last else ZERO
    body = {"operation": operation, "subject": subject}
    row = AuditLog(prev_hash=previous, body=body, row_hash=digest({"prev_hash": previous, "body": body}))
    db.add(row)
    db.flush()


def verify(db):
    previous = ZERO
    count = 0
    for row in db.scalars(select(AuditLog).order_by(AuditLog.id)):
        if row.prev_hash != previous or row.row_hash != digest({"prev_hash": previous, "body": row.body}):
            return {"valid": False, "rows": count, "broken_at": row.id, "reason": "AUDIT_CHAIN_BROKEN"}
        previous = row.row_hash
        count += 1
    return {"valid": True, "rows": count, "head": previous}
