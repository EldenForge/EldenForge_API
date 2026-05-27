import time
import uuid

import pytest

from core import security


def test_hash_password_returns_argon2id_string():
    h = security.hash_password("hunter2-Strong!")
    assert h.startswith("$argon2id$")
    assert h != "hunter2-Strong!"  # never store plaintext


def test_verify_password_roundtrip():
    h = security.hash_password("good-Password-1")
    assert security.verify_password("good-Password-1", h) is True
    assert security.verify_password("wrong", h) is False


def test_encode_decode_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = security.encode_access_token(user_id)
    decoded = security.decode_access_token(token)
    assert decoded == user_id


def test_decode_access_token_rejects_tampered():
    user_id = uuid.uuid4()
    token = security.encode_access_token(user_id)
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(security.InvalidTokenError):
        security.decode_access_token(tampered)


def test_decode_access_token_rejects_expired(monkeypatch):
    # Force un TTL minuscule pour cette assertion
    monkeypatch.setattr(security.settings, "access_token_ttl_seconds", 1)
    token = security.encode_access_token(uuid.uuid4())
    time.sleep(1.5)
    with pytest.raises(security.InvalidTokenError):
        security.decode_access_token(token)


def test_encode_refresh_token_returns_raw_and_hash():
    raw, h = security.encode_refresh_token()
    assert isinstance(raw, str) and len(raw) >= 40  # 32 bytes urlsafe ≈ 43 chars
    assert isinstance(h, str) and len(h) == 64       # sha256 hex
    assert security.sha256_hex(raw) == h


def test_generate_url_safe_token_length():
    t = security.generate_url_safe_token(32)
    assert isinstance(t, str)
    assert len(t) >= 40  # 32 bytes en base64 urlsafe sans padding


def test_sha256_hex_is_deterministic():
    assert security.sha256_hex("abc") == security.sha256_hex("abc")
    assert security.sha256_hex("abc") != security.sha256_hex("abd")
    assert len(security.sha256_hex("anything")) == 64
