"""Service métier pour l'authentification.

Une instance par requête : reçoit la session DB et l'email sender en injection.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import security
from core.email.base import EmailSender
from core.settings import settings
from models.email_token import EmailToken
from models.refresh_token import RefreshToken
from models.user import User
from schemas.auth import LoginIn, RegisterIn


class AuthError(Exception):
    """Base pour les erreurs métier auth (le router les traduit en HTTPException)."""


class EmailAlreadyExistsError(AuthError):
    pass


class PseudoAlreadyExistsError(AuthError):
    pass


class InvalidCredentialsError(AuthError):
    pass


class EmailNotVerifiedError(AuthError):
    pass


class InvalidRefreshTokenError(AuthError):
    """Refresh token unknown, expired, or already revoked."""


class AccountLockedError(AuthError):
    """Account temporarily locked due to repeated failed login attempts."""


class InvalidTokenError(AuthError):
    """Token inconnu ou de purpose incorrect."""


class TokenExpiredError(AuthError):
    pass


class TokenAlreadyUsedError(AuthError):
    pass


@dataclass
class LoginResult:
    user: User
    access_token: str
    refresh_token: str  # raw, à mettre dans le cookie httpOnly


class AuthService:
    def __init__(self, session: AsyncSession, email_sender: EmailSender) -> None:
        self._session = session
        self._sender = email_sender

    async def register_user(self, data: RegisterIn) -> User:
        # 1. Check uniqueness (citext → case-insensitive automatic)
        existing_email = (
            await self._session.execute(select(User.id).where(User.email == data.email))
        ).first()
        if existing_email:
            raise EmailAlreadyExistsError(data.email)

        existing_pseudo = (
            await self._session.execute(select(User.id).where(User.pseudo == data.pseudo))
        ).first()
        if existing_pseudo:
            raise PseudoAlreadyExistsError(data.pseudo)

        # 2. Create user (email_verified_at = NULL)
        user = User(
            email=data.email,
            pseudo=data.pseudo,
            password_hash=security.hash_password(data.password),
        )
        self._session.add(user)
        await self._session.flush()  # to get the id

        # 3. Create email verification token
        raw_token = security.generate_url_safe_token(32)
        token_hash = security.sha256_hex(raw_token)
        expires = datetime.now(timezone.utc) + timedelta(
            seconds=settings.email_verification_ttl_seconds
        )
        token = EmailToken(
            user_id=user.id,
            token_hash=token_hash,
            purpose="email_verification",
            expires_at=expires,
        )
        self._session.add(token)
        await self._session.flush()

        # 4. Send verification email
        verify_url = f"{settings.frontend_base_url}/verify?token={raw_token}"
        await self._sender.send(
            to=user.email,
            subject="Welcome to EldenForge — verify your email",
            html_body=(
                f"<p>Welcome, {user.pseudo} !</p>"
                f"<p>Please verify your email by clicking the link below :</p>"
                f"<p><a href=\"{verify_url}\">{verify_url}</a></p>"
                f"<p>This link expires in 24 hours.</p>"
            ),
        )

        return user

    async def login(self, data: LoginIn) -> LoginResult:
        # 1. Find user
        user = (
            await self._session.execute(select(User).where(User.email == data.email))
        ).scalar_one_or_none()
        if user is None:
            raise InvalidCredentialsError("No user with this email")

        # 2. Check lockout (before any password attempt)
        now = datetime.now(timezone.utc)
        if user.locked_until is not None and user.locked_until > now:
            raise AccountLockedError(f"Locked until {user.locked_until.isoformat()}")

        # 3. Verify password (Argon2id)
        if not security.verify_password(data.password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= settings.max_failed_logins:
                user.locked_until = now + timedelta(seconds=settings.lockout_duration_seconds)
            await self._session.flush()
            raise InvalidCredentialsError("Wrong password")

        # 4. Reject if email not verified
        if user.email_verified_at is None:
            raise EmailNotVerifiedError(user.email)

        # 5. Successful login — reset counters + update last_login_at
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now

        # 6. Issue access + refresh tokens
        access = security.encode_access_token(user.id)
        refresh_raw, refresh_hash = security.encode_refresh_token()
        refresh_row = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=now + timedelta(seconds=settings.refresh_token_ttl_seconds),
        )
        self._session.add(refresh_row)
        await self._session.flush()

        return LoginResult(user=user, access_token=access, refresh_token=refresh_raw)

    async def verify_email(self, raw_token: str) -> None:
        token_hash = security.sha256_hex(raw_token)
        token = (
            await self._session.execute(
                select(EmailToken).where(
                    EmailToken.token_hash == token_hash,
                    EmailToken.purpose == "email_verification",
                )
            )
        ).scalar_one_or_none()
        if token is None:
            raise InvalidTokenError("Token not found or wrong purpose")

        if token.used_at is not None:
            raise TokenAlreadyUsedError(str(token.id))

        if token.expires_at < datetime.now(timezone.utc):
            raise TokenExpiredError(str(token.id))

        # Mark token used + activate user
        now = datetime.now(timezone.utc)
        token.used_at = now

        user = await self._session.get(User, token.user_id)
        if user is not None:
            user.email_verified_at = now

        await self._session.flush()

    async def request_password_reset(self, email: str) -> None:
        """Génère un token de reset et envoie un email. Silencieux si user inconnu (anti enum)."""
        user = (
            await self._session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if user is None:
            return  # silent — anti user enumeration

        raw_token = security.generate_url_safe_token(32)
        token_hash = security.sha256_hex(raw_token)
        expires = datetime.now(timezone.utc) + timedelta(
            seconds=settings.password_reset_ttl_seconds
        )
        token = EmailToken(
            user_id=user.id,
            token_hash=token_hash,
            purpose="password_reset",
            expires_at=expires,
        )
        self._session.add(token)
        await self._session.flush()

        reset_url = f"{settings.frontend_base_url}/reset?token={raw_token}"
        await self._sender.send(
            to=user.email,
            subject="EldenForge — reset your password",
            html_body=(
                f"<p>Hi {user.pseudo},</p>"
                f"<p>Click the link below to reset your password :</p>"
                f"<p><a href=\"{reset_url}\">{reset_url}</a></p>"
                f"<p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>"
            ),
        )

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        token_hash = security.sha256_hex(raw_token)
        token = (
            await self._session.execute(
                select(EmailToken).where(
                    EmailToken.token_hash == token_hash,
                    EmailToken.purpose == "password_reset",
                )
            )
        ).scalar_one_or_none()
        if token is None:
            raise InvalidTokenError("Token not found or wrong purpose")

        if token.used_at is not None:
            raise TokenAlreadyUsedError(str(token.id))

        if token.expires_at < datetime.now(timezone.utc):
            raise TokenExpiredError(str(token.id))

        user = await self._session.get(User, token.user_id)
        if user is None:
            raise InvalidTokenError("User no longer exists")

        # Hash new password + mark token used
        user.password_hash = security.hash_password(new_password)
        token.used_at = datetime.now(timezone.utc)

        await self._session.flush()

    async def refresh(self, raw_refresh_token: str) -> LoginResult:
        """Rotation : valide le refresh raw, révoque l'ancien, émet une nouvelle paire."""
        old_hash = security.sha256_hex(raw_refresh_token)
        old_row = (
            await self._session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == old_hash)
            )
        ).scalar_one_or_none()
        if old_row is None:
            raise InvalidRefreshTokenError("Unknown refresh token")
        if old_row.revoked_at is not None:
            raise InvalidRefreshTokenError("Refresh token already revoked")
        if old_row.expires_at < datetime.now(timezone.utc):
            raise InvalidRefreshTokenError("Refresh token expired")

        old_row.revoked_at = datetime.now(timezone.utc)

        user = await self._session.get(User, old_row.user_id)
        if user is None:
            raise InvalidRefreshTokenError("User no longer exists")

        access = security.encode_access_token(user.id)
        new_raw, new_hash = security.encode_refresh_token()
        new_row = RefreshToken(
            user_id=user.id,
            token_hash=new_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.refresh_token_ttl_seconds),
        )
        self._session.add(new_row)
        await self._session.flush()

        return LoginResult(user=user, access_token=access, refresh_token=new_raw)

    async def logout(self, raw_refresh_token: str | None) -> None:
        """Révoque le refresh token. Silencieux/idempotent si déjà révoqué ou inconnu."""
        if not raw_refresh_token:
            return
        token_hash = security.sha256_hex(raw_refresh_token)
        row = (
            await self._session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        if row is None:
            return
        if row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            await self._session.flush()
