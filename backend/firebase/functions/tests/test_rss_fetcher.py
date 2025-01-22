import pytest
import asyncio
from datetime import datetime, timezone
from utils.rss_fetcher import YouTubeRSSFetcher
from models.video_metadata import VideoMetadata
import os
from dotenv import load_dotenv

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

@pytest.fixture(scope="module")
async def rss_fetcher():
    """Create a YouTubeRSSFetcher instance for testing."""
    fetcher = YouTubeRSSFetcher()
    yield fetcher
    await fetcher.close()  # Cleanup after tests

@pytest.mark.asyncio
async def test_fetch_channel_feed():
    """Test fetching RSS feed content from a channel."""
    fetcher = YouTubeRSSFetcher()
    
    for channel_id in TEST_CHANNEL_IDS:
        feed_content = await fetcher.fetch_feed(
            YouTubeRSSFetcher.CHANNEL_FEED_URL.format(channel_id)
        )
        
        assert feed_content is not None
        assert isinstance(feed_content, str)
        assert len(feed_content) > 0
        assert "<?xml" in feed_content
        assert "<feed" in feed_content
        
    await fetcher.close()

@pytest.mark.asyncio
async def test_fetch_playlist_feed():
    """Test fetching RSS feed content from a playlist."""
    fetcher = YouTubeRSSFetcher()
    
    for playlist_id in TEST_PLAYLIST_IDS:
        feed_content = await fetcher.fetch_feed(
            YouTubeRSSFetcher.PLAYLIST_FEED_URL.format(playlist_id)
        )
        
        assert feed_content is not None
        assert isinstance(feed_content, str)
        assert len(feed_content) > 0
        assert "<?xml" in feed_content
        assert "<feed" in feed_content
        
    await fetcher.close()

@pytest.mark.asyncio
async def test_fetch_channel_videos():
    """Test fetching and parsing videos from a channel."""
    fetcher = YouTubeRSSFetcher()
    
    for channel_id in TEST_CHANNEL_IDS:
        videos = await fetcher.fetch_channel_videos(channel_id)
        
        assert isinstance(videos, list)
        assert len(videos) > 0
        
        for video in videos:
            assert isinstance(video, VideoMetadata)
            assert video.youtube_video_id is not None
            assert video.title is not None
            assert video.channel_id == channel_id
            assert video.url is not None
            assert isinstance(video.uploaded_at, datetime)
            assert video.created_at is not None
            
    await fetcher.close()

@pytest.mark.asyncio
async def test_fetch_playlist_videos():
    """Test fetching and parsing videos from a playlist."""
    fetcher = YouTubeRSSFetcher()
    
    for playlist_id in TEST_PLAYLIST_IDS:
        videos = await fetcher.fetch_playlist_videos(playlist_id)
        
        assert isinstance(videos, list)
        assert len(videos) > 0
        
        for video in videos:
            assert isinstance(video, VideoMetadata)
            assert video.youtube_video_id is not None
            assert video.title is not None
            assert video.channel_id is not None
            assert video.url is not None
            assert isinstance(video.uploaded_at, datetime)
            assert video.created_at is not None
            
    await fetcher.close()

@pytest.mark.asyncio
async def test_max_videos_limit():
    """Test that max_videos parameter correctly limits the number of videos returned."""
    fetcher = YouTubeRSSFetcher()
    max_videos = 5
    
    # Test with channels
    for channel_id in TEST_CHANNEL_IDS:
        videos = await fetcher.fetch_channel_videos(channel_id, max_videos=max_videos)
        assert len(videos) <= max_videos
        
    # Test with playlists
    for playlist_id in TEST_PLAYLIST_IDS:
        videos = await fetcher.fetch_playlist_videos(playlist_id, max_videos=max_videos)
        assert len(videos) <= max_videos
        
    await fetcher.close()

@pytest.mark.asyncio
async def test_video_metadata_consistency():
    """Test that video metadata is consistent across multiple fetches."""
    fetcher = YouTubeRSSFetcher()
    
    # Test with first channel
    channel_id = TEST_CHANNEL_IDS[0]
    
    # Fetch videos twice
    videos_first = await fetcher.fetch_channel_videos(channel_id, max_videos=5)
    videos_second = await fetcher.fetch_channel_videos(channel_id, max_videos=5)
    
    # Compare metadata for the same videos
    for v1, v2 in zip(videos_first, videos_second):
        assert v1.youtube_video_id == v2.youtube_video_id
        assert v1.title == v2.title
        assert v1.channel_id == v2.channel_id
        assert v1.url == v2.url
        assert v1.uploaded_at == v2.uploaded_at
        
    await fetcher.close()

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling with invalid channel and playlist IDs."""
    fetcher = YouTubeRSSFetcher()
    
    # Test with invalid channel ID
    invalid_channel_videos = await fetcher.fetch_channel_videos("invalid_channel_id")
    assert invalid_channel_videos == []
    
    # Test with invalid playlist ID
    invalid_playlist_videos = await fetcher.fetch_playlist_videos("invalid_playlist_id")
    assert invalid_playlist_videos == []
    
    await fetcher.close()

@pytest.mark.asyncio
async def test_session_management():
    """Test proper session management."""
    fetcher = YouTubeRSSFetcher()
    
    # Test session creation
    assert fetcher.session is None
    await fetcher._ensure_session()
    assert fetcher.session is not None
    assert not fetcher.session.closed
    
    # Test session reuse
    original_session = fetcher.session
    await fetcher._ensure_session()
    assert fetcher.session is original_session
    
    # Test session closure
    await fetcher.close()
    assert fetcher.session.closed
    
    # Test new session creation after closure
    await fetcher._ensure_session()
    assert fetcher.session is not None
    assert not fetcher.session.closed
    
    await fetcher.close()

@pytest.mark.asyncio
async def test_concurrent_fetches():
    """Test concurrent fetching of multiple channels and playlists."""
    fetcher = YouTubeRSSFetcher()
    
    # Create tasks for all channels and playlists
    tasks = []
    for channel_id in TEST_CHANNEL_IDS:
        tasks.append(fetcher.fetch_channel_videos(channel_id))
    for playlist_id in TEST_PLAYLIST_IDS:
        tasks.append(fetcher.fetch_playlist_videos(playlist_id))
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    # Verify results
    assert len(results) == len(TEST_CHANNEL_IDS) + len(TEST_PLAYLIST_IDS)
    for videos in results:
        assert isinstance(videos, list)
        assert len(videos) > 0
        for video in videos:
            assert isinstance(video, VideoMetadata)
            
    await fetcher.close()