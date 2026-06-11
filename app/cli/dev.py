import typer

from app.settings import settings

app = typer.Typer(no_args_is_help=True, epilog=__doc__)


@app.command("debug-parsel")
def parsel(
    url: str,
):
    """Parse a URL and get the RSS feed."""

    from parsel import Selector

    client = settings.http.get_sync_client()
    res = client.get(url)
    res.raise_for_status()

    selector = Selector(res.text)

    print("Use 'selector' to interact with the parsed document.")

    breakpoint()
