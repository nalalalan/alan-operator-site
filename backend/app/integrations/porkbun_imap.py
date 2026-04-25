from __future__ import annotations

from dataclasses import dataclass
from email import message_from_bytes
from email.message import Message
from email.utils import parseaddr
import html
import imaplib
import re
from typing import Iterable

from app.core.config import settings


@dataclass
class ParsedMailboxMessage:
    uid: str
    message_id: str
    subject: str
    from_email: str
    to_email: str
    body_text: str
    raw_date: str


class PorkbunIMAPClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        mailbox: str = "INBOX",
    ) -> None:
        self.host = host or settings.buyer_acq_imap_host
        self.port = int(port or settings.buyer_acq_imap_port)
        self.username = username or settings.buyer_acq_mailbox_address
        self.password = password or settings.buyer_acq_mailbox_password
        self.mailbox = mailbox
        if not self.username or not self.password:
            raise ValueError("buyer acquisition IMAP username/password are required")

    def _connect(self) -> imaplib.IMAP4_SSL:
        client = imaplib.IMAP4_SSL(self.host, self.port)
        client.login(self.username, self.password)
        client.select(self.mailbox)
        return client

    def fetch_unseen(self, limit: int = 20) -> list[ParsedMailboxMessage]:
        client = self._connect()
        try:
            status, data = client.uid("search", None, "UNSEEN")
            if status != "OK":
                return []
            raw_uids = data[0].decode("utf-8").strip().split()
            selected_uids = raw_uids[-limit:]
            messages: list[ParsedMailboxMessage] = []
            for uid in selected_uids:
                fetch_status, fetch_data = client.uid("fetch", uid, "(BODY.PEEK[])")
                if fetch_status != "OK" or not fetch_data:
                    continue
                raw_bytes = b""
                for item in fetch_data:
                    if isinstance(item, tuple):
                        raw_bytes += item[1]
                if not raw_bytes:
                    continue
                email_message = message_from_bytes(raw_bytes)
                messages.append(
                    ParsedMailboxMessage(
                        uid=uid,
                        message_id=str(email_message.get("Message-ID", "")).strip(),
                        subject=_decode_header_value(email_message.get("Subject", "")),
                        from_email=parseaddr(email_message.get("From", ""))[1].lower().strip(),
                        to_email=parseaddr(email_message.get("To", ""))[1].lower().strip(),
                        body_text=_extract_body_text(email_message),
                        raw_date=str(email_message.get("Date", "")).strip(),
                    )
                )
            return messages
        finally:
            try:
                client.close()
            except Exception:
                pass
            client.logout()

    def mark_seen(self, uids: Iterable[str]) -> None:
        cleaned = [uid for uid in uids if str(uid).strip()]
        if not cleaned:
            return
        client = self._connect()
        try:
            for uid in cleaned:
                client.uid("store", uid, "+FLAGS", "(\\Seen)")
        finally:
            try:
                client.close()
            except Exception:
                pass
            client.logout()


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    try:
        from email.header import decode_header

        parts = []
        for chunk, encoding in decode_header(value):
            if isinstance(chunk, bytes):
                parts.append(chunk.decode(encoding or "utf-8", errors="replace"))
            else:
                parts.append(str(chunk))
        return " ".join(x for x in parts if x).strip()
    except Exception:
        return str(value).strip()


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _html_to_text(value: str) -> str:
    text = _TAG_RE.sub(" ", value)
    return _WS_RE.sub(" ", html.unescape(text)).strip()


def _extract_body_text(message: Message) -> str:
    if message.is_multipart():
        plain_parts: list[str] = []
        html_parts: list[str] = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if str(part.get("Content-Disposition", "")).lower().startswith("attachment"):
                continue
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            content_type = part.get_content_type().lower()
            if content_type == "text/plain":
                plain_parts.append(decoded)
            elif content_type == "text/html":
                html_parts.append(decoded)
        combined_plain = "\n".join(x.strip() for x in plain_parts if x.strip()).strip()
        if combined_plain:
            return combined_plain
        combined_html = "\n".join(_html_to_text(x) for x in html_parts if x.strip()).strip()
        return combined_html

    payload = message.get_payload(decode=True) or b""
    charset = message.get_content_charset() or "utf-8"
    decoded = payload.decode(charset, errors="replace")
    if message.get_content_type().lower() == "text/html":
        return _html_to_text(decoded)
    return decoded.strip()
