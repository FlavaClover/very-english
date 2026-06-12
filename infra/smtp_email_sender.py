import ssl
from email.message import EmailMessage as SmtpEmailMessage

import aiosmtplib

from auth.email_verification import EmailMessage, EmailSender


class SmtpEmailSender(EmailSender):
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_address = from_address

    def _smtp_tls_kwargs(self) -> dict[str, bool]:
        if self._port == 465:
            return {"use_tls": True, "start_tls": False}
        if self._port == 587:
            return {"use_tls": False, "start_tls": True}
        return {"use_tls": False, "start_tls": False}

    def _smtp_tls_context(self) -> ssl.SSLContext | None:
        tls_kwargs = self._smtp_tls_kwargs()
        if not tls_kwargs["use_tls"] and not tls_kwargs["start_tls"]:
            return None
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    async def send(self, message: EmailMessage) -> None:
        smtp_message = SmtpEmailMessage()
        smtp_message["From"] = self._from_address
        smtp_message["To"] = message.to
        smtp_message["Subject"] = message.subject
        smtp_message.set_content(message.body_text)

        await aiosmtplib.send(
            smtp_message,
            hostname=self._host,
            port=self._port,
            username=self._username or None,
            password=self._password or None,
            tls_context=self._smtp_tls_context(),
            use_tls=False,
            start_tls=True,
        )
