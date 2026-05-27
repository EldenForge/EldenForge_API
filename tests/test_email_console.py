import logging

from core.email.console import ConsoleEmailSender


async def test_console_sender_logs_payload(caplog):
    sender = ConsoleEmailSender()
    caplog.set_level(logging.INFO, logger="core.email.console")
    await sender.send(
        to="test@example.com",
        subject="Hello",
        html_body="<p>Body</p>",
    )
    msgs = "\n".join(r.message for r in caplog.records)
    assert "test@example.com" in msgs
    assert "Hello" in msgs
    assert "<p>Body</p>" in msgs


async def test_factory_returns_console_when_configured(monkeypatch):
    from core.email import get_email_sender
    from core.email.console import ConsoleEmailSender

    monkeypatch.setattr("core.email.settings.email_provider", "console")
    sender = get_email_sender()
    assert isinstance(sender, ConsoleEmailSender)
