import pytest
from datetime import datetime, timezone, timedelta
import uuid
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import aiohttp

from agents.channel_monitor import ChannelMonitorAgent
from models.user_info import UserInfo
from models.channel_info import ChannelInfo
from models.source_info import SourceInfo, SourceType
from models.video_metadata import VideoMetadata
from models.source_channel_info import SourceChannelInfo
from models.source_video_info import SourceVideoInfo
from models.generation_job import GenerationJob, JobStatus
from utils.database import Database
from utils.api_wrappers import YouTubeAPI
from tests.seed_test_data import seed_test_data
from tests.cleanup_test_data import cleanup_test_data
from utils.rss_fetcher import YouTubeRSSFetcher

# Load test environment variables
test_env_path = Path(__file__).parent.parent / 'test.env'
if test_env_path.exists():
    load_dotenv(test_env_path)

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="session")
def test_data():
    """Fixture to seed and return test data once per test session."""
    cleanup_test_data()
    return seed_test_data()

@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Cleanup fixture that runs once after all tests."""
    yield
    cleanup_test_data()

@pytest.fixture(scope="session")
async def database():
    """Create database connection for the session."""
    db = Database()
    yield db

@pytest.fixture(scope="session")
async def rss_fetcher():
    """Create YouTubeRSSFetcher instance for the session."""
    timeout = aiohttp.ClientTimeout(total=10)
    # Create session with proper context management
    session = aiohttp.ClientSession(timeout=timeout)
    try:
        fetcher = YouTubeRSSFetcher(session=session)
        yield fetcher
    finally:
        await session.close()

@pytest.fixture(scope="session")
async def youtube_api(database, rss_fetcher):
    """Create YouTubeAPI instance for the session."""
    # Pass the existing session from rss_fetcher to ensure we reuse the same session
    api = YouTubeAPI(database=database, session=rss_fetcher.session)
    yield api
    await api.close()

@pytest.fixture(scope="session")
async def channel_monitor(database, youtube_api):
    """Create ChannelMonitorAgent instance for the session."""
    monitor = ChannelMonitorAgent(database=database, youtube_api=youtube_api)
    yield monitor
    # No need to close here as youtube_api fixture will handle cleanup

@pytest.fixture(scope="session")
def test_channel_ids():
    """Get test channel IDs from environment."""
    channels = [
        os.getenv('TEST_CHANNEL_ID_1'),
        os.getenv('TEST_CHANNEL_ID_2'),
        os.getenv('TEST_CHANNEL_ID_3')
    ]
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
    assert all(playlists), "All TEST_PLAYLIST_ID_* environment variables must be set"
    assert all(p.startswith('PL') for p in playlists), "All playlist IDs must start with 'PL'"
    return playlists

class TestChannelMonitorAgentIntegration:
    """Integration tests for ChannelMonitorAgent."""

    async def _ensure_channels_exist(self, youtube_api, channel_ids):
        """Helper method to ensure channels exist in database before testing."""
        for channel_id in channel_ids:
            # Check if channel exists
            channel = youtube_api.database.get_channel(channel_id)
            if not channel:
                # Fetch and insert channel info if it doesn't exist
                channel_info = await youtube_api.fetch_channel_info(channel_id)
                if channel_info:
                    try:
                        youtube_api.database.insert_channel(channel_info)
                    except Exception as e:
                        print(f"Error inserting channel {channel_id}: {str(e)}")
                        raise
                else:
                    raise ValueError(f"Could not fetch info for channel {channel_id}")
            
            # Verify channel was inserted
            channel = youtube_api.database.get_channel(channel_id)
            if not channel:
                raise ValueError(f"Channel {channel_id} was not properly inserted")

    @pytest.fixture(scope="class")
    async def setup_test_channels(self, youtube_api, test_channel_ids):
        """Fixture to ensure test channels exist in database."""
        await self._ensure_channels_exist(youtube_api, test_channel_ids)
        return test_channel_ids
    
    #----------------------------------------------------------- TESTS

    @pytest.mark.integration
    async def test_run_with_channel_collection(self, channel_monitor, test_data, setup_test_channels):
        """Test monitoring a channel collection with real channels."""
        test_channel_ids = setup_test_channels
        
        # Create a new channel collection source for the test user
        source = SourceInfo(
            id=uuid.uuid4(),
            user_id=test_data["user"].id,
            name="Test Channel Collection",
            source_type=SourceType.CHANNEL_COLLECTION,
            preferences={}
        )
        channel_monitor.database.insert_source(source)
        
        # Add test channels to the collection
        for channel_id in test_channel_ids:
            source_channel = SourceChannelInfo(
                source_id=source.id,
                youtube_channel_id=channel_id
            )
            channel_monitor.database.insert_source_channel(source_channel)
        
        # Run the monitor
        jobs = await channel_monitor.run(test_data["user"].id)
        
        # Verify jobs were created
        assert jobs, "No jobs were created"
        assert all(isinstance(job, GenerationJob) for job in jobs)
        
        # Find the job for our specific source
        source_jobs = [job for job in jobs if job.source_id == source.id]
        assert len(source_jobs) > 0, f"No jobs found for source {source.id}"
        
        for job in source_jobs:
            assert job.user_id == test_data["user"].id
            assert job.source_id == source.id
            assert job.status == JobStatus.QUEUED
        
        # Verify videos were stored
        source_videos = channel_monitor.database.get_source_videos_by_source(source.id)
        assert source_videos, "No videos were stored for the source"
