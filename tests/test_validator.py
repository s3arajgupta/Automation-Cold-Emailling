from pathlib import Path
import tempfile
import pytest

from coldmail.validator import validate_email_syntax, load_and_validate_recipients


def test_validate_email_syntax():
    valid, _ = validate_email_syntax("user@example.com")
    assert valid is True

    valid, _ = validate_email_syntax("invalid-email-string")
    assert valid is False

    valid, _ = validate_email_syntax("")
    assert valid is False


def test_load_and_validate_recipients():
    sample_csv_content = """Name,Email,Company,Title
Alice Smith,alice@example.com,Acme Corp,CTO
Bob Jones,bob@tech.org,Tech Co,Director
Bad Entry,not-an-email,Test Co,Engineer
Alice Duplicate,alice@example.com,Duplicate Inc,VP
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8") as f:
        f.write(sample_csv_content)
        temp_path = Path(f.name)

    try:
        valid_recipients, invalid_entries = load_and_validate_recipients(temp_path)
        assert len(valid_recipients) == 2
        assert valid_recipients[0].email == "alice@example.com"
        assert valid_recipients[0].name == "Alice Smith"
        assert valid_recipients[0].company == "Acme Corp"
        assert valid_recipients[1].email == "bob@tech.org"

        assert len(invalid_entries) == 2
        # One invalid format, one duplicate
        reasons = [item[2] for item in invalid_entries]
        assert any("Duplicate" in r for r in reasons)
    finally:
        if temp_path.exists():
            temp_path.unlink()
