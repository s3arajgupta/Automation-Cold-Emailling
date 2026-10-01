"""Data models for ColdMail outreach campaigns."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SendStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    DRY_RUN = "DRY_RUN"


@dataclass
class Recipient:
    """Represents a prospective contact to email."""

    email: str
    name: str
    company: str = "your team"
    title: Optional[str] = None
    custom_note: Optional[str] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @property
    def domain(self) -> str:
        """Extract the domain from the email address."""
        if "@" in self.email:
            return self.email.split("@", 1)[1].lower().strip()
        return ""


@dataclass
class EmailDraft:
    """A prepared email message ready for dispatch or preview."""

    recipient: Recipient
    subject: str
    body_html: str
    body_text: str
    attachments: List[Path] = field(default_factory=list)


@dataclass
class SendResult:
    """The result of an attempted email dispatch."""

    recipient_email: str
    recipient_name: str
    status: SendStatus
    timestamp: str
    error_message: Optional[str] = None
    delay_taken_seconds: float = 0.0
