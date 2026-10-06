import threading

import pytest
from sqlalchemy import func, select

from app import services
from app.errors import Conflict
from app.models import AuditLog, Refund, User
from tests.integration.helpers import refund, under_review


def _refund_count(session_factory, did):
    with session_factory() as db:
        return db.scalar(select(func.count()).select_from(Refund).where(Refund.dispute_id == did))


def test_refund_cannot_be_applied_twice(client, customer, agent, session_factory):
    """The headline guarantee: whatever the caller does, a dispute is refunded exactly once."""
    did = under_review(client, customer, agent)

    first = refund(client, agent, did, "key-aaaa-0001")
    assert first.status_code == 201

    # A different key is a different request: it must be refused, not applied again.
    second = refund(client, agent, did, "key-bbbb-0002")
    assert second.status_code == 409

    assert _refund_count(session_factory, did) == 1
    with session_factory() as db:
        refund_logs = db.scalar(select(func.count()).select_from(AuditLog)
                                .where(AuditLog.dispute_id == did, AuditLog.action == "refund_approved"))
    assert refund_logs == 1


def test_retry_with_same_key_replays_the_original_result(client, customer, agent, session_factory):
    did = under_review(client, customer, agent)
    first = refund(client, agent, did, "key-retry-0001")
    retry = refund(client, agent, did, "key-retry-0001")

    assert first.status_code == 201 and first.json()["replayed"] is False
    assert retry.status_code == 200 and retry.json()["replayed"] is True
    assert retry.headers["Idempotent-Replay"] == "true"
    assert retry.json()["id"] == first.json()["id"]
    assert _refund_count(session_factory, did) == 1


def test_same_key_on_a_different_dispute_is_rejected(client, customer, agent):
    a = under_review(client, customer, agent, order_ref="A")
    b = under_review(client, customer, agent, order_ref="B")
    assert refund(client, agent, a, "key-shared-0001").status_code == 201
    assert refund(client, agent, b, "key-shared-0001").status_code == 422


def test_idempotency_key_header_is_required(client, customer, agent):
    did = under_review(client, customer, agent)
    assert client.post(f"/disputes/{did}/refund", headers=agent).status_code == 422


def _race(session_factory, agent_id, did, keys):
    """Fire len(keys) refund attempts at the same instant, each on its own DB session."""
    barrier = threading.Barrier(len(keys))
    results = []

    def attempt(key):
        with session_factory() as db:
            agent = db.get(User, agent_id)
            barrier.wait()
            try:
                _, r, replayed = services.refund_dispute(db, agent, did, key)
                results.append(("ok", r.id, replayed))
            except Conflict:
                results.append(("conflict", None, None))

    threads = [threading.Thread(target=attempt, args=(k,)) for k in keys]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return results


def _agent_id(session_factory):
    with session_factory() as db:
        return db.scalar(select(User.id).where(User.email == "agent@example.com"))


def test_concurrent_double_click_with_different_keys_refunds_once(client, customer, agent, session_factory):
    did = under_review(client, customer, agent)
    results = _race(session_factory, _agent_id(session_factory), did, [f"key-race-{i:04d}" for i in range(8)])
    assert [r[0] for r in results].count("ok") == 1
    assert [r[0] for r in results].count("conflict") == 7
    assert _refund_count(session_factory, did) == 1


def test_concurrent_retries_with_the_same_key_all_see_one_refund(client, customer, agent, session_factory):
    did = under_review(client, customer, agent)
    results = _race(session_factory, _agent_id(session_factory), did, ["key-same-00001"] * 8)
    assert all(r[0] == "ok" for r in results)
    assert len({r[1] for r in results}) == 1  # everyone got the same refund id
    assert [r[2] for r in results].count(False) == 1  # exactly one actually performed it
    assert _refund_count(session_factory, did) == 1


def test_database_itself_refuses_a_second_refund_row(client, customer, agent, session_factory):
    """Even if application code were buggy, UNIQUE(dispute_id) stops a double refund."""
    from sqlalchemy.exc import IntegrityError

    did = under_review(client, customer, agent)
    assert refund(client, agent, did, "key-db-guard-001").status_code == 201
    with session_factory() as db:
        db.add(Refund(dispute_id=did, idempotency_key="key-db-guard-002", amount_cents=1, issued_by=_agent_id(session_factory)))
        with pytest.raises(IntegrityError):
            db.commit()
