import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timezone
import uuid
import asyncio

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

# Test Data Fixtures
@pytest.fixture
def mock_database():
    return Mock(spec=Database)

@pytest.fixture
def mock_youtube_api():
    return Mock(spec=YouTubeAPI)

@pytest.fixture
def channel_monitor(mock_database, mock_youtube_api):
    return ChannelMonitorAgent(database=mock_database, youtube_api=mock_youtube_api)

@pytest.fixture
def test_user():
    return UserInfo(
        id="test_user_id",
        email="test@example.com",
        display_name="Test User",
        created_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def test_channel():
    return ChannelInfo(
        youtube_channel_id="test_channel_id",
        title="Test Channel",
        description="Test Channel Description",
        channel_url="https://youtube.com/c/test_channel",
        created_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def test_source():
    return SourceInfo(
        id=uuid.uuid4(),
        user_id="test_user_id",
        source_type=SourceType.CHANNEL_COLLECTION,
        name="Test Source",
        created_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def test_video():
    return VideoMetadata(
        youtube_video_id="test_video_id",
        title="Test Video",
        description="Test Video Description",
        url="https://youtube.com/watch?v=test_video_id",
        channel_id="test_channel_id",
        uploaded_at=datetime.now(timezone.utc)
    )

# Main Functionality Tests
@pytest.mark.asyncio
async def test_run_with_no_user(channel_monitor, mock_database):
    """Test run method when user doesn't exist."""
    mock_database.get_user.return_value = None
    
    result = await channel_monitor.run("nonexistent_user_id")
    
    assert result == []
    mock_database.get_user.assert_called_once_with(user_id="nonexistent_user_id")

@pytest.mark.asyncio
async def test_run_with_no_sources(channel_monitor, mock_database, test_user):
    """Test run method when user has no sources."""
    mock_database.get_user.return_value = test_user
    mock_database.get_sources_by_user.return_value = []
    
    result = await channel_monitor.run(test_user.id)
    
    assert result == []
    mock_database.get_user.assert_called_once_with(user_id=test_user.id)
    mock_database.get_sources_by_user.assert_called_once_with(user_id=test_user.id)

@pytest.mark.asyncio
async def test_run_with_channel_collection(
    channel_monitor, mock_database, mock_youtube_api,
    test_user, test_source, test_channel, test_video
):
    """Test successful processing of a channel collection source."""
    # Setup mocks
    mock_database.get_user.return_value = test_user
    mock_database.get_sources_by_user.return_value = [test_source]
    mock_database.get_source_channels_by_source.return_value = [
        SourceChannelInfo(source_id=test_source.id, youtube_channel_id=test_channel.youtube_channel_id)
    ]
    mock_database.get_channel.return_value = test_channel
    mock_youtube_api.fetch_channel_videos = AsyncMock(return_value=[test_video])
    mock_database.get_video.return_value = None
    mock_database.insert_video.return_value = test_video
    mock_database.insert_generation_job.return_value = GenerationJob(
        id=uuid.uuid4(),
        user_id=test_user.id,
        source_id=test_source.id,
        status=JobStatus.QUEUED,
        created_at=datetime.now(timezone.utc)
    )
    
    # Run test
    result = await channel_monitor.run(test_user.id)
    
    # Verify results
    assert len(result) == 1
    assert isinstance(result[0], GenerationJob)
    assert result[0].user_id == test_user.id
    assert result[0].source_id == test_source.id
    assert result[0].status == JobStatus.QUEUED

@pytest.mark.asyncio
async def test_run_with_playlist(
    channel_monitor, mock_database, mock_youtube_api,
    test_user, test_video
):
    """Test successful processing of a playlist source."""
    # Create playlist source
    playlist_source = SourceInfo(
        id=uuid.uuid4(),
        user_id=test_user.id,
        source_type=SourceType.PLAYLIST,
        name="Test Playlist",
        youtube_playlist_id="test_playlist_id",
        created_at=datetime.now(timezone.utc)
    )
    
    # Setup mocks
    mock_database.get_user.return_value = test_user
    mock_database.get_sources_by_user.return_value = [playlist_source]
    mock_youtube_api.fetch_playlist_videos = AsyncMock(return_value=[test_video])
    mock_database.get_video.return_value = None
    mock_database.insert_video.return_value = test_video
    mock_database.insert_generation_job.return_value = GenerationJob(
        id=uuid.uuid4(),
        user_id=test_user.id,
        source_id=playlist_source.id,
        status=JobStatus.QUEUED,
        created_at=datetime.now(timezone.utc)
    )
    
    # Run test
    result = await channel_monitor.run(test_user.id)
    
    # Verify results
    assert len(result) == 1
    assert isinstance(result[0], GenerationJob)
    assert result[0].user_id == test_user.id
    assert result[0].source_id == playlist_source.id
    assert result[0].status == JobStatus.QUEUED

# Rate Limiting Tests
@pytest.mark.asyncio
async def test_rate_limiting(channel_monitor):
    """Test that rate limiting works correctly."""
    # Set a very low rate limit for testing
    channel_monitor.rate_limit = 2
    channel_monitor._request_count = 0
    
    # First request should go through immediately
    await channel_monitor._check_rate_limit()
    assert channel_monitor._request_count == 1
    
    # Second request should go through
    await channel_monitor._check_rate_limit()
    assert channel_monitor._request_count == 2
    
    # Third request should trigger waiting
    with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
        await channel_monitor._check_rate_limit()
        mock_sleep.assert_called_once()

# Batch Processing Tests
@pytest.mark.asyncio
async def test_batch_processing(
    channel_monitor, mock_database, test_source, test_video
):
    """Test that videos are processed in correct batch sizes."""
    # Create a list of test videos
    test_videos = [
        VideoMetadata(
            youtube_video_id=f"video_{i}",
            title=f"Video {i}",
            channel_id="test_channel",
            created_at=datetime.now(timezone.utc)
        )
        for i in range(120)  # Create more videos than batch size
    ]
    
    # Set a smaller batch size for testing
    channel_monitor.batch_size = 50
    
    # Process videos
    result = await channel_monitor._process_videos_batch(test_videos)
    
    # Verify that database was called with correct batch sizes
    assert mock_database.get_video.call_count <= len(test_videos)
    assert len(result) <= len(test_videos)

# Error Handling Tests
@pytest.mark.asyncio
async def test_quota_exceeded_handling(
    channel_monitor, mock_youtube_api, test_channel
):
    """Test handling of YouTube API quota exceeded error."""
    mock_youtube_api.fetch_channel_videos = AsyncMock(
        side_effect=Exception("quota exceeded")
    )
    
    with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
        result = await channel_monitor._fetch_new_videos_from_channel(
            channel=test_channel,
            user_id="test_user"
        )
        
        assert result == []
        assert mock_sleep.called

@pytest.mark.asyncio
async def test_channel_not_found_handling(
    channel_monitor, mock_database, test_source, test_user
):
    """Test handling of non-existent channel."""
    source_channel = SourceChannelInfo(
        source_id=test_source.id,
        youtube_channel_id="nonexistent_channel"
    )
    
    mock_database.get_source_channels_by_source.return_value = [source_channel]
    mock_database.get_channel.return_value = None
    
    # This should log a warning but not raise an exception
    await channel_monitor._process_channel_collection(
        user=test_user,
        source=test_source,
        jobs=[]
    )
    
    mock_database.get_channel.assert_called_once_with(
        youtube_channel_id="nonexistent_channel"
    )

# Progress Tracking Tests
def test_progress_tracking(channel_monitor):
    """Test that progress tracking works correctly."""
    source_id = str(uuid.uuid4())
    
    # Test initial update
    channel_monitor._update_progress(source_id, total=100)
    assert channel_monitor._progress[source_id]["total"] == 100
    assert channel_monitor._progress[source_id]["processed"] == 0
    
    # Test progress update
    channel_monitor._update_progress(source_id, processed=50)
    assert channel_monitor._progress[source_id]["total"] == 100
    assert channel_monitor._progress[source_id]["processed"] == 50
    
    # Test completion
    channel_monitor._update_progress(source_id, processed=100)
    assert channel_monitor._progress[source_id]["processed"] == 100

# Integration-style Tests
@pytest.mark.asyncio
async def test_full_processing_flow(
    channel_monitor, mock_database, mock_youtube_api,
    test_user, test_source, test_channel, test_video
):
    """Test the full processing flow from channel to job creation."""
    # Setup initial state
    source_channel = SourceChannelInfo(
        source_id=test_source.id,
        youtube_channel_id=test_channel.youtube_channel_id
    )
    
    # Setup mocks
    mock_database.get_user.return_value = test_user
    mock_database.get_sources_by_user.return_value = [test_source]
    mock_database.get_source_channels_by_source.return_value = [source_channel]
    mock_database.get_channel.return_value = test_channel
    mock_youtube_api.fetch_channel_videos = AsyncMock(return_value=[test_video])
    mock_database.get_video.return_value = None
    mock_database.insert_video.return_value = test_video
    mock_database.insert_source_video.return_value = SourceVideoInfo(
        source_id=test_source.id,
        youtube_video_id=test_video.youtube_video_id
    )
    mock_database.insert_generation_job.return_value = GenerationJob(
        id=uuid.uuid4(),
        user_id=test_user.id,
        source_id=test_source.id,
        status=JobStatus.QUEUED,
        created_at=datetime.now(timezone.utc)
    )
    
    # Run the full process
    result = await channel_monitor.run(test_user.id)
    
    # Verify the complete flow
    assert len(result) == 1
    assert isinstance(result[0], GenerationJob)
    assert result[0].user_id == test_user.id
    assert result[0].source_id == test_source.id
    assert result[0].status == JobStatus.QUEUED
    
    # Verify all expected database calls were made
    mock_database.get_user.assert_called_once()
    mock_database.get_sources_by_user.assert_called_once()
    mock_database.get_source_channels_by_source.assert_called_once()
    mock_database.get_channel.assert_called_once()
    mock_database.insert_video.assert_called_once()
    mock_database.insert_generation_job.assert_called_once()
    mock_database.update_source.assert_called_once() 