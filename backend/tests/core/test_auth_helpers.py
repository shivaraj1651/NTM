from backend.app.core.auth_helpers import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    hashed = hash_password("devpass123")
    assert hashed != "devpass123"
    assert verify_password("devpass123", hashed) is True
    assert verify_password("wrong", hashed) is False
