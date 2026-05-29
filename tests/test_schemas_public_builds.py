import pytest
from pydantic import ValidationError

from schemas.build import ALLOWED_TAGS, BuildCreateIn, PublicBuildListItem


def test_allowed_tags_contains_expected():
    for t in ("Strength", "PvP", "Bleed", "Boss"):
        assert t in ALLOWED_TAGS


def test_build_create_accepts_valid_tags():
    b = BuildCreateIn(name="B", data={}, tags=["Strength", "PvP"])
    assert b.tags == ["Strength", "PvP"]


def test_build_create_defaults_empty_tags():
    b = BuildCreateIn(name="B", data={})
    assert b.tags == []


def test_build_create_rejects_unknown_tag():
    with pytest.raises(ValidationError):
        BuildCreateIn(name="B", data={}, tags=["NotARealTag"])


def test_public_list_item_from_attributes():
    import uuid
    from datetime import datetime, timezone
    class Row:
        id = uuid.uuid4()
        name = "B"
        description = None
        tags = ["PvP"]
        like_count = 3
        created_at = datetime.now(timezone.utc)
        author_pseudo = "Hero"
        liked_by_me = False
    item = PublicBuildListItem.model_validate(Row())
    assert item.author_pseudo == "Hero"
    assert item.like_count == 3
