"""This is the command-line interface for the feedwright RSS feed generator.

For debugging and development purposes, the `list` and `get` commands will be worth looking into.
"""

import typer

from app.settings import settings
from app.extract import extractors

app = typer.Typer(no_args_is_help=True, epilog=__doc__)


@app.command("config")
def show_config():
    """Show the current configuration."""
    # Placeholder for actual implementation
    typer.echo(settings.model_dump_json(indent=2))


@app.command("list")
def list_extractors():
    """List all configured extractors."""
    for extractor in sorted(extractors.extractors):
        typer.echo(extractor)


@app.command("get")
def get_extractor(name: str):
    """Get the RSS feed for a specific extractor name."""

    feed = extractors.get(name)

    typer.echo(feed.model_dump_json(indent=2, exclude_none=True))


@app.command()
def serve():
    """Start the FastAPI server."""
    from app.main import app as fastapi_app

    import uvicorn

    uvicorn.run(fastapi_app)


if __name__ == "__main__":
    app()
