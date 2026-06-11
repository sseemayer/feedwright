import typer
import json

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


@app.command("extractor-schema")
def extractor_schema(plugin: str):
    """Print the schema for the extractor configuration."""

    model = extractors.get_extractor_class(plugin)

    print(json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False))


try:
    import litellm
    import instructor
    import yaml

    @app.command("generate-config")
    @partial(syncify, raise_sync_error=False)
    async def generate_config(url: str, plugin: str):
        """Generate a configuration file for the extractors."""

        litellm.suppress_debug_info = True
        result = await extractors.generate_config(url, plugin)

        output = {
            "plugin": plugin,
            "config": result.model_dump(mode="json", exclude_none=True),
        }

        print(
            yaml.safe_dump(
                output,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        )

except ImportError:
    pass
