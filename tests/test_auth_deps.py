import uuid

import pytest
from fastapi import HTTPException

from core.auth_deps import get_current_user
from core import security
from models.user import User


async def _make_user(session):
    user = User(email="dep@example.com", pseudo="Dep", password_hash="$argon2id$h")
    session.add(user)
    await session.flush()
    return user


async def test_get_current_user_with_valid_cookie(db_session):
    user = await _make_user(db_session)
    token = security.encode_access_token(user.id)
    result = await get_current_user(access_token=token, session=db_session)
    assert result.id == user.id


async def test_get_current_user_without_cookie(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(access_token=None, session=db_session)
    assert exc.value.status_code == 401


async def test_get_current_user_invalid_token(db_session):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(access_token="not-a-jwt", session=db_session)
    assert exc.value.status_code == 401


async def test_get_current_user_unknown_user_id(db_session):
    # JWT signed for a user that does not exist in DB
    fake_token = security.encode_access_token(uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        await get_current_user(access_token=fake_token, session=db_session)
    assert exc.value.status_code == 401
