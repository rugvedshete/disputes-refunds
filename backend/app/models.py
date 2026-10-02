import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Role(str, enum.Enum):
    customer = "customer"
    agent = "agent"


class Status(str, enum.Enum):
    opened = "opened"
    evidence_submitted = "evidence_submitted"
    under_review = "under_review"
    resolved = "resolved"


class Resolution(str, enum.Enum):
    refund = "refund"
    reject = "reject"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Dispute(Base):
    __tablename__ = "disputes"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="ck_disputes_amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_ref: Mapped[str] = mapped_column(String(64), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=Status.opened.value, index=True)
    resolution: Mapped[str | None] = mapped_column(String(16), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer: Mapped[User] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(order_by="Evidence.id")
    audit_logs: Mapped[list["AuditLog"]] = relationship(order_by="AuditLog.id")
    refund: Mapped["Refund | None"] = relationship(uselist=False)

    @property
    def customer_email(self) -> str:
        return self.customer.email


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    dispute_id: Mapped[int] = mapped_column(ForeignKey("disputes.id"), index=True)
    submitted_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Append-only: one row per state change (or evidence addition), with the acting user."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    dispute_id: Mapped[int] = mapped_column(ForeignKey("disputes.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(32))
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    actor: Mapped[User] = relationship()

    @property
    def actor_email(self) -> str:
        return self.actor.email


class Refund(Base):
    """UNIQUE(dispute_id) is the last line of defence: the DB itself refuses a second refund."""

    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(primary_key=True)
    dispute_id: Mapped[int] = mapped_column(ForeignKey("disputes.id"), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    issued_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
