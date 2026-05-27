"""Interface EmailSender — Protocol structural pour permettre des impls multiples."""
from __future__ import annotations

from typing import Protocol


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, html_body: str) -> None: ...
