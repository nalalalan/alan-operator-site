from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import smtplib

from app.core.config import settings


@dataclass
class PorkbunSendResult:
    message_id: str
    accepted_recipients: list[str]
    raw_provider: str


class PorkbunSMTPClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
    ) -> None:
        self.host = host or settings.buyer_acq_smtp_host
        self.port = int(port or settings.buyer_acq_smtp_port)
        self.username = username or settings.buyer_acq_mailbox_address
        self.password = password or settings.buyer_acq_mailbox_password
        self.from_email = from_email or settings.buyer_acq_mailbox_address
        if not self.username or not self.password:
            raise ValueError("buyer acquisition SMTP username/password are required")

    def send_plain_text(
        self,
        to_email: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> PorkbunSendResult:
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = subject
        message["Date"] = formatdate(localtime=True)
        message_id = make_msgid(domain=self.from_email.split("@", 1)[-1])
        message["Message-ID"] = message_id
        if reply_to:
            message["Reply-To"] = reply_to
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if references:
            message["References"] = references
        message.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=30) as server:
            server.starttls()
            server.login(self.username, self.password)
            send_result = server.send_message(message)

        rejected = list(send_result.keys()) if isinstance(send_result, dict) else []
        accepted = [] if rejected else [to_email]
        provider = "smtp"
        return PorkbunSendResult(message_id=message_id, accepted_recipients=accepted, raw_provider=provider)
