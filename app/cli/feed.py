import typer
import json
import re

from enum import Enum
from asyncer import syncify
from functools import partial
from pathlib import Path

from app.ai import AI_AVAILABLE
from app.extract import extractors
from app.render import OutputFormat
from app.settings import settings

app = typer.Typer(no_args_is_help=True, epilog=__doc__)


@app.command("list")
def list_extractors():
    """List all configured extractors."""
    for extractor in sorted(extractors.extractors):
        typer.echo(extractor)


@app.command("get")
@partial(syncify, raise_sync_error=False)
async def get_extractor(
    name: str,
    format: OutputFormat = typer.Option(OutputFormat.json, help="Output format"),
):
    """Get the RSS feed for a specific extractor name."""

    feed = await extractors.get(name)

    rendered = format.render(feed)

    typer.echo(rendered)


@app.command("extractor-schema")
def extractor_schema(plugin: str):
    """Print the schema for the extractor configuration."""

    model = extractors.get_extractor_class(plugin)

    print(json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False))


if AI_AVAILABLE:
    import yaml
    import litellm

    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.syntax import Syntax
    from rich.table import Table

    from app.autoconfigure import (
        AutoConfigureError,
        AutoConfigureRequest,
        AutoConfigureSession,
        ValidationExhaustedError,
        autoconfigure,
    )

    class ConfigOutputFormat(str, Enum):
        yaml = "yaml"
        json = "json"

    def _configuration_output(
        plugin: str, config: dict[str, object], format: ConfigOutputFormat
    ) -> str:
        output = {"plugin": plugin, "config": config}
        if format == ConfigOutputFormat.json:
            return json.dumps(output, indent=2, ensure_ascii=False)
        return yaml.safe_dump(
            output,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def _validate_feed_name(name: str) -> str:
        name = name.strip()
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)
            or Path(name).name != name
            or name in {".", ".."}
            or "/" in name
            or "\\" in name
        ):
            raise ValueError(
                "Feed name must be a filename containing only letters, numbers, "
                "dots, underscores, and dashes"
            )
        return name

    def _configuration_path(name: str, base_path: Path) -> Path:
        return base_path / "feeds" / f"{_validate_feed_name(name)}.yaml"

    @app.command("generate-config")
    @partial(syncify, raise_sync_error=False)
    async def generate_config(
        url: str,
        plugin: str = "app.extractors.parsel:ParselExtractor",
        max_attempts: int = typer.Option(4, min=1, max=10),
        format: ConfigOutputFormat = typer.Option(ConfigOutputFormat.yaml),
    ):
        """Generate and validate an extractor configuration without prompting."""

        litellm.suppress_debug_info = True
        try:
            result = await autoconfigure(
                AutoConfigureRequest(
                    url=url, plugin=plugin, max_attempts=max_attempts
                )
            )
        except ValidationExhaustedError as exc:
            typer.echo(str(exc), err=True)
            for report in exc.reports:
                typer.echo(report.model_dump_json(), err=True)
            raise typer.Exit(1) from exc
        except AutoConfigureError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

        typer.echo(_configuration_output(result.plugin, result.config, format))

    @app.command("configure")
    @partial(syncify, raise_sync_error=False)
    async def configure(
        max_attempts: int = typer.Option(6, min=1, max=10),
    ):
        """Interactively generate, refine, and optionally save a configuration."""

        litellm.suppress_debug_info = True
        console = Console()
        console.print(
            Panel.fit(
                "Generate, validate, and refine a feed extractor with an AI agent.",
                title="Feedwright Auto-Configuration",
                border_style="cyan",
            )
        )
        url = Prompt.ask("[bold]Source URL[/bold]", console=console)
        plugin = Prompt.ask(
            "[bold]Extractor plugin[/bold]",
            default="app.extractors.parsel:ParselExtractor",
            console=console,
        )
        request = AutoConfigureRequest(
            url=url, plugin=plugin, max_attempts=max_attempts
        )
        try:
            with console.status("[cyan]Downloading and preparing the source document..."):
                session = await AutoConfigureSession.create(request)
        except AutoConfigureError as exc:
            console.print(str(exc), style="bold red", markup=False)
            raise typer.Exit(1) from exc

        feedback: str | None = None
        accepted = None
        for attempt in range(1, max_attempts + 1):
            try:
                with console.status(
                    f"[cyan]Generating candidate {attempt} of {max_attempts}..."
                ):
                    candidate = await session.generate(feedback)
            except AutoConfigureError as exc:
                console.print(str(exc), style="bold red", markup=False)
                raise typer.Exit(1) from exc

            config = candidate.extractor.model_dump(mode="json", exclude_none=True)
            rendered_config = _configuration_output(
                plugin, config, ConfigOutputFormat.yaml
            )
            console.print(
                Panel(
                    Syntax(
                        rendered_config,
                        "yaml",
                        theme="ansi_dark",
                        word_wrap=True,
                    ),
                    title=f"Candidate {attempt}",
                    border_style="blue",
                )
            )
            if candidate.valid and candidate.feed is not None:
                summary = Table(
                    title="Validation passed",
                    show_header=False,
                    border_style="green",
                )
                summary.add_column("Field", style="bold")
                summary.add_column("Value")
                summary.add_row("Feed", candidate.feed.title or candidate.feed.id)
                summary.add_row("Articles", str(len(candidate.feed.articles)))
                summary.add_row("RSS", "valid", style="green")
                summary.add_row("Atom", "valid", style="green")
                console.print(summary)
                action = Prompt.ask(
                    "[bold]Next action[/bold]",
                    choices=["accept", "retry", "cancel"],
                    default="accept",
                    console=console,
                )
                if action == "accept":
                    accepted = config
                    break
                if action == "cancel":
                    raise typer.Abort()
            else:
                errors = Table(
                    title="Validation failed",
                    border_style="red",
                    show_lines=True,
                )
                errors.add_column("Code", style="bold red", no_wrap=True)
                errors.add_column("Error")
                for issue in candidate.report.errors:
                    errors.add_row(issue.code, issue.message)
                console.print(errors)

            feedback = Prompt.ask(
                "[bold]Feedback for the next attempt[/bold]",
                default="Fix the reported validation errors",
                console=console,
            )

        if accepted is None:
            console.print(
                f"No configuration accepted after {max_attempts} attempts",
                style="bold red",
            )
            raise typer.Exit(1)

        if not Confirm.ask(
            "[bold]Save this configuration?[/bold]", default=True, console=console
        ):
            console.print("Configuration accepted without saving.", style="yellow")
            return

        while True:
            feed_name = Prompt.ask("[bold]Feed name[/bold]", console=console)
            try:
                feed_name = _validate_feed_name(feed_name)
                break
            except ValueError as exc:
                console.print(str(exc), style="bold red")

        default_base = settings.config_paths[-1]
        base_path = Path(
            Prompt.ask(
                "[bold]Configuration directory[/bold]",
                default=str(default_base),
                console=console,
            )
        ).expanduser()
        destination = _configuration_path(feed_name, base_path)
        if destination.exists() and not Confirm.ask(
            f"[bold red]Overwrite {destination}?[/bold red]",
            default=False,
            console=console,
        ):
            raise typer.Abort()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            _configuration_output(plugin, accepted, ConfigOutputFormat.yaml),
            encoding="utf-8",
        )
        console.print(
            Panel.fit(str(destination), title="Configuration saved", border_style="green")
        )
