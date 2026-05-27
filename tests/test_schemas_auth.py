import pytest
from pydantic import ValidationError

from schemas.auth import LoginIn, RegisterIn, UserOut


def test_register_in_happy_path():
    data = RegisterIn(email="user@example.com", pseudo="Tarnished", password="GoodPass123")
    assert data.email == "user@example.com"
    assert data.pseudo == "Tarnished"


def test_register_in_password_must_have_uppercase():
    with pytest.raises(ValidationError):
        RegisterIn(email="u@e.com", pseudo="ABC", password="lowercase123")


def test_register_in_password_must_have_lowercase():
    with pytest.raises(ValidationError):
        RegisterIn(email="u@e.com", pseudo="ABC", password="UPPERCASE123")


def test_register_in_password_must_have_digit():
    with pytest.raises(ValidationError):
        RegisterIn(email="u@e.com", pseudo="ABC", password="NoDigitHere")


def test_register_in_password_too_short():
    with pytest.raises(ValidationError):
        RegisterIn(email="u@e.com", pseudo="ABC", password="Ab1short")  # 8 chars


def test_register_in_pseudo_too_short():
    with pytest.raises(ValidationError):
        RegisterIn(email="u@e.com", pseudo="Ab", password="GoodPass123")


def test_register_in_pseudo_invalid_chars():
    with pytest.raises(ValidationError):
        RegisterIn(email="u@e.com", pseudo="bad pseudo!", password="GoodPass123")


def test_register_in_invalid_email():
    with pytest.raises(ValidationError):
        RegisterIn(email="not-an-email", pseudo="Hero", password="GoodPass123")


def test_login_in_minimal():
    data = LoginIn(email="u@e.com", password="anything")
    assert data.email == "u@e.com"


def test_user_out_from_attributes():
    import uuid
    from datetime import datetime, timezone
    class FakeUser:
        id = uuid.uuid4()
        email = "u@e.com"
        pseudo = "Hero"
        email_verified_at = None
        created_at = datetime.now(timezone.utc)
    out = UserOut.model_validate(FakeUser())
    assert out.email == "u@e.com"
    assert out.email_verified_at is None
