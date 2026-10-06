from tests.integration.helpers import open_dispute, refund, under_review, with_evidence


def test_full_lifecycle_with_audit_trail(client, customer, agent):
    did = open_dispute(client, customer)
    client.post(f"/disputes/{did}/evidence", headers=customer, json={"description": "Photo of the damage"})
    client.post(f"/disputes/{did}/review", headers=agent)
    r = refund(client, agent, did, "key-lifecycle-001")
    assert r.status_code == 201

    d = client.get(f"/disputes/{did}", headers=agent).json()
    assert d["status"] == "resolved" and d["resolution"] == "refund"
    assert len(d["evidence"]) == 1
    assert d["refund"]["amount_cents"] == 5000

    trail = [(a["action"], a["from_status"], a["to_status"], a["actor_role"], a["actor_email"]) for a in d["audit_logs"]]
    assert trail == [
        ("opened", None, "opened", "customer", "ana@example.com"),
        ("evidence_submitted", "opened", "evidence_submitted", "customer", "ana@example.com"),
        ("review_started", "evidence_submitted", "under_review", "agent", "agent@example.com"),
        ("refund_approved", "under_review", "resolved", "agent", "agent@example.com"),
    ]


def test_reject_path_requires_note_and_blocks_later_refund(client, customer, agent):
    did = under_review(client, customer, agent)
    assert client.post(f"/disputes/{did}/reject", headers=agent, json={"note": ""}).status_code == 422
    r = client.post(f"/disputes/{did}/reject", headers=agent, json={"note": "Outside policy window"})
    assert r.status_code == 200
    assert r.json()["resolution"] == "reject" and r.json()["resolution_note"] == "Outside policy window"
    assert refund(client, agent, did, "key-after-reject-1").status_code == 409


def test_invalid_transitions_return_409(client, customer, agent):
    did = open_dispute(client, customer)
    assert client.post(f"/disputes/{did}/review", headers=agent).status_code == 409  # no evidence yet
    assert refund(client, agent, did, "key-too-early-001").status_code == 409
    assert client.post(f"/disputes/{did}/reject", headers=agent, json={"note": "nope nope"}).status_code == 409


def test_evidence_locked_once_review_starts(client, customer, agent):
    did = under_review(client, customer, agent)
    r = client.post(f"/disputes/{did}/evidence", headers=customer, json={"description": "Late upload"})
    assert r.status_code == 409


def test_extra_evidence_is_logged_without_changing_status(client, customer):
    did = with_evidence(client, customer)
    r = client.post(f"/disputes/{did}/evidence", headers=customer, json={"description": "A second photo"})
    assert r.status_code == 200 and r.json()["status"] == "evidence_submitted"
    assert [a["action"] for a in r.json()["audit_logs"]][-1] == "evidence_added"


def test_customers_cannot_use_agent_actions(client, customer, agent):
    did = with_evidence(client, customer)
    assert client.post(f"/disputes/{did}/review", headers=customer).status_code == 403
    assert refund(client, customer, did, "key-customer-0001").status_code == 403
    assert client.post(f"/disputes/{did}/reject", headers=customer, json={"note": "hahaha"}).status_code == 403


def test_agents_cannot_open_disputes_or_submit_evidence(client, customer, agent):
    assert client.post("/disputes", headers=agent,
                       json={"order_ref": "X", "amount_cents": 100, "reason": "abc"}).status_code == 403
    did = open_dispute(client, customer)
    assert client.post(f"/disputes/{did}/evidence", headers=agent, json={"description": "abc"}).status_code == 403


def test_customer_cannot_see_someone_elses_dispute(client, customer, other_customer, agent):
    did = open_dispute(client, customer)
    assert client.get(f"/disputes/{did}", headers=other_customer).status_code == 404
    assert client.get("/disputes", headers=other_customer).json()["total"] == 0
    assert client.get("/disputes", headers=customer).json()["total"] == 1
    assert client.get("/disputes", headers=agent).json()["total"] == 1


def test_auth_required_and_bad_credentials(client):
    assert client.get("/disputes").status_code == 401
    assert client.get("/disputes", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.post("/auth/login", json={"email": "no@one.com", "password": "whatever1"}).status_code == 401


def test_register_creates_customer_only(client):
    r = client.post("/auth/register", json={"email": "new@example.com", "password": "password123"})
    assert r.status_code == 201 and r.json()["role"] == "customer"
    assert client.post("/auth/register", json={"email": "new@example.com", "password": "password123"}).status_code == 409


def test_list_filters_by_status_and_search(client, customer, other_customer, agent):
    a = open_dispute(client, customer, order_ref="ORD-ALPHA")
    b = under_review(client, other_customer, agent, order_ref="ORD-BETA")
    by_status = client.get("/disputes", headers=agent, params={"status": "under_review"}).json()
    assert [i["id"] for i in by_status["items"]] == [b]
    by_order = client.get("/disputes", headers=agent, params={"q": "alpha"}).json()
    assert [i["id"] for i in by_order["items"]] == [a]
    by_email = client.get("/disputes", headers=agent, params={"q": "luis@"}).json()
    assert [i["id"] for i in by_email["items"]] == [b]
    by_id = client.get("/disputes", headers=agent, params={"q": str(a)}).json()
    assert a in [i["id"] for i in by_id["items"]]
    assert client.get("/disputes", headers=agent, params={"status": "bogus"}).status_code == 422
