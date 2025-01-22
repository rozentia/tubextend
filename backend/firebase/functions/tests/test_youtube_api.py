from datetime import datetime, timezone, timedelta
from unittest import mock
from unittest.mock import patch, MagicMock, AsyncMock
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import pytest
from googleapiclient.errors import HttpError
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncio
from typing import cast

from utils.api_wrappers import YouTubeAPI
from utils.database import Database
from models.video_metadata import VideoMetadata
from models.channel_info import ChannelInfo

# Load test environment variables
test_env_path = Path(__file__).parent.parent / 'test.env'
if test_env_path.exists():
    load_dotenv(test_env_path)

pytestmark = pytest.mark.asyncio  # Mark all tests in this module as async

@pytest.fixture
async def database():
    """Fixture to create real database connection."""
    db = Database()
    yield db

@pytest.fixture
async def youtube_api(database):
    """Fixture to create YouTubeAPI instance with real API key."""
    api = YouTubeAPI(database=database)
    return api

@pytest.fixture
def test_channel_ids():
    """Get test channel IDs from environment."""
    channels = [
        os.getenv('TEST_CHANNEL_ID_1'),
        os.getenv('TEST_CHANNEL_ID_2'),
        os.getenv('TEST_CHANNEL_ID_3')
    ]
    # Verify that we have valid channel IDs (should start with UC)
    assert all(channels), "All TEST_CHANNEL_ID_* environment variables must be set"
    assert all(c.startswith('UC') for c in channels), "All channel IDs must start with 'UC'"
    return channels

@pytest.fixture
def test_playlist_ids():
    """Get test playlist IDs from environment."""
    playlists = [
        os.getenv('TEST_PLAYLIST_ID_1'),
        os.getenv('TEST_PLAYLIST_ID_2'),
        os.getenv('TEST_PLAYLIST_ID_3')
    ]
    # Verify that we have valid playlist IDs (should start with PL)
    assert all(playlists), "All TEST_PLAYLIST_ID_* environment variables must be set"
    assert all(p.startswith('PL') for p in playlists), "All playlist IDs must start with 'PL'"
    return playlists

class TestYouTubeAPIIntegration:
    """Integration tests for YouTubeAPI class using real API calls."""

    @pytest.mark.integration
    async def test_fetch_channel_videos(self, youtube_api, test_channel_ids):
        """Test fetching videos from real channels."""
        for channel_id in test_channel_ids:
            videos = await youtube_api.fetch_channel_videos(channel_id)
            
            # Verify we get videos and respect the limit
            assert videos, f"No videos found for channel {channel_id}"
            assert len(videos) <= 50, f"Too many videos returned for channel {channel_id}"
            assert all(isinstance(v, VideoMetadata) for v in videos)
            
            # Verify video metadata structure
            for video in videos:
                assert video.youtube_video_id
                assert video.title
                assert video.channel_id == channel_id
                assert str(video.url).startswith('https://www.youtube.com/watch?v=')
                assert isinstance(video.uploaded_at, datetime)
                
            # Rate limiting pause between channels
            await asyncio.sleep(1)

    @pytest.mark.integration
    async def test_fetch_playlist_videos(self, youtube_api, test_playlist_ids):
        """Test fetching videos from real playlists."""
        for playlist_id in test_playlist_ids:
            videos = await youtube_api.fetch_playlist_videos(playlist_id)
            
            # Verify we get videos and respect the limit
            assert videos, f"No videos found for playlist {playlist_id}"
            assert len(videos) <= 50, f"Too many videos returned for playlist {playlist_id}"
            assert all(isinstance(v, VideoMetadata) for v in videos)
            
            # Verify video metadata structure
            for video in videos:
                assert video.youtube_video_id
                assert video.title
                assert video.channel_id  # Channel ID should be present
                assert str(video.url).startswith('https://www.youtube.com/watch?v=')
                assert isinstance(video.uploaded_at, datetime)
            
            # Rate limiting pause between playlists
            await asyncio.sleep(1)

    @pytest.mark.integration
    async def test_fetch_channel_info(self, youtube_api, test_channel_ids):
        """Test fetching channel information."""
        for channel_id in test_channel_ids:
            channel_info = await youtube_api.fetch_channel_info(channel_id)
            
            # Verify channel info
            assert channel_info, f"No channel info found for {channel_id}"
            assert isinstance(channel_info, ChannelInfo)
            assert channel_info.youtube_channel_id == channel_id
            assert channel_info.title
            assert channel_info.description
            assert channel_info.channel_url == f"https://www.youtube.com/channel/{channel_id}"
            
            # Rate limiting pause between channels
            await asyncio.sleep(1)

    @pytest.mark.integration
    async def test_nonexistent_channel(self, youtube_api):
        """Test fetching info for a nonexistent channel."""
        channel_info = await youtube_api.fetch_channel_info("UC_nonexistent_channel_id_123456789")
        assert channel_info is None

    @pytest.mark.integration
    async def test_nonexistent_playlist(self, youtube_api):
        """Test fetching videos from a nonexistent playlist."""
        videos = await youtube_api.fetch_playlist_videos("PL_nonexistent_playlist_id_123456789")
        assert videos == []

    @pytest.mark.integration
    async def test_rate_limiting(self, youtube_api, test_channel_ids):
        """Test rate limiting with real API calls."""
        channel_id = test_channel_ids[0]
        
        # Make multiple quick requests
        results = []
        for _ in range(3):
            videos = await youtube_api.fetch_channel_videos(channel_id)
            results.append(bool(videos))
            await asyncio.sleep(1)  # Increased delay to avoid rate limiting
        
        # All requests should succeed with rate limiting
        assert all(results), "Rate limiting caused request failures"

    @pytest.mark.integration
    async def test_database_integration(self, youtube_api, database, test_channel_ids):
        """Test integration between YouTube API and database."""
        channel_id = test_channel_ids[0]
        
        # Fetch channel info and verify storage
        channel_info = await youtube_api.fetch_channel_info(channel_id)
        assert channel_info
        
        stored_channel = database.get_channel(youtube_channel_id=channel_id)
        if stored_channel:
            assert stored_channel.youtube_channel_id == channel_id
            assert stored_channel.title == channel_info.title
        
        # Fetch videos and verify they can be stored
        videos = await youtube_api.fetch_channel_videos(channel_id)
        assert videos
        
        for video in videos[:5]:  # Test with first 5 videos
            stored_video = database.get_video(youtube_video_id=video.youtube_video_id)
            if stored_video:
                assert stored_video.youtube_video_id == video.youtube_video_id
                assert stored_video.title == video.title
    