import pytest
import asyncio
from datetime import datetime, timezone
from utils.rss_fetcher import YouTubeRSSFetcher
from models.video_metadata import VideoMetadata
import os
from dotenv import load_dotenv
import aiohttp

# Load test environment variables
load_dotenv('test.env')

# Get test channel and playlist IDs
TEST_CHANNEL_IDS = [
    os.getenv('TEST_CHANNEL_ID_1'),
    os.getenv('TEST_CHANNEL_ID_2'),
    os.getenv('TEST_CHANNEL_ID_3')
]

TEST_PLAYLIST_IDS = [
    os.getenv('TEST_PLAYLIST_ID_1'),
    os.getenv('TEST_PLAYLIST_ID_2'),
    os.getenv('TEST_PLAYLIST_ID_3')
]

# Mark all tests in this file to use session-scoped event loop
pytestmark = [
    pytest.mark.asyncio(scope="session"),
    pytest.mark.integration
]

@pytest.fixture
async def rss_fetcher():
    """Create a fresh YouTubeRSSFetcher instance for each test."""
    fetcher = YouTubeRSSFetcher()
    yield fetcher
    await fetcher.close()

@pytest.mark.asyncio
async def test_fetch_channel_feed(rss_fetcher):
    """Test fetching RSS feed content from a channel."""
    channel_id = os.getenv('TEST_CHANNEL_ID_1')
    assert channel_id, "TEST_CHANNEL_ID_1 environment variable must be set"
    
    feed_content = await rss_fetcher.fetch_feed(
        YouTubeRSSFetcher.CHANNEL_FEED_URL.format(channel_id)
    )
    
    assert feed_content is not None
    assert isinstance(feed_content, str)
    assert len(feed_content) > 0
    assert "<?xml" in feed_content
    assert "<feed" in feed_content

@pytest.mark.asyncio
async def test_fetch_playlist_feed(rss_fetcher):
    """Test fetching RSS feed content from a playlist."""
    for playlist_id in TEST_PLAYLIST_IDS:
        assert playlist_id, f"{playlist_id} environment variable must be set"
        
        feed_content = await rss_fetcher.fetch_feed(
            YouTubeRSSFetcher.PLAYLIST_FEED_URL.format(playlist_id)
        )
        
        assert feed_content is not None
        assert isinstance(feed_content, str)
        assert len(feed_content) > 0
        assert "<?xml" in feed_content
        assert "<feed" in feed_content
        
    await rss_fetcher.close()

@pytest.mark.asyncio
async def test_fetch_channel_videos(rss_fetcher):
    """Test fetching and parsing videos from a channel."""
    for channel_id in TEST_CHANNEL_IDS:
        assert channel_id, f"{channel_id} environment variable must be set"
        
        videos = await rss_fetcher.fetch_channel_videos(channel_id)
        
        assert isinstance(videos, list)
        assert len(videos) > 0
        
        for video in videos:
            assert isinstance(video, VideoMetadata)
            assert video.youtube_video_id is not None
            assert video.title is not None
            assert video.channel_id == channel_id
            assert video.url is not None
            assert isinstance(video.uploaded_at, datetime)
            assert video.uploaded_at.tzinfo == timezone.utc
            assert video.created_at is not None
            
    await rss_fetcher.close()

@pytest.mark.asyncio
async def test_fetch_playlist_videos(rss_fetcher):
    """Test fetching and parsing videos from a playlist."""
    for playlist_id in TEST_PLAYLIST_IDS:
        assert playlist_id, f"{playlist_id} environment variable must be set"
        
        videos = await rss_fetcher.fetch_playlist_videos(playlist_id)
        
        assert isinstance(videos, list)
        assert len(videos) > 0
        
        for video in videos:
            assert isinstance(video, VideoMetadata)
            assert video.youtube_video_id is not None
            assert video.title is not None
            assert video.channel_id is not None
            assert video.url is not None
            assert isinstance(video.uploaded_at, datetime)
            assert video.uploaded_at.tzinfo == timezone.utc
            assert video.created_at is not None
            
    await rss_fetcher.close()

@pytest.mark.asyncio
async def test_max_videos_limit(rss_fetcher):
    """Test that max_videos parameter correctly limits the number of videos returned."""
    max_videos = 5
    
    # Test with channels
    for channel_id in TEST_CHANNEL_IDS:
        assert channel_id, f"{channel_id} environment variable must be set"
        
        videos = await rss_fetcher.fetch_channel_videos(channel_id, max_videos=max_videos)
        assert len(videos) <= max_videos
        
    # Test with playlists
    for playlist_id in TEST_PLAYLIST_IDS:
        assert playlist_id, f"{playlist_id} environment variable must be set"
        
        videos = await rss_fetcher.fetch_playlist_videos(playlist_id, max_videos=max_videos)
        assert len(videos) <= max_videos
        
    await rss_fetcher.close()

@pytest.mark.asyncio
async def test_video_metadata_consistency(rss_fetcher):
    """Test that video metadata is consistent across multiple fetches."""
    # Test with first channel
    channel_id = TEST_CHANNEL_IDS[0]
    assert channel_id, f"{channel_id} environment variable must be set"
    
    # Fetch videos twice
    videos_first = await rss_fetcher.fetch_channel_videos(channel_id, max_videos=5)
    videos_second = await rss_fetcher.fetch_channel_videos(channel_id, max_videos=5)
    
    # Compare metadata for the same videos
    for v1, v2 in zip(videos_first, videos_second):
        assert v1.youtube_video_id == v2.youtube_video_id
        assert v1.title == v2.title
        assert v1.channel_id == v2.channel_id
        assert v1.url == v2.url
        assert v1.uploaded_at == v2.uploaded_at
        
    await rss_fetcher.close()

@pytest.mark.asyncio
async def test_error_handling(rss_fetcher):
    """Test error handling with invalid channel and playlist IDs."""
    # Test with invalid channel ID
    invalid_channel_videos = await rss_fetcher.fetch_channel_videos("invalid_channel_id")
    assert invalid_channel_videos == []
    
    # Test with invalid playlist ID
    invalid_playlist_videos = await rss_fetcher.fetch_playlist_videos("invalid_playlist_id")
    assert invalid_playlist_videos == []
    
    await rss_fetcher.close()

@pytest.mark.asyncio
async def test_session_management(rss_fetcher):
    """Test proper session management."""
    # Initial state - no session
    assert rss_fetcher.session is None
    
    # First context - creates a new session
    async with rss_fetcher._get_session() as session1:
        assert session1 is not None
        assert not session1.closed
        first_session = session1
        
        # Nested context - should reuse the same session
        async with rss_fetcher._get_session() as session2:
            assert session2 is session1
            assert not session2.closed
    
    # After context exit, owned sessions should be closed and cleared
    assert rss_fetcher.session is None
    assert first_session.closed
    
    # New context should create a new session
    async with rss_fetcher._get_session() as new_session:
        assert new_session is not None
        assert not new_session.closed
        assert new_session is not first_session

@pytest.mark.asyncio
async def test_concurrent_fetches(rss_fetcher):
    """Test concurrent fetching of multiple channels and playlists."""
    # Create tasks for all channels and playlists
    tasks = []
    for channel_id in TEST_CHANNEL_IDS:
        tasks.append(rss_fetcher.fetch_channel_videos(channel_id))
    for playlist_id in TEST_PLAYLIST_IDS:
        tasks.append(rss_fetcher.fetch_playlist_videos(playlist_id))
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    # Verify results
    assert len(results) == len(TEST_CHANNEL_IDS) + len(TEST_PLAYLIST_IDS)
    for videos in results:
        assert isinstance(videos, list)
        assert len(videos) > 0
        for video in videos:
            assert isinstance(video, VideoMetadata)
            
    await rss_fetcher.close()