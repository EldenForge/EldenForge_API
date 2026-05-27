"""Primitives de sécurité : hash de mot de passe (Argon2id), JWT, tokens aléatoires.

Stateless — pas de dépendance à la BDD. Réutilisable par auth_service et auth_deps.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .settings import settings


class InvalidTokenError(Exception):
    """Levée quand un JWT est invalide (expiré, signature wrong, malformé)."""


_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash Argon2id (string standard avec salt + params embarqués)."""
    return _hasher.hash(plain)


def verify_password(plain: str, stored_hash: str) -> bool:
    try:
        _hasher.verify(stored_hash, plain)
        return True
    except VerifyMismatchError:
        return False


def encode_access_token(user_id: uuid.UUID) -> str:
    """JWT HS256 contenant le user_id en 'sub' + exp."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> uuid.UUID:
    """Décode et valide le JWT. Retourne le user_id. Raise InvalidTokenError sinon."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as e:
        raise InvalidTokenError(str(e)) from e
    sub = payload.get("sub")
    if not sub:
        raise InvalidTokenError("Missing 'sub' claim")
    try:
        return uuid.UUID(sub)
    except (ValueError, TypeError) as e:
        raise InvalidTokenError(f"Invalid sub: {sub}") from e


def generate_url_safe_token(n_bytes: int = 32) -> str:
    """Token cryptographiquement aléatoire, url-safe (utilisé pour email verif et reset)."""
    return secrets.token_urlsafe(n_bytes)


def sha256_hex(value: str) -> str:
    """SHA-256 hex digest. Utilisé pour stocker un hash des tokens en BDD."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def encode_refresh_token() -> tuple[str, str]:
    """Génère (raw_token_pour_cookie, sha256_hash_pour_BDD)."""
    raw = generate_url_safe_token(32)
    return raw, sha256_hex(raw)
