def open_dispute(client, headers, amount_cents=5000, order_ref="ORD-1"):
    r = client.post("/disputes", headers=headers,
                    json={"order_ref": order_ref, "amount_cents": amount_cents, "reason": "Item arrived damaged"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def with_evidence(client, customer, **kw):
    did = open_dispute(client, customer, **kw)
    r = client.post(f"/disputes/{did}/evidence", headers=customer, json={"description": "Photo of the damage"})
    assert r.status_code == 200, r.text
    return did


def under_review(client, customer, agent, **kw):
    did = with_evidence(client, customer, **kw)
    r = client.post(f"/disputes/{did}/review", headers=agent)
    assert r.status_code == 200, r.text
    return did


def refund(client, agent, did, key):
    return client.post(f"/disputes/{did}/refund", headers={**agent, "Idempotency-Key": key})
