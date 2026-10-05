"""Demo data. Idempotent: does nothing if users already exist.
Logins: agent@example.com / agent1234  and  customer@example.com / customer1234"""
from sqlalchemy import func, select

from . import services
from .db import SessionLocal
from .models import Role, User
from .security import hash_password


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User)):
            return
        agent = User(email="agent@example.com", password_hash=hash_password("agent1234"), role=Role.agent.value)
        ana = User(email="customer@example.com", password_hash=hash_password("customer1234"), role=Role.customer.value)
        luis = User(email="luis@example.com", password_hash=hash_password("customer1234"), role=Role.customer.value)
        db.add_all([agent, ana, luis])
        db.commit()

        d1 = services.open_dispute(db, ana, "ORD-1001", 4999, "Item arrived damaged")
        d2 = services.open_dispute(db, ana, "ORD-1002", 12900, "Charged twice for the same order")
        services.add_evidence(db, ana, d2.id, "Bank statement shows two identical charges on 12 Sept.")
        d3 = services.open_dispute(db, luis, "ORD-2001", 2500, "Never received the parcel")
        services.add_evidence(db, luis, d3.id, "Tracking shows delivered to the wrong address.")
        services.start_review(db, agent, d3.id)
        d4 = services.open_dispute(db, luis, "ORD-2002", 8900, "Subscription cancelled but still billed")
        services.add_evidence(db, luis, d4.id, "Cancellation confirmation email attached.")
        services.start_review(db, agent, d4.id)
        services.refund_dispute(db, agent, d4.id, "seed-refund-key-0001")
        d5 = services.open_dispute(db, luis, "ORD-2003", 1500, "Changed my mind")
        services.add_evidence(db, luis, d5.id, "No evidence, just a change of mind.")
        services.start_review(db, agent, d5.id)
        services.reject_dispute(db, agent, d5.id, "Change of mind is outside the dispute policy.")


if __name__ == "__main__":
    seed()
