from datetime import datetime, timezone
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from googleapiclient.errors import HttpError

from utils.api_wrappers import YouTubeAPI
from models.video_metadata import VideoMetadata
from models.channel_info import ChannelInfo

pytestmark = pytest.mark.asyncio

class TestYouTubeAPIUnit:
    """Unit tests for YouTubeAPI class using mocks."""
    
    @pytest.fixture
    def mock_database(self):
        return MagicMock()
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config with no API key."""
        config = MagicMock()
        config.youtube_api_key = None
        return config
    
    async def test_init_without_api_key(self, mock_database, mock_config):
        """Test initialization without API key should still work but raise error on client creation."""
        with patch('utils.api_wrappers.config', mock_config):
            api = YouTubeAPI(database=mock_database)
            assert api.api_key is None
            with pytest.raises(ValueError, match="YouTube API key must be provided"):
                await api._get_youtube_client()
    
    @patch('googleapiclient.discovery.build')
    async def test_get_youtube_client(self, mock_build, mock_database):
        """Test YouTube client creation with API key."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client

        api = YouTubeAPI(database=mock_database)
        client = await api._get_youtube_client()
        
        assert client == mock_client
        mock_build.assert_called_once_with("youtube", "v3", developerKey=api.api_key)
    
    @patch('googleapiclient.discovery.build')
    async def test_fetch_channel_videos_success(self, mock_build, mock_database):
        """Test successful channel video fetching."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        # Mock response with multiple videos
        mock_search = MagicMock()
        mock_client.search.return_value = mock_search
        mock_search.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "video1"},
                    "snippet": {
                        "title": "Test Video 1",
                        "description": "Description 1",
                        "publishedAt": "2024-01-01T00:00:00Z"
                    }
                },
                {
                    "id": {"videoId": "video2"},
                    "snippet": {
                        "title": "Test Video 2",
                        "description": "Description 2",
                        "publishedAt": "2024-01-02T00:00:00Z"
                    }
                }
            ]
        }

        api = YouTubeAPI(database=mock_database)
        videos = await api.fetch_channel_videos("test_channel")
        
        assert len(videos) == 2
        assert all(isinstance(v, VideoMetadata) for v in videos)
        assert videos[0].youtube_video_id == "video1"
        assert videos[1].youtube_video_id == "video2"

        # Verify correct API call
        mock_search.list.assert_called_once_with(
            part="snippet",
            channelId="test_channel",
            order="date",
            type="video",
            maxResults=50
        )
    
    @patch('googleapiclient.discovery.build')
    async def test_fetch_channel_videos_empty(self, mock_build, mock_database):
        """Test channel video fetching with no results."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        mock_client.search().list().execute.return_value = {"items": []}

        api = YouTubeAPI(database=mock_database)
        videos = await api.fetch_channel_videos("test_channel")
        assert videos == []
    
    @patch('googleapiclient.discovery.build')
    async def test_fetch_channel_videos_quota_exceeded(self, mock_build, mock_database):
        """Test handling of quota exceeded error."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        resp = MagicMock()
        resp.status = 403
        mock_client.search().list().execute.side_effect = HttpError(
            resp=resp,
            content=b'{"error": {"code": 403, "message": "Quota exceeded"}}'
        )

        api = YouTubeAPI(database=mock_database)
        videos = await api.fetch_channel_videos("test_channel")
        assert videos == []
    
    @patch('googleapiclient.discovery.build')
    async def test_fetch_playlist_videos_success(self, mock_build, mock_database):
        """Test successful playlist video fetching."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        mock_playlist = MagicMock()
        mock_client.playlistItems.return_value = mock_playlist
        mock_playlist.list.return_value.execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "resourceId": {"videoId": "video1"},
                        "title": "Playlist Video 1",
                        "description": "Description 1",
                        "channelId": "channel1",
                        "publishedAt": "2024-01-01T00:00:00Z"
                    }
                }
            ]
        }

        api = YouTubeAPI(database=mock_database)
        videos = await api.fetch_playlist_videos("test_playlist")
        
        assert len(videos) == 1
        assert isinstance(videos[0], VideoMetadata)
        assert videos[0].youtube_video_id == "video1"
        assert videos[0].channel_id == "channel1"

        # Verify correct API call
        mock_playlist.list.assert_called_once_with(
            part="snippet",
            playlistId="test_playlist",
            maxResults=50
        )
    
    @patch('googleapiclient.discovery.build')
    async def test_fetch_channel_info_success(self, mock_build, mock_database):
        """Test successful channel info fetching."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        mock_channels = MagicMock()
        mock_client.channels.return_value = mock_channels
        mock_channels.list.return_value.execute.return_value = {
            "items": [{
                "snippet": {
                    "title": "Test Channel",
                    "description": "Channel Description"
                }
            }]
        }

        api = YouTubeAPI(database=mock_database)
        channel_info = await api.fetch_channel_info("test_channel")
        
        assert isinstance(channel_info, ChannelInfo)
        assert channel_info.youtube_channel_id == "test_channel"
        assert channel_info.title == "Test Channel"
        assert channel_info.description == "Channel Description" 