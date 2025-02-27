from typing import TypedDict

from spotapi import Public
from innertube import InnerTube
from yt_dlp import YoutubeDL

from time import sleep
from random import uniform
from loguru import logger
from pathlib import Path

client = None


class PlaylistInfo(TypedDict):
    title: str
    artist: str
    length: int


def get_playlist_info(playlist_id: str) -> list[PlaylistInfo]:
    """Extracts data from Spotify and return them in format
       `[{"title": title, "artist": artist, "length": length}]`."""

    items = next(Public.playlist_info(playlist_id))["items"]

    result: list[PlaylistInfo] = []

    for item in items:
        item = item["itemV2"]["data"]
        song: PlaylistInfo = {
            "title": item["name"],
            "artist": item["artists"]["items"][0]["profile"]["name"],
            "length": int(item["trackDuration"]["totalMilliseconds"])
        }
        result.append(song)

    return result


def convert_to_milliseconds(text: str) -> int:
    """Converts `"%M:%S"` timestamp from YTMusic to milliseconds."""
    minutes, seconds = text.split(":")
    return (int(minutes) * 60 + int(seconds)) * 1000


def get_song_url(song_info: PlaylistInfo) -> tuple[str, str]:
    """Simulates searching from the YTMusic web and returns url to the
    closest match."""

    global client
    if client is None:
        client = InnerTube("WEB_REMIX", "1.20250203.01.00")
    data = client.search(f"{song_info['title']} {song_info['artist']}")

    # handle "did you mean" case
    if "itemSectionRenderer" in data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]:  # noqa: E501
        del data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]  # noqa: E501

    top_result_length = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]["musicCardShelfRenderer"]["subtitle"]["runs"][-1]["text"]  # noqa: E501
    first_song_length = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][1]["musicShelfRenderer"]["contents"][0]["musicResponsiveListItemRenderer"]["flexColumns"][1]["musicResponsiveListItemFlexColumnRenderer"]["text"]["runs"][-1]["text"]  # noqa: E501

    top_result_diff = abs(convert_to_milliseconds(top_result_length) - song_info["length"])  # noqa: E501
    first_song_diff = abs(convert_to_milliseconds(first_song_length) - song_info["length"])  # noqa: E501

    if top_result_diff < first_song_diff:
        # get top result url
        video_id = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]["musicCardShelfRenderer"]["title"]["runs"][0]["navigationEndpoint"]["watchEndpoint"]["videoId"]  # noqa: E501
        video_title = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]["musicCardShelfRenderer"]["title"]["runs"][0]["text"]  # noqa: E501
    else:
        # get first song result url
        video_id = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][1]["musicShelfRenderer"]["contents"][0]["musicResponsiveListItemRenderer"]["overlay"]["musicItemThumbnailOverlayRenderer"]["content"]["musicPlayButtonRenderer"]["playNavigationEndpoint"]["watchEndpoint"]["videoId"]  # noqa: E501
        video_title = data["contents"]["tabbedSearchResultsRenderer"]["tabs"][0]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][1]["musicShelfRenderer"]["contents"][0]["musicResponsiveListItemRenderer"]["flexColumns"][0]["musicResponsiveListItemFlexColumnRenderer"]["text"]["runs"][0]["text"]  # noqa: E501

    url = "https://music.youtube.com/watch?v=" + video_id

    return url, video_title


def get_song_urls(playlist_info: list[PlaylistInfo]) -> list[str]:
    """Repeatedly calls get_song_url on given playlist info. Returns
    list of results."""
    urls = []

    for song_info in playlist_info:
        logger.info(f"Getting url for {song_info['title']}")
        url, title = get_song_url(song_info)
        urls.append(url)
        logger.debug(f"{title} ({url})")
        sleep(uniform(1, 3))

    return urls


def download_from_urls(urls: list[str], download_path: Path) -> None:
    """Downloads list of songs with yt-dlp"""
    
    if not download_path.exists():
        download_path.mkdir(parents=True)
    # options generated from https://github.com/yt-dlp/yt-dlp/blob/master/devscripts/cli_to_api.py  # noqa: E501
    options = {"extract_flat": "discard_in_playlist",
               "final_ext": "m4a",
               "format": "bestaudio/best",
               "fragment_retries": 10,
               "ignoreerrors": "only_download",
               "outtmpl": {"default": f"{download_path}/%(title)s.%(ext)s"},
               "postprocessors": [{"key": "FFmpegExtractAudio",
                                   "nopostoverwrites": False,
                                   "preferredcodec": "m4a",
                                   "preferredquality": "5"},
                                  {"add_chapters": True,
                                   "add_infojson": "if_exists",
                                   "add_metadata": True,
                                   "key": "FFmpegMetadata"},
                                  {"key": "FFmpegConcat",
                                   "only_multi_video": True,
                                   "when": "playlist"}],
               "logger": logger,
               "retries": 10}

    # downloads stream with highest bitrate, then save them in m4a format
    with YoutubeDL(options) as ydl:
        ydl.download(urls)


def main(playlist_id: str):
    playlist_info = get_playlist_info(playlist_id)
    download_urls = get_song_urls(playlist_info)
    download_from_urls(download_urls)
