import pytest
from datetime import datetime, timezone
import uuid
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

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
    fetcher = YouTubeRSSFetcher()
    yield fetcher
    await fetcher.close()

@pytest.fixture(scope="session")
async def youtube_api(database, rss_fetcher):
    """Create YouTubeAPI instance for the session."""
    api = YouTubeAPI(database=database)
    api.rss_fetcher = rss_fetcher
    return api

@pytest.fixture(scope="session")
async def channel_monitor(database, youtube_api):
    """Create ChannelMonitorAgent instance for the session."""
    return ChannelMonitorAgent(database=database, youtube_api=youtube_api)

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

    @pytest.mark.integration
    async def test_run_with_channel_collection(self, channel_monitor, test_data, setup_test_channels):
        """Test monitoring a channel collection with real channels."""
        test_channel_ids = setup_test_channels
        
        # Create a new channel collection source for the test user
        source = SourceInfo(
            id=uuid.uuid4(),
            user_id=test_data["user"].id,
            source_type=SourceType.CHANNEL_COLLECTION,
            name="Test Channel Collection",
            created_at=datetime.now(timezone.utc)
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
        
        for job in jobs:
            assert job.user_id == test_data["user"].id
            assert job.source_id == source.id
            assert job.status == JobStatus.QUEUED
        
        # Verify videos were stored
        source_videos = channel_monitor.database.get_source_videos_by_source(source.id)
        assert source_videos, "No videos were stored for the source"

    @pytest.mark.integration
    async def test_run_with_playlist(self, channel_monitor, test_data, test_playlist_ids):
        """Test monitoring a playlist with real playlist."""
        # First clean up any existing sources for this user
        try:
            existing_sources = channel_monitor.database.get_sources_by_user(test_data["user"].id)
            print(f">>>>>>> Existing sources: {len(existing_sources)}")
            # Clean up each source and its related data
            for existing_source in existing_sources:
                channel_monitor.database.client.table('podcasts')\
                    .delete()\
                    .eq('source_id', str(existing_source.id))\
                    .execute()
                channel_monitor.database.client.table('source_videos')\
                    .delete()\
                    .eq('source_id', str(existing_source.id))\
                    .execute()
                channel_monitor.database.client.table('source_channels')\
                    .delete()\
                    .eq('source_id', str(existing_source.id))\
                    .execute()
                channel_monitor.database.client.table('sources')\
                    .delete()\
                    .eq('id', str(existing_source.id))\
                    .execute()
        except Exception as e:
            print(f"Error cleaning up existing data: {str(e)}")
        
        # Create a new playlist source
        source = SourceInfo(
            id=uuid.uuid4(),
            user_id=test_data["user"].id,
            source_type=SourceType.PLAYLIST,
            name="Test Playlist Source",
            youtube_playlist_id=test_playlist_ids[0],
            created_at=datetime.now(timezone.utc)
        )
        
        try:
            # Insert the new source
            channel_monitor.database.insert_source(source)
            
            # Run the monitor
            jobs = await channel_monitor.run(test_data["user"].id)
            
            # Verify results
            assert jobs, "No jobs were created"
            assert len(jobs) == 1, f"Expected 1 job, found {len(jobs)}"
            assert jobs[0].user_id == test_data["user"].id
            assert jobs[0].source_id == source.id
            assert jobs[0].status == JobStatus.QUEUED
            
            # Verify videos were stored
            source_videos = channel_monitor.database.get_source_videos_by_source(source.id)
            assert source_videos, "No videos were stored for the source"
            
        finally:
            # Clean up test data
            try:
                channel_monitor.database.client.table('source_videos')\
                    .delete()\
                    .eq('source_id', str(source.id))\
                    .execute()
                channel_monitor.database.client.table('sources')\
                    .delete()\
                    .eq('id', str(source.id))\
                    .execute()
            except Exception as e:
                print(f"Error cleaning up test data: {str(e)}")

    @pytest.mark.integration
    async def test_duplicate_video_handling(self, channel_monitor, test_data, setup_test_channels):
        """Test handling of duplicate videos with real data."""
        test_channel_ids = setup_test_channels
        
        test_data = test_data
        
        # Create a test source with one channel
        source = SourceInfo(
            id=uuid.uuid4(),
            user_id=test_data["user"].id,
            source_type=SourceType.CHANNEL_COLLECTION,
            name="Test Duplicate Channel",
            created_at=datetime.now(timezone.utc)
        )
        channel_monitor.database.insert_source(source)
        
        # Add first test channel
        source_channel = SourceChannelInfo(
            source_id=source.id,
            youtube_channel_id=test_channel_ids[0]
        )
        channel_monitor.database.insert_source_channel(source_channel)
        
        # First run to populate videos
        await channel_monitor.run(test_data["user"].id)
        
        # Get initial video count
        initial_videos = channel_monitor.database.get_source_videos_by_source(source.id)
        initial_count = len(initial_videos)
        
        # Second run should handle duplicates
        jobs = await channel_monitor.run(test_data["user"].id)
        assert jobs, "No jobs were created on second run"
        
        # Verify no duplicate videos in database
        final_videos = channel_monitor.database.get_source_videos_by_source(source.id)
        assert len(final_videos) == initial_count, "Duplicate videos were stored"

    @pytest.mark.integration
    async def test_nonexistent_user(self, channel_monitor):
        """Test running monitor for nonexistent user."""
        # Test with nonexistent user ID
        jobs = await channel_monitor.run("nonexistent_user_id")
        assert jobs == [], "Expected empty list for nonexistent user"
        
        # Test with invalid user ID format
        jobs = await channel_monitor.run("")
        assert jobs == [], "Expected empty list for invalid user ID"
        
        # Test with None user ID
        jobs = await channel_monitor.run(None)  # type: ignore
        assert jobs == [], "Expected empty list for None user ID"

    @pytest.mark.integration
    async def test_empty_source(self, channel_monitor, test_data):
        """Test monitoring an empty channel collection."""
        # First clean up any existing sources for this user
        try:
            existing_sources = channel_monitor.database.get_sources_by_user(test_data["user"].id)
            for existing_source in existing_sources:
                # Clean up related data
                channel_monitor.database.client.table('podcasts')\
                    .delete()\
                    .eq('source_id', str(existing_source.id))\
                    .execute()
                channel_monitor.database.client.table('source_videos')\
                    .delete()\
                    .eq('source_id', str(existing_source.id))\
                    .execute()
                channel_monitor.database.client.table('source_channels')\
                    .delete()\
                    .eq('source_id', str(existing_source.id))\
                    .execute()
                channel_monitor.database.client.table('sources')\
                    .delete()\
                    .eq('id', str(existing_source.id))\
                    .execute()
        except Exception as e:
            print(f"Error cleaning up existing data: {str(e)}")

        # Create empty source
        source = SourceInfo(
            id=uuid.uuid4(),
            user_id=test_data["user"].id,
            source_type=SourceType.CHANNEL_COLLECTION,
            name="Empty Collection",
            created_at=datetime.now(timezone.utc)
        )
        
        try:
            # Insert the source
            channel_monitor.database.insert_source(source)
            
            # Verify no channels are linked
            source_channels = channel_monitor.database.get_source_channels(source.id)
            assert not source_channels, "Source should have no channels"

            # Run the monitor
            jobs = await channel_monitor.run(test_data["user"].id)
            assert not jobs, "Jobs were created for empty source"
            
        finally:
            # Clean up test data
            try:
                channel_monitor.database.client.table('sources')\
                    .delete()\
                    .eq('id', str(source.id))\
                    .execute()
            except Exception as e:
                print(f"Error cleaning up test data: {str(e)}")

    @pytest.mark.integration
    async def test_progress_tracking(self, channel_monitor, test_data, setup_test_channels):
        """Test progress tracking with real processing."""
        test_channel_ids = setup_test_channels
        
        test_data = test_data
        
        # Create source with multiple channels
        source = SourceInfo(
            id=uuid.uuid4(),
            user_id=test_data["user"].id,
            source_type=SourceType.CHANNEL_COLLECTION,
            name="Progress Test Collection",
            created_at=datetime.now(timezone.utc)
        )
        channel_monitor.database.insert_source(source)
        
        # Add all test channels
        for channel_id in test_channel_ids:
            source_channel = SourceChannelInfo(
                source_id=source.id,
                youtube_channel_id=channel_id
            )
            channel_monitor.database.insert_source_channel(source_channel)
        
        # Run monitor
        await channel_monitor.run(test_data["user"].id)
        
        # Verify progress was tracked
        progress = channel_monitor._progress[str(source.id)]
        assert progress["total"] == len(test_channel_ids)
        assert progress["processed"] == progress["total"] 