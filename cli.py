#!/usr/bin/env python3

import typer
import sys

from pathlib import Path
from loguru import logger
from typing_extensions import Annotated

from main import get_playlist_info, get_song_urls, download_from_urls

def setup_logger():
    logger.remove()
    logger.add(sys.stderr, level="INFO")

def setup_debug_logger():
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

def main(playlist_url: str,
    output: Path = typer.Option(default=Path.cwd() / "downloads", help="Output directory for downloaded files."),
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    if verbose:
        setup_debug_logger()
    else:
        setup_logger()
    playlist_info = get_playlist_info(playlist_url)
    download_urls = get_song_urls(playlist_info)
    download_from_urls(download_urls, output)


if __name__ == "__main__":
    typer.run(main)