from coldmail.config import Settings
from coldmail.models import EmailDraft, Recipient, SendStatus
from coldmail.sender import SMTPSender


def test_dry_run_dispatch():
    settings = Settings(
        smtp_email="test@example.com",
        smtp_password="dummy",
        dry_run=True,
    )
    sender = SMTPSender(settings=settings, dry_run=True)

    recipient = Recipient(name="Tester", email="tester@example.com", company="Acme")
    draft = EmailDraft(
        recipient=recipient,
        subject="Test Subject",
        body_html="<p>Test</p>",
        body_text="Test",
    )

    result = sender.dispatch(draft)
    assert result.status == SendStatus.DRY_RUN
    assert result.recipient_email == "tester@example.com"
    assert result.recipient_name == "Tester"


def test_build_message():
    settings = Settings(
        smtp_email="sender@example.com",
        sender_name="Swaraj",
    )
    sender = SMTPSender(settings=settings, dry_run=True)
    recipient = Recipient(name="Bob", email="bob@test.com")
    draft = EmailDraft(
        recipient=recipient,
        subject="Hello Bob",
        body_html="<h1>Hi</h1>",
        body_text="Hi",
    )

    msg = sender.build_message(draft)
    assert msg["Subject"] == "Hello Bob"
    assert "sender@example.com" in msg["From"]
    assert "bob@test.com" in msg["To"]
