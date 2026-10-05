import jwt
import pytest

from app.security import create_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("s3cret-pass")
    assert h != "s3cret-pass"
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_token_carries_subject_and_role():
    payload = decode_token(create_token(42, "agent"))
    assert payload["sub"] == "42" and payload["role"] == "agent"


def test_expired_token_is_rejected():
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(create_token(1, "customer", ttl_minutes=-1))


def test_tampered_token_is_rejected():
    token = create_token(1, "customer")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(token[:-2] + ("aa" if not token.endswith("aa") else "bb"))
