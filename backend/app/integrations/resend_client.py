import resend

from app.core.config import settings


class ResendClient:
    def __init__(self) -> None:
        resend.api_key = settings.resend_api_key

    def send_email(
        self,
        to_email: str,
        subject: str,
        html: str,
        from_email: str | None = None,
        reply_to: str | None = None,
    ) -> dict:
        sender = from_email or settings.from_email_outbound or settings.from_email_fulfillment
        payload = {
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
        reply_target = reply_to or settings.reply_to_email
        if reply_target:
            payload["replyTo"] = reply_target
        return resend.Emails.send(payload)

    def send_packet_email(self, to_email: str, subject: str, html: str) -> dict:
        return self.send_email(
            to_email=to_email,
            subject=subject,
            html=html,
            from_email=settings.from_email_fulfillment,
        )

    def send_outbound_email(self, to_email: str, subject: str, html: str) -> dict:
        return self.send_email(
            to_email=to_email,
            subject=subject,
            html=html,
            from_email=settings.from_email_outbound or settings.from_email_fulfillment,
        )
