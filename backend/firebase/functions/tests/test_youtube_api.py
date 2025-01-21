from datetime import datetime, timezone, timedelta
from unittest import mock
from unittest.mock import patch, MagicMock
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import pytest
from googleapiclient.errors import HttpError
import os
from pathlib import Path
from dotenv import load_dotenv

from utils.api_wrappers import YouTubeAPI

# Load test environment variables
test_env_path = Path(__file__).parent.parent / 'test.env'
if test_env_path.exists():
    load_dotenv(test_env_path)

pytestmark = pytest.mark.asyncio  # Mark all tests in this module as async

class TestYouTubeAPI:
    """Integration tests for YouTubeAPI class."""
    
    @pytest.fixture
    def youtube_api(self, db):
        """Fixture to create YouTubeAPI instance."""
        api = YouTubeAPI(database=db)
        return api
    
    async def test_get_credentials(self, youtube_api, test_data):
        """Test credentials retrieval and refresh."""
        real_refresh_token = os.getenv('YOUTUBE_REAL_REFRESH_TOKEN')
        token_expiry = os.getenv('YOUTUBE_TOKEN_EXPIRY')
        
        if not real_refresh_token or not token_expiry:
            pytest.skip("No real YouTube refresh token available in test.env")
            
        try:
            expiry = datetime.fromisoformat(token_expiry)
            if expiry <= datetime.now(timezone.utc):
                pytest.skip("YouTube refresh token has expired. Please run get_youtube_token.py to get a new token.")
        except ValueError:
            pytest.skip("Invalid token expiry format in test.env")
        
        # Update test user with real refresh token
        youtube_api.database.update_user(test_data["user"].id, {
            "refresh_token": real_refresh_token,
            "token_expires_at": expiry
        })
        
        # Test getting credentials
        credentials = await youtube_api._get_credentials(test_data["user"].id)
        assert credentials is not None
        assert credentials.refresh_token == real_refresh_token
    
    async def test_youtube_client_creation(self, youtube_api, test_data):
        """Test YouTube client creation."""
        real_refresh_token = os.getenv('YOUTUBE_REAL_REFRESH_TOKEN')
        token_expiry = os.getenv('YOUTUBE_TOKEN_EXPIRY')
        
        if not real_refresh_token or not token_expiry:
            pytest.skip("No real YouTube refresh token available in test.env")
        
        # Update test user with real refresh token
        youtube_api.database.update_user(test_data["user"].id, {
            "refresh_token": real_refresh_token,
            "token_expires_at": datetime.fromisoformat(token_expiry)
        })
        
        # Test client creation with OAuth
        client = await youtube_api._get_youtube_client(test_data["user"].id)
        assert client is not None
        
        # Test a simple API call
        channel_response = client.channels().list(
            part="snippet",
            mine=True
        ).execute()
        assert "items" in channel_response
    
    async def test_fetch_channel_videos(self, youtube_api, test_data):
        """Test fetching channel videos."""
        real_refresh_token = os.getenv('YOUTUBE_REAL_REFRESH_TOKEN')
        token_expiry = os.getenv('YOUTUBE_TOKEN_EXPIRY')
        
        if not real_refresh_token or not token_expiry:
            pytest.skip("No real YouTube refresh token available in test.env")
        
        # Update test user with real refresh token
        youtube_api.database.update_user(test_data["user"].id, {
            "refresh_token": real_refresh_token,
            "token_expires_at": datetime.fromisoformat(token_expiry)
        })
        
        # Get the user's channel ID from the API
        client = await youtube_api._get_youtube_client(test_data["user"].id)
        channel_response = client.channels().list(
            part="id",
            mine=True
        ).execute()
        
        if not channel_response.get("items"):
            pytest.skip("No YouTube channels found for the authenticated user")
            
        channel_id = channel_response["items"][0]["id"]
        
        # Test fetching videos
        videos = await youtube_api.fetch_channel_videos(
            channel_id=channel_id,
            user_id=test_data["user"].id
        )
        
        assert isinstance(videos, list)
    
    @pytest.mark.unit
    @patch('googleapiclient.discovery.build')
    async def test_youtube_client_mock(self, mock_build, youtube_api):
        """Unit test for client creation with mocks."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        client = await youtube_api._get_youtube_client()
        assert client == mock_client
    
    @patch('googleapiclient.discovery.build')
    async def test_fetch_channel_videos_with_oauth(self, mock_build, youtube_api, test_data):
        """Test fetching channel videos using OAuth credentials."""
        # Mock YouTube client and response
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        mock_client.search().list().execute.return_value = {
            "items": [{
                "id": {"videoId": "test_video_id"},
                "snippet": {
                    "title": "Test Video",
                    "description": "Test Description",
                    "publishedAt": datetime.now(timezone.utc).isoformat() + "Z"
                }
            }]
        }
        
        # Test fetching videos with OAuth
        videos = await youtube_api.fetch_channel_videos(
            channel_id="test_channel",
            user_id=test_data["user"].id
        )
        assert len(videos) == 1
        assert videos[0].youtube_video_id == "test_video_id"
        
        # Verify OAuth credentials were used
        mock_build.assert_called_with("youtube", "v3", credentials=mock.ANY)

    @patch('googleapiclient.discovery.build')
    async def test_fetch_channel_videos_quota_exceeded(self, mock_build, youtube_api, test_data):
        """Test handling of quota exceeded error."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        # Mock quota exceeded error
        resp = MagicMock()
        resp.status = 403
        mock_client.search().list().execute.side_effect = HttpError(
            resp=resp,
            content=b'{"error": {"code": 403, "message": "Quota exceeded"}}'
        )
        
        # Test quota exceeded handling
        videos = await youtube_api.fetch_channel_videos(
            channel_id="test_channel",
            user_id=test_data["user"].id
        )
        assert videos == []

    @patch('googleapiclient.discovery.build')
    async def test_fetch_playlist_videos_with_pagination(self, mock_build, youtube_api, test_data):
        """Test fetching playlist videos with pagination."""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        # Mock paginated responses
        mock_client.playlistItems().list().execute.side_effect = [
            {
                "items": [{
                    "snippet": {
                        "resourceId": {"videoId": "video1"},
                        "title": "Video 1",
                        "description": "Description 1",
                        "channelId": "channel1",
                        "publishedAt": datetime.now(timezone.utc).isoformat() + "Z"
                    }
                }],
                "nextPageToken": "token123"
            },
            {
                "items": [{
                    "snippet": {
                        "resourceId": {"videoId": "video2"},
                        "title": "Video 2",
                        "description": "Description 2",
                        "channelId": "channel1",
                        "publishedAt": datetime.now(timezone.utc).isoformat() + "Z"
                    }
                }]
            }
        ]
        
        # Test fetching videos with pagination
        videos = await youtube_api.fetch_playlist_videos(
            playlist_id="test_playlist",
            user_id=test_data["user"].id
        )
        assert len(videos) == 2
        assert videos[0].youtube_video_id == "video1"
        assert videos[1].youtube_video_id == "video2" 