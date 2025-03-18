"""CLI Module for Spotify Playlist Downloader"""

from __future__ import annotations

import typer
from loguru import logger
from typing_extensions import Annotated
from typing import Optional
from importlib.metadata import version
from pathlib import Path

from main import main as spotify_dl_main

app = typer.Typer()

def version_callback(value: bool):
    if value:
        typer.echo(f"{version('spotify-dl')}")
        raise typer.Exit()


@app.command()
def main(
    playlist_url: str = typer.Argument(..., help="Spotify playlist URL or ID"),
    output_dir: Path = typer.Option(
        "--output-dir",
        "-o",
        help="Output directory for downloading songs (default: ./downloads)",
        default=Path.cwd() / "downloads",
    ),
    version: Annotated[
        Optional[bool], typer.Option("--version", callback=version_callback)
    ] = None,
):
    """Spotify Playlist Downloader"""
    logger.info(f"Starting download from {playlist_url} to {output_dir}")
    try:
        spotify_dl_main(playlist_url, output_dir)
        logger.info("Download completed.")
        typer.Exit(0)
    except Exception as e:
        logger.error(e)
        logger.error(
            "If you'd like to report this issue, "
            "please include the message above when opening issues on GitHub. "
            "For detailed instructions, see CONTRIBUTING.md"
        )
        typer.Exit(1)


if __name__ == "__main__":
    app()
