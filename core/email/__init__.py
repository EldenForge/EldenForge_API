"""Factory EmailSender — sélectionne l'impl selon settings.email_provider."""
from __future__ import annotations

from core.settings import settings

from .base import EmailSender
from .console import ConsoleEmailSender
from .resend import ResendEmailSender


def get_email_sender() -> EmailSender:
    provider = settings.email_provider.lower()
    if provider == "console":
        return ConsoleEmailSender()
    if provider == "resend":
        return ResendEmailSender(settings.resend_api_key, settings.email_from)
    raise ValueError(
        f"Unknown EMAIL_PROVIDER: {settings.email_provider!r} "
        f"(expected 'console' or 'resend')"
    )


# Singleton calculé au démarrage du module.
email_sender: EmailSender = get_email_sender()


__all__ = ["EmailSender", "ConsoleEmailSender", "ResendEmailSender", "get_email_sender", "email_sender"]
