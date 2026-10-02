"""initial schema

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _ts(name: str = "created_at"):
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        _ts(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "disputes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("customer_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("order_ref", sa.String(64), nullable=False),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("resolution", sa.String(16), nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
        _ts(),
        _ts("updated_at"),
        sa.CheckConstraint("amount_cents > 0", name="ck_disputes_amount_positive"),
    )
    op.create_index("ix_disputes_customer_id", "disputes", ["customer_id"])
    op.create_index("ix_disputes_order_ref", "disputes", ["order_ref"])
    op.create_index("ix_disputes_status", "disputes", ["status"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dispute_id", sa.Integer, sa.ForeignKey("disputes.id"), nullable=False),
        sa.Column("submitted_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        _ts(),
    )
    op.create_index("ix_evidence_dispute_id", "evidence", ["dispute_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dispute_id", sa.Integer, sa.ForeignKey("disputes.id"), nullable=False),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        _ts(),
    )
    op.create_index("ix_audit_log_dispute_id", "audit_log", ["dispute_id"])

    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dispute_id", sa.Integer, sa.ForeignKey("disputes.id"), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("amount_cents", sa.Integer, nullable=False),
        sa.Column("issued_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        _ts(),
    )


def downgrade() -> None:
    for table in ("refunds", "audit_log", "evidence", "disputes", "users"):
        op.drop_table(table)
