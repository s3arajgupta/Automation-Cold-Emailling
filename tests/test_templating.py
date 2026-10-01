from pathlib import Path
import tempfile
import pytest

from coldmail.config import Settings
from coldmail.models import Recipient
from coldmail.templating import TemplateRenderer, strip_html_tags


def test_strip_html_tags():
    html = "<p>Hello <b>World</b></p><br><span>Test</span>"
    clean = strip_html_tags(html)
    assert "Hello" in clean
    assert "World" in clean
    assert "<p>" not in clean


def test_template_renderer():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        html_tpl = tmp_path / "test_email.html"
        html_tpl.write_text(
            "<p>Dear {{ name }}, welcome to {{ company }} from {{ sender_name }}.</p>",
            encoding="utf-8",
        )

        settings = Settings(sender_name="Swaraj Test")
        renderer = TemplateRenderer(tmp_path, settings=settings)

        recipient = Recipient(
            name="Charlie",
            email="charlie@sample.com",
            company="Globex",
        )

        draft = renderer.render_draft(
            template_name="test_email.html",
            subject_template="Hello {{ company }}!",
            recipient=recipient,
        )

        assert draft.subject == "Hello Globex!"
        assert "Dear Charlie" in draft.body_html
        assert "Globex" in draft.body_html
        assert "Swaraj Test" in draft.body_html
        assert "Dear Charlie" in draft.body_text
