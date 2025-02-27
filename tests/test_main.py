"""
Unit tests for the Spotify Playlist Downloader.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from main import (
    SongInfo,
    PlaylistDownloader,
    get_playlist_info,
    get_song_urls,
    download_from_urls,
)


class TestSongInfo:
    """Tests for the SongInfo Pydantic model."""
    
    def test_song_info_creation(self):
        """Test creating a SongInfo instance."""
        song = SongInfo(
            title="Bohemian Rhapsody",
            artist="Queen",
            length=354000,
        )
        
        assert song.title == "Bohemian Rhapsody"
        assert song.artist == "Queen"
        assert song.length == 354000


class TestPlaylistDownloader:
    """Tests for the PlaylistDownloader class."""
    
    @pytest.fixture
    def downloader(self):
        """Create a PlaylistDownloader instance for testing."""
        return PlaylistDownloader()
    
    def test_convert_to_milliseconds(self, downloader):
        """Test conversion of MM:SS format to milliseconds."""
        assert downloader._convert_to_milliseconds("3:45") == 225000
        assert downloader._convert_to_milliseconds("0:30") == 30000
        assert downloader._convert_to_milliseconds("1:00") == 60000
    
    @patch('main.Public')
    def test_get_playlist_info(self, mock_public, downloader):
        """Test fetching playlist information from Spotify."""
        # Mock Spotify API response
        mock_playlist_data = {
            "items": [
                {
                    "itemV2": {
                        "data": {
                            "name": "Song 1",
                            "artists": {
                                "items": [
                                    {
                                        "profile": {
                                            "name": "Artist 1"
                                        }
                                    }
                                ]
                            },
                            "trackDuration": {
                                "totalMilliseconds": 180000
                            }
                        }
                    }
                },
                {
                    "itemV2": {
                        "data": {
                            "name": "Song 2",
                            "artists": {
                                "items": [
                                    {
                                        "profile": {
                                            "name": "Artist 2"
                                        }
                                    }
                                ]
                            },
                            "trackDuration": {
                                "totalMilliseconds": 240000
                            }
                        }
                    }
                }
            ]
        }
        
        mock_public.playlist_info.return_value = iter([mock_playlist_data])
        
        # Call the method
        result = downloader.get_playlist_info("spotify:playlist:123456")
        
        # Verify the result
        assert len(result) == 2
        assert result[0].title == "Song 1"
        assert result[0].artist == "Artist 1"
        assert result[0].length == 180000
        assert result[1].title == "Song 2"
        assert result[1].artist == "Artist 2"
        assert result[1].length == 240000
        
        # Verify the API was called with the correct parameters
        mock_public.playlist_info.assert_called_once_with("spotify:playlist:123456")
    
    @patch('main.InnerTube')
    def test_client_lazy_loading(self, mock_innertube, downloader):
        """Test that the InnerTube client is lazily loaded."""
        # Client should initially be None
        assert downloader._client is None
        
        # Accessing the client property should create an instance
        client = downloader.client
        assert client is not None
        
        # The InnerTube constructor should have been called once
        mock_innertube.assert_called_once_with("WEB_REMIX", "1.20250203.01.00")
    
    @patch.object(PlaylistDownloader, 'client')
    def test_get_song_url_top_result(self, mock_client, downloader):
        """Test getting a song URL when top result is closer."""
        # Create a SongInfo object
        song_info = SongInfo(
            title="Bohemian Rhapsody",
            artist="Queen",
            length=354000,  # 5:54
        )
        
        # Mock search response where top result is closer to expected length
        mock_search_data = {
            "contents": {
                "tabbedSearchResultsRenderer": {
                    "tabs": [
                        {
                            "tabRenderer": {
                                "content": {
                                    "sectionListRenderer": {
                                        "contents": [
                                            {
                                                "musicCardShelfRenderer": {
                                                    "title": {
                                                        "runs": [
                                                            {
                                                                "text": "Bohemian Rhapsody",
                                                                "navigationEndpoint": {
                                                                    "watchEndpoint": {
                                                                        "videoId": "top_video_id"
                                                                    }
                                                                }
                                                            }
                                                        ]
                                                    },
                                                    "subtitle": {
                                                        "runs": [
                                                            {"text": "Queen · Song · "},
                                                            {"text": "5:55"}  # Closer to expected length
                                                        ]
                                                    }
                                                }
                                            },
                                            {
                                                "musicShelfRenderer": {
                                                    "contents": [
                                                        {
                                                            "musicResponsiveListItemRenderer": {
                                                                "flexColumns": [
                                                                    {
                                                                        "musicResponsiveListItemFlexColumnRenderer": {
                                                                            "text": {
                                                                                "runs": [
                                                                                    {"text": "Bohemian Rhapsody"}
                                                                                ]
                                                                            }
                                                                        }
                                                                    },
                                                                    {
                                                                        "musicResponsiveListItemFlexColumnRenderer": {
                                                                            "text": {
                                                                                "runs": [
                                                                                    {"text": "Queen · "},
                                                                                    {"text": "6:07"}  # Further from expected length
                                                                                ]
                                                                            }
                                                                        }
                                                                    }
                                                                ],
                                                                "overlay": {
                                                                    "musicItemThumbnailOverlayRenderer": {
                                                                        "content": {
                                                                            "musicPlayButtonRenderer": {
                                                                                "playNavigationEndpoint": {
                                                                                    "watchEndpoint": {
                                                                                        "videoId": "list_video_id"
                                                                                    }
                                                                                }
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        mock_client.search.return_value = mock_search_data
        
        # Call the method
        url, title = downloader.get_song_url(song_info)
        
        # Verify the result
        assert url == "https://music.youtube.com/watch?v=top_video_id"
        assert title == "Bohemian Rhapsody"
        
        # Verify the search was called with the correct query
        mock_client.search.assert_called_once_with("Bohemian Rhapsody Queen")
    
    @patch.object(PlaylistDownloader, 'get_song_url')
    @patch('main.sleep')
    def test_get_song_urls(self, mock_sleep, mock_get_song_url, downloader):
        """Test getting URLs for all songs in a playlist."""
        # Create test data
        song1 = SongInfo(title="Song 1", artist="Artist 1", length=180000)
        song2 = SongInfo(title="Song 2", artist="Artist 2", length=240000)
        playlist_info = [song1, song2]
        
        # Mock get_song_url to return specific URLs
        mock_get_song_url.side_effect = [
            ("https://music.youtube.com/watch?v=id1", "Song 1 - Artist 1"),
            ("https://music.youtube.com/watch?v=id2", "Song 2 - Artist 2"),
        ]
        
        # Call the method
        result = downloader.get_song_urls(playlist_info)
        
        # Verify the result
        assert result == [
            "https://music.youtube.com/watch?v=id1",
            "https://music.youtube.com/watch?v=id2",
        ]
        
        # Verify get_song_url was called for each song
        assert mock_get_song_url.call_count == 2
        mock_get_song_url.assert_has_calls([
            call(song1),
            call(song2),
        ])
        
        # Verify sleep was called between requests
        assert mock_sleep.call_count == 2
    
    @patch('main.YoutubeDL')
    def test_download_from_urls(self, mock_ytdl, downloader):
        """Test downloading songs from URLs."""
        # Test data
        urls = [
            "https://music.youtube.com/watch?v=id1",
            "https://music.youtube.com/watch?v=id2",
        ]
        download_path = Path("/test/downloads")
        
        # Mock Path.exists and Path.mkdir
        with patch.object(Path, 'exists', return_value=False) as mock_exists:
            with patch.object(Path, 'mkdir') as mock_mkdir:
                # Mock YoutubeDL context manager
                mock_ytdl_instance = MagicMock()
                mock_ytdl.return_value.__enter__.return_value = mock_ytdl_instance
                
                # Call the method
                PlaylistDownloader.download_from_urls(urls, download_path)
                
                # Verify directory was created
                mock_exists.assert_called_once()
                mock_mkdir.assert_called_once_with(parents=True)
                
                # Verify YoutubeDL was called with the correct options and URLs
                mock_ytdl_instance.download.assert_called_once_with(urls)


@patch('main.PlaylistDownloader')
def test_get_playlist_info_function(mock_downloader_class):
    """Test the get_playlist_info helper function."""
    # Setup mock
    mock_instance = MagicMock()
    mock_downloader_class.return_value = mock_instance
    
    mock_instance.get_playlist_info.return_value = [
        SongInfo(title="Song 1", artist="Artist 1", length=180000)
    ]
    
    # Call the function
    result = get_playlist_info("spotify:playlist:123456")
    
    # Verify the downloader was created and its method was called
    mock_downloader_class.assert_called_once()
    mock_instance.get_playlist_info.assert_called_once_with("spotify:playlist:123456")
    
    # Verify the result was returned correctly
    assert result == mock_instance.get_playlist_info.return_value


@patch('main.PlaylistDownloader')
def test_get_song_urls_function(mock_downloader_class):
    """Test the get_song_urls helper function."""
    # Setup mock
    mock_instance = MagicMock()
    mock_downloader_class.return_value = mock_instance
    
    playlist_info = [
        SongInfo(title="Song 1", artist="Artist 1", length=180000)
    ]
    
    mock_instance.get_song_urls.return_value = [
        "https://music.youtube.com/watch?v=id1"
    ]
    
    # Call the function
    result = get_song_urls(playlist_info)
    
    # Verify the downloader was created and its method was called
    mock_downloader_class.assert_called_once()
    mock_instance.get_song_urls.assert_called_once_with(playlist_info)
    
    # Verify the result was returned correctly
    assert result == mock_instance.get_song_urls.return_value


@patch.object(PlaylistDownloader, 'download_from_urls')
def test_download_from_urls_function(mock_download_method):
    """Test the download_from_urls helper function."""
    # Test data
    urls = ["https://music.youtube.com/watch?v=id1"]
    download_path = Path("/test/downloads")
    
    # Call the function
    download_from_urls(urls, download_path)
    
    # Verify the static method was called with the correct parameters
    mock_download_method.assert_called_once_with(urls, download_path)