import pytest
from pydantic import ValidationError

from schemas.user import ChangePasswordIn, UpdatePseudoIn


def test_update_pseudo_in_happy_path():
    data = UpdatePseudoIn(pseudo="NewPseudo")
    assert data.pseudo == "NewPseudo"


def test_update_pseudo_in_too_short():
    with pytest.raises(ValidationError):
        UpdatePseudoIn(pseudo="ab")


def test_update_pseudo_in_invalid_chars():
    with pytest.raises(ValidationError):
        UpdatePseudoIn(pseudo="bad pseudo!")


def test_change_password_in_happy_path():
    data = ChangePasswordIn(current_password="OldPass123", new_password="NewPass987")
    assert data.current_password == "OldPass123"
    assert data.new_password == "NewPass987"


def test_change_password_in_new_password_weak():
    with pytest.raises(ValidationError):
        ChangePasswordIn(current_password="OldPass123", new_password="weak")


def test_change_password_in_new_password_no_digit():
    with pytest.raises(ValidationError):
        ChangePasswordIn(current_password="OldPass123", new_password="NoDigitHere")
