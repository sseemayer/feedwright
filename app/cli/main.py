"""This is the command-line interface for the feedwright RSS feed generator.

For debugging and development purposes, the `list` and `get` commands will be worth looking into.
"""

import typer

from app.cli.config import app as config_app
from app.cli.dev import app as dev_app
from app.cli.feed import app as feed_app
from app.cli.server import app as server_app

app = typer.Typer(no_args_is_help=True, epilog=__doc__)

app.add_typer(config_app, name="config", help="Commands for working with configuration")
app.add_typer(dev_app, name="dev", help="Commands for development and debugging")
app.add_typer(feed_app, name="feed", help="Commands for working with RSS feeds")
app.add_typer(server_app, name="server", help="Commands for running the server")


if __name__ == "__main__":
    app()
