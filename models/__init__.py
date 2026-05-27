from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base déclarative partagée par tous les modèles ORM du projet."""


from .user import User  # noqa: E402
from .build import Build  # noqa: E402
from .email_token import EmailToken  # noqa: E402
from .refresh_token import RefreshToken  # noqa: E402

__all__ = ["Base", "User", "Build", "EmailToken", "RefreshToken"]
