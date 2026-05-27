"""Impl email pour prod : Resend (https://resend.com)."""
from __future__ import annotations

import httpx


class ResendEmailSender:
    """Envoie un email via l'API HTTP de Resend.

    Doc API : https://resend.com/docs/api-reference/emails/send-email
    Format : POST https://api.resend.com/emails avec Authorization: Bearer <api_key>.
    """

    API_URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, from_addr: str) -> None:
        if not api_key:
            raise ValueError("RESEND_API_KEY is required when EMAIL_PROVIDER=resend")
        self._api_key = api_key
        self._from = from_addr

    async def send(self, to: str, subject: str, html_body: str) -> None:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"from": self._from, "to": [to], "subject": subject, "html": html_body}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self.API_URL, headers=headers, json=payload)
            response.raise_for_status()
