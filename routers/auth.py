"""Endpoints /auth/* — register, login, me (PR2a)."""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth_deps import get_current_user
from core.db import get_session
from core.email import email_sender
from core.settings import settings
from models.user import User
from schemas.auth import ForgotPasswordIn, LoginIn, RegisterIn, ResetPasswordIn, UserOut
from services.auth_service import (
    AccountLockedError,
    AuthService,
    EmailAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError as ServiceInvalidTokenError,
    PseudoAlreadyExistsError,
    TokenAlreadyUsedError,
    TokenExpiredError,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common: dict = dict(
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    if settings.cookie_domain:
        common["domain"] = settings.cookie_domain
    response.set_cookie(
        "access_token",
        access_token,
        max_age=settings.access_token_ttl_seconds,
        **common,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=settings.refresh_token_ttl_seconds,
        **common,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterIn,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    svc = AuthService(session, email_sender)
    try:
        user = await svc.register_user(data)
    except EmailAlreadyExistsError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    except PseudoAlreadyExistsError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Pseudo already taken")
    await session.commit()
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginIn,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    svc = AuthService(session, email_sender)
    try:
        result = await svc.login(data)
    except InvalidCredentialsError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    except AccountLockedError:
        raise HTTPException(status.HTTP_423_LOCKED, "Account locked")
    except EmailNotVerifiedError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Email not verified")
    await session.commit()
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return UserOut.model_validate(result.user)


@router.get("/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)


@router.get("/verify")
async def verify(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    svc = AuthService(session, email_sender)
    try:
        await svc.verify_email(token)
    except ServiceInvalidTokenError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token not found")
    except TokenAlreadyUsedError:
        raise HTTPException(status.HTTP_410_GONE, "Token already used")
    except TokenExpiredError:
        raise HTTPException(status.HTTP_410_GONE, "Token expired")
    await session.commit()
    return {"ok": True}


@router.post("/forgot", status_code=status.HTTP_202_ACCEPTED)
async def forgot(
    data: ForgotPasswordIn,
    session: AsyncSession = Depends(get_session),
) -> dict:
    svc = AuthService(session, email_sender)
    await svc.request_password_reset(data.email)
    await session.commit()
    # Always 202 — anti user enumeration
    return {"ok": True}


@router.post("/reset")
async def reset(
    data: ResetPasswordIn,
    session: AsyncSession = Depends(get_session),
) -> dict:
    svc = AuthService(session, email_sender)
    try:
        await svc.reset_password(data.token, data.new_password)
    except ServiceInvalidTokenError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token not found")
    except TokenAlreadyUsedError:
        raise HTTPException(status.HTTP_410_GONE, "Token already used")
    except TokenExpiredError:
        raise HTTPException(status.HTTP_410_GONE, "Token expired")
    await session.commit()
    return {"ok": True}


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    svc = AuthService(session, email_sender)
    try:
        result = await svc.refresh(refresh_token)
    except InvalidRefreshTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    await session.commit()
    _set_auth_cookies(response, result.access_token, result.refresh_token)
    return {"ok": True}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = AuthService(session, email_sender)
    await svc.logout(refresh_token)
    await session.commit()
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
