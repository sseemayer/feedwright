import typer

from asyncer import syncify
from functools import partial

from app.extract import extractors
from app.render import OutputFormat

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
