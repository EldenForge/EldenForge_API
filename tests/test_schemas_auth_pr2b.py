import pytest
from pydantic import ValidationError

from schemas.auth import ForgotPasswordIn, ResetPasswordIn


def test_forgot_password_in_happy_path():
    data = ForgotPasswordIn(email="user@example.com")
    assert data.email == "user@example.com"


def test_forgot_password_in_invalid_email():
    with pytest.raises(ValidationError):
        ForgotPasswordIn(email="not-an-email")


def test_reset_password_in_happy_path():
    data = ResetPasswordIn(token="some-raw-token", new_password="NewGoodPass1")
    assert data.token == "some-raw-token"
    assert data.new_password == "NewGoodPass1"


def test_reset_password_in_weak_password_rejected():
    with pytest.raises(ValidationError):
        ResetPasswordIn(token="t", new_password="weak")


def test_reset_password_in_password_missing_digit():
    with pytest.raises(ValidationError):
        ResetPasswordIn(token="t", new_password="NoDigitHere")


def test_reset_password_in_token_required():
    with pytest.raises(ValidationError):
        ResetPasswordIn(new_password="GoodPass123")  # type: ignore[call-arg]
