"""Configuration management for ColdMail with environment variables and .env support."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    # Load from .env if present in current or parent directory
    load_dotenv(override=False)
except ImportError:
    pass


@dataclass
class Settings:
    """Application and SMTP settings loaded from environment."""

    smtp_email: str = os.getenv("SMTP_EMAIL", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    sender_name: str = os.getenv("SMTP_NAME", "Swaraj Gupta")
    sender_title: str = os.getenv("SMTP_TITLE", "Full-Stack Data Engineer")
    sender_reply_to: str = os.getenv("SMTP_REPLY_TO", "")

    linkedin_url: str = os.getenv("LINKEDIN_URL", "https://linkedin.com/in/s3arajgupta")
    github_url: str = os.getenv("GITHUB_URL", "https://github.com/s3arajgupta")
    portfolio_highlight: str = os.getenv(
        "PORTFOLIO_HIGHLIGHT",
        "CKAD Certified | Open source contributor | Big Data & MLOps Engineer"
    )

    min_delay_seconds: float = float(os.getenv("MIN_DELAY_SECONDS", "8.0"))
    max_delay_seconds: float = float(os.getenv("MAX_DELAY_SECONDS", "18.0"))
    max_emails_per_domain: int = int(os.getenv("MAX_EMAILS_PER_DOMAIN", "5"))
    dry_run: bool = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")

    def validate_for_send(self) -> list[str]:
        """Verify that credentials needed for actual live dispatch are present."""
        errors: list[str] = []
        if not self.smtp_email:
            errors.append("SMTP_EMAIL is not configured in .env or environment.")
        if not self.smtp_password:
            errors.append("SMTP_PASSWORD is not configured in .env or environment.")
        if not self.smtp_server:
            errors.append("SMTP_SERVER is not configured.")
        return errors


def get_settings() -> Settings:
    """Retrieve active settings singleton."""
    return Settings()
