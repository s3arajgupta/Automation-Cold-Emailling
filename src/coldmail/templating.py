"""Jinja2 template rendering engine with dual HTML and plaintext generation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    HAS_JINJA = True
except ImportError:
    HAS_JINJA = False

from coldmail.config import Settings
from coldmail.models import EmailDraft, Recipient

HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html_tags(html_content: str) -> str:
    """Fallback plain-text converter by stripping HTML tags and collapsing whitespace."""
    text = HTML_TAG_RE.sub(" ", html_content)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(chunk for chunk in lines if chunk)


class TemplateRenderer:
    """Manages email template loading, variable injection, and compilation."""

    def __init__(self, template_dir: Path, settings: Settings) -> None:
        self.template_dir = template_dir
        self.settings = settings
        if HAS_JINJA:
            self.env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.env = None

    def _render_string_fallback(self, template_str: str, context: dict) -> str:
        """Simple regex template replacer for {{ key }} when Jinja2 is unavailable."""
        result = template_str
        # Replace basic {{ variable }} tokens
        for key, val in context.items():
            pattern = re.compile(r"\{\{\s*" + re.escape(str(key)) + r"\s*\}\}")
            result = pattern.sub(str(val or ""), result)
        # Strip remaining unresolved tokens or unclosed simple jinja tags
        result = re.sub(r"\{%\s*if[^\}]*%\}.*?\{%\s*endif\s*%\}", "", result, flags=re.DOTALL)
        result = re.sub(r"\{\{[^\}]*\}\}", "", result)
        return result

    def render_draft(
        self,
        template_name: str,
        subject_template: str,
        recipient: Recipient,
        attachment_paths: list[Path] | None = None,
    ) -> EmailDraft:
        """Render an email draft for a specific recipient."""
        context = {
            # Recipient specific
            "name": recipient.name,
            "email": recipient.email,
            "company": recipient.company,
            "title": recipient.title or "",
            "custom_note": recipient.custom_note or "",
            **recipient.extra_fields,
            # Sender settings
            "sender_name": self.settings.sender_name,
            "sender_title": self.settings.sender_title,
            "linkedin_url": self.settings.linkedin_url,
            "github_url": self.settings.github_url,
            "portfolio_highlight": self.settings.portfolio_highlight,
        }

        template_file = self.template_dir / template_name
        template_raw = template_file.read_text(encoding="utf-8") if template_file.exists() else ""

        if HAS_JINJA and self.env is not None:
            template = self.env.get_template(template_name)
            rendered_html = template.render(**context)
        else:
            rendered_html = self._render_string_fallback(template_raw, context)

        # Check if corresponding .txt template exists
        txt_template_name = Path(template_name).with_suffix(".txt").name
        txt_path = self.template_dir / txt_template_name
        if txt_path.exists():
            if HAS_JINJA and self.env is not None:
                txt_template = self.env.get_template(txt_template_name)
                rendered_text = txt_template.render(**context)
            else:
                rendered_text = self._render_string_fallback(
                    txt_path.read_text(encoding="utf-8"), context
                )
        else:
            rendered_text = strip_html_tags(rendered_html)

        # Render dynamic subject
        if HAS_JINJA and self.env is not None:
            subject_jinja = self.env.from_string(subject_template)
            rendered_subject = subject_jinja.render(**context)
        else:
            rendered_subject = self._render_string_fallback(subject_template, context)

        return EmailDraft(
            recipient=recipient,
            subject=rendered_subject,
            body_html=rendered_html,
            body_text=rendered_text,
            attachments=attachment_paths or [],
        )
