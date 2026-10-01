import csv
import sys
from pathlib import Path
from typing import List, Optional

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.syntax import Syntax
from rich.table import Table

from coldmail.config import get_settings
from coldmail.limiter import RateLimiter
from coldmail.models import Recipient, SendResult, SendStatus
from coldmail.sender import SMTPSender
from coldmail.templating import TemplateRenderer
from coldmail.validator import load_and_validate_recipients

app = typer.Typer(
    name="coldmail",
    help="Privacy-first, modular CLI cold email automation engine.",
    add_completion=False,
)
console = Console()


@app.command()
def init() -> None:
    """Initialize environment config (.env) and project directories."""
    cwd = Path.cwd()
    env_example = cwd / ".env.example"
    env_target = cwd / ".env"

    if env_target.exists():
        console.print("[yellow][INFO] '.env' file already exists.[/yellow]")
    elif env_example.exists():
        env_target.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
        console.print("[green][OK] Created '.env' from '.env.example'.[/green]")
        console.print("[bold cyan][->] Please update '.env' with your SMTP credentials.[/bold cyan]")
    else:
        console.print("[red][ERROR] '.env.example' not found in current directory.[/red]")

    # Ensure data, attachments, and templates exist
    (cwd / "data").mkdir(exist_ok=True)
    (cwd / "templates").mkdir(exist_ok=True)
    (cwd / "attachments").mkdir(exist_ok=True)
    console.print("[green][OK] Verified directories: data/, templates/, attachments/[/green]")


@app.command()
def validate(
    csv_path: Path = typer.Argument(
        Path("data/recipients.sample.csv"),
        help="Path to CSV recipient file.",
    ),
    check_mx: bool = typer.Option(
        False,
        "--check-mx",
        help="Perform live DNS MX record checks for domain verification.",
    ),
) -> None:
    """Validate recipient CSV formatting, syntax, and duplicates."""
    console.print(f"[bold blue]Validating recipient list:[/bold blue] {csv_path}")

    try:
        valid_recipients, invalid_entries = load_and_validate_recipients(csv_path, check_mx=check_mx)
    except Exception as e:
        console.print(f"[bold red]Error reading CSV:[/bold red] {e}")
        raise typer.Exit(code=1)

    table = Table(title="Validation Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Count", justify="right")

    table.add_row("Valid Unique Contacts", f"[green]{len(valid_recipients)}[/green]")
    table.add_row("Invalid or Duplicate Rows", f"[red]{len(invalid_entries)}[/red]")
    console.print(table)

    if invalid_entries:
        console.print("\n[bold yellow]Invalid / Duplicate Entries:[/bold yellow]")
        for row_idx, row_dict, reason in invalid_entries[:10]:
            email_val = row_dict.get("email", "N/A")
            console.print(f"  • Row {row_idx}: [cyan]{email_val}[/cyan] -> [red]{reason}[/red]")
        if len(invalid_entries) > 10:
            console.print(f"  ... and {len(invalid_entries) - 10} more.")


@app.command()
def preview(
    template: str = typer.Option(
        "job_outreach.html",
        "--template",
        "-t",
        help="Template filename inside templates/ directory.",
    ),
    csv_path: Path = typer.Option(
        Path("data/recipients.sample.csv"),
        "--csv",
        help="Path to recipient CSV to extract preview contact.",
    ),
    subject: str = typer.Option(
        "Software Engineer Opportunities | {{ company }} | {{ sender_name }}",
        "--subject",
        "-s",
        help="Subject line template.",
    ),
    template_dir: Path = typer.Option(
        Path("templates"),
        "--template-dir",
        help="Directory containing email templates.",
    ),
) -> None:
    """Preview rendered subject, plaintext, and HTML body for a recipient."""
    settings = get_settings()
    valid_recipients, _ = load_and_validate_recipients(csv_path)

    if not valid_recipients:
        console.print("[red]No valid recipients found to generate preview.[/red]")
        raise typer.Exit(code=1)

    sample = valid_recipients[0]
    renderer = TemplateRenderer(template_dir=template_dir, settings=settings)
    draft = renderer.render_draft(
        template_name=template,
        subject_template=subject,
        recipient=sample,
    )

    console.print(Panel(
        f"[bold]To:[/bold] {draft.recipient.name} <{draft.recipient.email}>\n"
        f"[bold]Company:[/bold] {draft.recipient.company}\n"
        f"[bold]Subject:[/bold] {draft.subject}",
        title="[bold green]Rendered Metadata Preview[/bold green]",
        border_style="green",
    ))

    console.print(Panel(
        draft.body_text,
        title="[bold cyan]Rendered Plaintext Body (Spam Fallback)[/bold cyan]",
        border_style="cyan",
    ))

    console.print("[bold yellow]HTML Preview Code (Snippet):[/bold yellow]")
    snippet = draft.body_html[:500] + ("\n..." if len(draft.body_html) > 500 else "")
    console.print(Syntax(snippet, "html", theme="monokai", line_numbers=True))


@app.command()
def run(
    csv_path: Path = typer.Option(
        Path("data/recipients.sample.csv"),
        "--csv",
        help="Path to recipient CSV file.",
    ),
    template: str = typer.Option(
        "job_outreach.html",
        "--template",
        "-t",
        help="Jinja2 template filename.",
    ),
    subject: str = typer.Option(
        "Opportunities at {{ company }} | {{ sender_name }}",
        "--subject",
        "-s",
        help="Subject template.",
    ),
    attachments: Optional[List[Path]] = typer.Option(
        None,
        "--attach",
        "-a",
        help="File path(s) to attach to outgoing emails.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate run without connecting to SMTP or sending emails.",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-n",
        help="Limit number of emails to dispatch in this session.",
    ),
    delay_min: float = typer.Option(
        8.0,
        "--delay-min",
        help="Minimum randomized jitter delay in seconds.",
    ),
    delay_max: float = typer.Option(
        18.0,
        "--delay-max",
        help="Maximum randomized jitter delay in seconds.",
    ),
    log_output: Path = typer.Option(
        Path("dispatch_report.csv"),
        "--log",
        help="Output CSV audit log path.",
    ),
) -> None:
    """Execute automated outreach campaign with deliverability guardrails."""
    settings = get_settings()
    is_dry = dry_run or settings.dry_run

    mode_label = "[bold yellow]DRY-RUN SIMULATION[/bold yellow]" if is_dry else "[bold red]LIVE DISPATCH[/bold red]"
    console.print(f"\n[*] Initializing ColdMail Campaign ({mode_label})\n")

    # Ingest and validate contacts
    valid_recipients, _ = load_and_validate_recipients(csv_path)
    if limit and limit > 0:
        valid_recipients = valid_recipients[:limit]

    total = len(valid_recipients)
    if total == 0:
        console.print("[red]No valid recipients found. Exiting.[/red]")
        raise typer.Exit(code=1)

    console.print(f"Loaded [bold green]{total}[/bold green] recipients.")

    # Setup attachments
    verified_attachments: List[Path] = []
    if attachments:
        for att in attachments:
            if att.exists():
                verified_attachments.append(att)
            else:
                console.print(f"[yellow]Warning: Attachment not found:[/yellow] {att}")

    renderer = TemplateRenderer(Path("templates"), settings=settings)
    limiter = RateLimiter(
        min_delay=delay_min,
        max_delay=delay_max,
        max_per_domain=settings.max_emails_per_domain,
    )

    results: List[SendResult] = []

    try:
        with SMTPSender(settings=settings, dry_run=is_dry) as sender:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Dispatching emails...", total=total)

                for idx, recipient in enumerate(valid_recipients, start=1):
                    # Check domain velocity throttle
                    allowed, reason = limiter.can_send_to_domain(recipient.domain)
                    if not allowed:
                        res = SendResult(
                            recipient_email=recipient.email,
                            recipient_name=recipient.name,
                            status=SendStatus.SKIPPED,
                            timestamp="",
                            error_message=reason,
                        )
                        results.append(res)
                        progress.advance(task)
                        continue

                    # Render dynamic draft
                    draft = renderer.render_draft(
                        template_name=template,
                        subject_template=subject,
                        recipient=recipient,
                        attachment_paths=verified_attachments,
                    )

                    # Dispatch
                    result = sender.dispatch(draft)
                    limiter.record_sent(recipient.domain)

                    # Apply jitter if not the last item
                    if idx < total:
                        delay_waited = limiter.wait_jitter(dry_run=is_dry)
                        result.delay_taken_seconds = delay_waited

                    results.append(result)
                    progress.advance(task)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Campaign interrupted by user. Generating partial report...[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Fatal Error during dispatch:[/red] {e}")

    # Generate summary report table
    success_count = sum(1 for r in results if r.status in (SendStatus.SUCCESS, SendStatus.DRY_RUN))
    failed_count = sum(1 for r in results if r.status == SendStatus.FAILED)
    skipped_count = sum(1 for r in results if r.status == SendStatus.SKIPPED)

    summary_table = Table(title="Campaign Results", show_header=True)
    summary_table.add_column("Status", style="bold")
    summary_table.add_column("Count", justify="right")
    summary_table.add_row("Delivered / Simulated", f"[green]{success_count}[/green]")
    summary_table.add_row("Failed", f"[red]{failed_count}[/red]")
    summary_table.add_row("Throttled / Skipped", f"[yellow]{skipped_count}[/yellow]")
    console.print("\n", summary_table)

    # Write audit log CSV
    with open(log_output, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Name", "Email", "Status", "DelaySec", "Error"])
        for r in results:
            writer.writerow([
                r.timestamp,
                r.recipient_name,
                r.recipient_email,
                r.status.value,
                r.delay_taken_seconds,
                r.error_message or "",
            ])
    console.print(f"[dim]Audit log saved to: [cyan]{log_output}[/cyan][/dim]\n")


if __name__ == "__main__":
    app()
