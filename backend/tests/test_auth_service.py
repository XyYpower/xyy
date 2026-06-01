from datetime import timedelta

from app.services.auth_service import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_does_not_store_plain_text_and_verifies():
    hashed = hash_password("secret123")

    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong-password", hashed)


def test_access_token_round_trips_subject_and_type():
    token = create_access_token("user-1", expires_delta=timedelta(minutes=5))

    payload = decode_token(token)

    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"

