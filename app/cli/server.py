import typer

from app.settings import settings

app = typer.Typer(no_args_is_help=True, epilog=__doc__)


@app.command()
def serve():
    """Start the FastAPI server."""
    from app.main import app as fastapi_app

    import uvicorn

    uvicorn.run(fastapi_app)
