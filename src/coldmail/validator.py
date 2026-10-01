"""CSV ingestion and email validation engine."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List, Tuple

from coldmail.models import Recipient

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_syntax(email: str, check_mx: bool = False) -> Tuple[bool, str]:
    """Validate email address format and optionally check domain MX records."""
    email = email.strip()
    if not email:
        return False, "Email address is empty"

    try:
        from email_validator import validate_email, EmailNotValidError
        validated = validate_email(email, check_deliverability=check_mx)
        return True, validated.normalized
    except ImportError:
        # Fallback to standard RFC regex
        if EMAIL_REGEX.match(email):
            return True, email.lower()
        return False, f"Invalid email format: {email}"
    except Exception as e:
        return False, str(e)


def load_and_validate_recipients(
    csv_path: Path,
    check_mx: bool = False,
) -> Tuple[List[Recipient], List[Tuple[int, dict, str]]]:
    """
    Load recipients from a CSV file.
    
    Returns:
        (valid_recipients, invalid_entries)
        where invalid_entries is a list of (row_number, raw_dict, reason)
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Recipients file not found at: {csv_path}")

    valid_recipients: List[Recipient] = []
    invalid_entries: List[Tuple[int, dict, str]] = []
    seen_emails: set[str] = set()

    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV file is empty or has no header: {csv_path}")

        # Normalize header keys to lowercase
        for row_idx, raw_row in enumerate(reader, start=2):
            normalized = {
                k.strip().lower().replace(" ", "_"): (v.strip() if v else "")
                for k, v in raw_row.items()
                if k
            }

            raw_email = (
                normalized.get("email")
                or normalized.get("e-mail")
                or normalized.get("mail")
                or ""
            )
            raw_name = (
                normalized.get("name")
                or normalized.get("full_name")
                or normalized.get("first_name")
                or ""
            )
            company = (
                normalized.get("company")
                or normalized.get("company_name")
                or normalized.get("organization")
                or "your team"
            )
            title = normalized.get("title") or normalized.get("position") or None
            custom_note = normalized.get("custom_note") or normalized.get("note") or None

            if not raw_email:
                invalid_entries.append((row_idx, raw_row, "Missing 'email' column or empty value"))
                continue

            is_valid, email_or_error = validate_email_syntax(raw_email, check_mx=check_mx)
            if not is_valid:
                invalid_entries.append((row_idx, raw_row, email_or_error))
                continue

            clean_email = email_or_error.lower()
            if clean_email in seen_emails:
                invalid_entries.append((row_idx, raw_row, f"Duplicate email address: {clean_email}"))
                continue

            seen_emails.add(clean_email)
            valid_recipients.append(
                Recipient(
                    email=clean_email,
                    name=raw_name if raw_name else clean_email.split("@")[0].capitalize(),
                    company=company,
                    title=title,
                    custom_note=custom_note,
                    extra_fields=normalized,
                )
            )

    return valid_recipients, invalid_entries
