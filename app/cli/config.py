import typer

from app.settings import settings

app = typer.Typer(no_args_is_help=True, epilog=__doc__)


@app.command("show")
def show_config():
    """Show the current configuration."""
    # Placeholder for actual implementation
    typer.echo(settings.model_dump_json(indent=2))
