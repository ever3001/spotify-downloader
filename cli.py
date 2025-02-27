#!/usr/bin/env python3
"""
Spotify Playlist Downloader CLI.

This module provides a command-line interface for downloading music from
Spotify playlists using YouTube Music as a source.
"""

import typer
import sys
from pathlib import Path
from loguru import logger
from typing_extensions import Annotated

from main import get_playlist_info, get_song_urls, download_from_urls


app = typer.Typer(
    name="spotify-downloader",
    help="Download Spotify playlists as audio files via YouTube Music",
    add_completion=False,
)


def setup_logging(verbose: bool) -> None:
    """
    Configure the logger based on verbosity level.
    
    Args:
        verbose: Whether to use DEBUG logging level
    """
    logger.remove()  # Remove default handler
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <green>{time:YYYY-MM-DD HH:mm:ss}</green> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
    )


@app.command()
def download(
    playlist_url: Annotated[
        str,
        typer.Argument(help="URL of the Spotify playlist to download")
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output", "-o",
            help="Output directory for downloaded files"
        )
    ] = Path.cwd() / "downloads",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
):
    """
    Download all songs from a Spotify playlist.
    
    The songs are searched on YouTube Music and downloaded as M4A audio files.
    """
    setup_logging(verbose)
    
    logger.info(f"Starting download of playlist: {playlist_url}")
    logger.info(f"Files will be saved to: {output.absolute()}")
    
    try:
        # Get playlist information from Spotify
        playlist_info = get_playlist_info(playlist_url)
        
        # Get YouTube Music URLs for each song
        download_urls = get_song_urls(playlist_info)
        
        # Download the songs
        download_from_urls(download_urls, output)
        
        logger.success(f"Download completed successfully. Files saved to {output.absolute()}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()