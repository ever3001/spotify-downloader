"""
Spotify Playlist Downloader.

This module provides functionality to download music from Spotify playlists
by searching for corresponding songs on YouTube Music and downloading them.
"""

from typing import List, Tuple
from pathlib import Path
from time import sleep
from random import uniform
from loguru import logger

from pydantic import BaseModel, Field
from spotapi import Public
from innertube import InnerTube
from yt_dlp import YoutubeDL


class SongInfo(BaseModel):
    """Model representing information about a song in a playlist."""
    title: str = Field(..., description="Title of the song")
    artist: str = Field(..., description="Primary artist of the song")
    length: int = Field(..., description="Length of the song in milliseconds")


class PlaylistDownloader:
    """Handles the downloading of Spotify playlists via YouTube Music."""
    
    def __init__(self):
        """Initialize the PlaylistDownloader with a None InnerTube client."""
        self._client = None
    
    @property
    def client(self) -> InnerTube:
        """
        Lazy-loaded InnerTube client.
        
        Returns:
            InnerTube: The initialized InnerTube client
        """
        if self._client is None:
            self._client = InnerTube("WEB_REMIX", "1.20250203.01.00")
        return self._client
    
    def get_playlist_info(self, playlist_id: str) -> List[SongInfo]:
        """
        Extract song data from a Spotify playlist.
        
        Args:
            playlist_id: The Spotify playlist ID or URL
            
        Returns:
            List of SongInfo objects containing song metadata
        """
        logger.info(f"Fetching playlist with ID: {playlist_id}")
        items = next(Public.playlist_info(playlist_id))["items"]
        
        result: List[SongInfo] = []
        
        for item in items:
            item_data = item["itemV2"]["data"]
            song = SongInfo(
                title=item_data["name"],
                artist=item_data["artists"]["items"][0]["profile"]["name"],
                length=int(item_data["trackDuration"]["totalMilliseconds"])
            )
            result.append(song)
        
        logger.info(f"Found {len(result)} songs in playlist")
        return result
    
    @staticmethod
    def _convert_to_milliseconds(text: str) -> int:
        """
        Convert MM:SS timestamp from YouTube Music to milliseconds.
        
        Args:
            text: String timestamp in "MM:SS" format
            
        Returns:
            Equivalent time in milliseconds
        """
        minutes, seconds = text.split(":")
        return (int(minutes) * 60 + int(seconds)) * 1000
    
    def get_song_url(self, song_info: SongInfo) -> Tuple[str, str]:
        """
        Search for a song on YouTube Music and return the URL of the closest match.
        
        Args:
            song_info: SongInfo object containing song metadata
            
        Returns:
            Tuple of (url, video_title)
        """
        search_query = f"{song_info.title} {song_info.artist}"
        logger.debug(f"Searching for: {search_query}")
        
        data = self.client.search(search_query)
        
        # Handle "did you mean" case
        if "itemSectionRenderer" in data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]:
            del data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]
        
        # Extract data from search results
        try:
            # Top result
            top_result_length = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]["musicCardShelfRenderer"]["subtitle"]["runs"][-1]["text"]
            top_result_diff = abs(self._convert_to_milliseconds(top_result_length) - song_info.length)
            
            # First song in list
            first_song_length = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][1]["musicShelfRenderer"]["contents"][0]["musicResponsiveListItemRenderer"]["flexColumns"][1]["musicResponsiveListItemFlexColumnRenderer"]["text"]["runs"][-1]["text"]
            first_song_diff = abs(self._convert_to_milliseconds(first_song_length) - song_info.length)
            
            # Choose the result closest to the expected length
            if top_result_diff < first_song_diff:
                # Get top result url
                video_id = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]["musicCardShelfRenderer"]["title"]["runs"][0]["navigationEndpoint"]["watchEndpoint"]["videoId"]
                video_title = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]["musicCardShelfRenderer"]["title"]["runs"][0]["text"]
            else:
                # Get first song result url
                video_id = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][1]["musicShelfRenderer"]["contents"][0]["musicResponsiveListItemRenderer"]["overlay"]["musicItemThumbnailOverlayRenderer"]["content"]["musicPlayButtonRenderer"]["playNavigationEndpoint"]["watchEndpoint"]["videoId"]
                video_title = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][1]["musicShelfRenderer"]["contents"][0]["musicResponsiveListItemRenderer"]["flexColumns"][0]["musicResponsiveListItemFlexColumnRenderer"]["text"]["runs"][0]["text"]
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing search results for {search_query}: {e}")
            raise ValueError(f"Failed to find matching song for {song_info.title} by {song_info.artist}")
        
        url = f"https://music.youtube.com/watch?v={video_id}"
        
        return url, video_title
    
    def get_song_urls(self, playlist_info: List[SongInfo]) -> List[str]:
        """
        Get YouTube Music URLs for all songs in a playlist.
        
        Args:
            playlist_info: List of SongInfo objects
            
        Returns:
            List of YouTube Music URLs
        """
        urls = []
        
        for song_info in playlist_info:
            logger.info(f"Getting URL for {song_info.title} by {song_info.artist}")
            try:
                url, title = self.get_song_url(song_info)
                urls.append(url)
                logger.debug(f"Found: {title} ({url})")
                # Add random delay to avoid rate limiting
                sleep(uniform(1, 3))
            except Exception as e:
                logger.error(f"Failed to get URL for {song_info.title}: {e}")
        
        return urls
    
    @staticmethod
    def download_from_urls(urls: List[str], download_path: Path) -> None:
        """
        Download songs from YouTube Music URLs.
        
        Args:
            urls: List of YouTube Music URLs
            download_path: Directory path for downloaded files
        """
        if not urls:
            logger.warning("No URLs to download")
            return
            
        logger.info(f"Downloading {len(urls)} songs to {download_path}")
        
        # Create download directory if it doesn't exist
        if not download_path.exists():
            download_path.mkdir(parents=True)
            
        # Options for yt-dlp
        options = {
            "extract_flat": "discard_in_playlist",
            "final_ext": "m4a",
            "format": "bestaudio/best",
            "fragment_retries": 10,
            "ignoreerrors": "only_download",
            "outtmpl": {"default": f"{download_path}/%(title)s.%(ext)s"},
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "nopostoverwrites": False,
                    "preferredcodec": "m4a",
                    "preferredquality": "5"
                },
                {
                    "add_chapters": True,
                    "add_infojson": "if_exists",
                    "add_metadata": True,
                    "key": "FFmpegMetadata"
                },
                {
                    "key": "FFmpegConcat",
                    "only_multi_video": True,
                    "when": "playlist"
                }
            ],
            "logger": logger,
            "retries": 10
        }
        
        # Downloads stream with highest bitrate, then saves them in m4a format
        with YoutubeDL(options) as ydl:
            ydl.download(urls)
        
        logger.success(f"Download complete. Files saved to {download_path}")


def get_playlist_info(playlist_id: str) -> List[SongInfo]:
    """
    Extract song data from a Spotify playlist.
    
    Args:
        playlist_id: The Spotify playlist ID or URL
        
    Returns:
        List of SongInfo objects containing song metadata
    """
    downloader = PlaylistDownloader()
    return downloader.get_playlist_info(playlist_id)


def get_song_urls(playlist_info: List[SongInfo]) -> List[str]:
    """
    Get YouTube Music URLs for all songs in a playlist.
    
    Args:
        playlist_info: List of SongInfo objects
        
    Returns:
        List of YouTube Music URLs
    """
    downloader = PlaylistDownloader()
    return downloader.get_song_urls(playlist_info)


def download_from_urls(urls: List[str], download_path: Path = Path.cwd() / "downloads") -> None:
    """
    Download songs from YouTube Music URLs.
    
    Args:
        urls: List of YouTube Music URLs
        download_path: Directory path for downloaded files
    """
    PlaylistDownloader.download_from_urls(urls, download_path)