"""Impl email pour dev : log au stdout via le logger nommé."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ConsoleEmailSender:
    """Pour le développement local. Tous les emails sont loggés au lieu d'être envoyés."""

    async def send(self, to: str, subject: str, html_body: str) -> None:
        logger.info(
            "[EMAIL] to=%s subject=%s\n%s",
            to,
            subject,
            html_body,
        )
