"""Initial schema and immutable evidence/audit tables."""
from alembic import op
from app.db.models import Base
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    immutable = ("events", "event_parents", "corroborations", "audit_log")
    if bind.dialect.name == "postgresql":
        op.execute("CREATE FUNCTION modelledger_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'append-only evidence table'; END $$")
        for table in immutable:
            op.execute(f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION modelledger_immutable()")
    else:
        for table in immutable:
            for action in ("UPDATE", "DELETE"):
                op.execute(f"CREATE TRIGGER immutable_{table}_{action} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only evidence table'); END")


def downgrade():
    raise RuntimeError("Destructive evidence downgrade is intentionally disabled; restore an approved backup")
