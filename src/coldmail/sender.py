"""SMTP connection management and email transmission engine."""

from __future__ import annotations

import datetime
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from coldmail.config import Settings
from coldmail.models import EmailDraft, SendResult, SendStatus


class SMTPSender:
    """Manages SMTP lifecycle, MIME composition, and secure dispatch."""

    def __init__(self, settings: Settings, dry_run: bool = False) -> None:
        self.settings = settings
        self.dry_run = dry_run
        self._server: Optional[smtplib.SMTP] = None

    def __enter__(self) -> "SMTPSender":
        if not self.dry_run:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def connect(self) -> None:
        """Establish TLS connection to the SMTP server."""
        errors = self.settings.validate_for_send()
        if errors:
            raise ValueError(f"SMTP Configuration Error: {'; '.join(errors)}")

        server = smtplib.SMTP(self.settings.smtp_server, self.settings.smtp_port, timeout=30)
        server.ehlo()
        if self.settings.smtp_use_tls:
            server.starttls()
            server.ehlo()
        server.login(self.settings.smtp_email, self.settings.smtp_password)
        self._server = server

    def disconnect(self) -> None:
        """Gracefully close SMTP session."""
        if self._server:
            try:
                self._server.quit()
            except Exception:
                pass
            finally:
                self._server = None

    def build_message(self, draft: EmailDraft) -> EmailMessage:
        """Construct a modern dual-MIME multipart message with attachments."""
        msg = EmailMessage()
        msg["Subject"] = draft.subject
        msg["From"] = f"{self.settings.sender_name} <{self.settings.smtp_email}>"
        msg["To"] = f"{draft.recipient.name} <{draft.recipient.email}>"

        if self.settings.sender_reply_to:
            msg["Reply-To"] = self.settings.sender_reply_to

        # Set plain-text as base content, then add HTML as alternative
        msg.set_content(draft.body_text)
        msg.add_alternative(draft.body_html, subtype="html")

        # Process attachments
        for attachment_path in draft.attachments:
            if not attachment_path.exists():
                continue

            ctype, encoding = mimetypes.guess_type(str(attachment_path))
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)

            with open(attachment_path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=attachment_path.name,
                )

        return msg

    def dispatch(self, draft: EmailDraft) -> SendResult:
        """Dispatch a single email draft or record dry-run."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.dry_run:
            return SendResult(
                recipient_email=draft.recipient.email,
                recipient_name=draft.recipient.name,
                status=SendStatus.DRY_RUN,
                timestamp=timestamp,
            )

        if not self._server:
            raise RuntimeError("SMTP connection is not active.")

        try:
            msg = self.build_message(draft)
            self._server.send_message(msg)
            return SendResult(
                recipient_email=draft.recipient.email,
                recipient_name=draft.recipient.name,
                status=SendStatus.SUCCESS,
                timestamp=timestamp,
            )
        except Exception as e:
            return SendResult(
                recipient_email=draft.recipient.email,
                recipient_name=draft.recipient.name,
                status=SendStatus.FAILED,
                timestamp=timestamp,
                error_message=str(e),
            )
