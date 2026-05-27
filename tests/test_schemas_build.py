import pytest
from pydantic import ValidationError

from schemas.build import BuildCreateIn, BuildUpdateIn, BuildOut, BuildListItem


def test_build_create_in_happy_path():
    data = BuildCreateIn(name="My Build", description="Some desc", data={"v": 1}, is_public=False)
    assert data.name == "My Build"
    assert data.is_public is False


def test_build_create_in_data_required():
    with pytest.raises(ValidationError):
        BuildCreateIn(name="X", data=None)  # type: ignore[arg-type]


def test_build_create_in_name_required():
    with pytest.raises(ValidationError):
        BuildCreateIn(data={"v": 1})  # type: ignore[call-arg]


def test_build_create_in_name_too_long():
    with pytest.raises(ValidationError):
        BuildCreateIn(name="x" * 101, data={"v": 1})


def test_build_create_in_description_too_long():
    with pytest.raises(ValidationError):
        BuildCreateIn(name="OK", description="x" * 2001, data={"v": 1})


def test_build_create_in_defaults():
    data = BuildCreateIn(name="X", data={})
    assert data.description is None
    assert data.is_public is False


def test_build_update_in_all_fields_optional():
    data = BuildUpdateIn()
    assert data.name is None
    assert data.data is None


def test_build_update_in_partial():
    data = BuildUpdateIn(name="New Name")
    assert data.name == "New Name"
    assert data.data is None


def test_build_list_item_from_attributes():
    import uuid
    from datetime import datetime, timezone
    class FakeBuild:
        id = uuid.uuid4()
        name = "Test"
        description = "Desc"
        is_public = True
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
    item = BuildListItem.model_validate(FakeBuild())
    assert item.name == "Test"
    assert item.is_public is True
