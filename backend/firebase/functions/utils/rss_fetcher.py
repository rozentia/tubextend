import asyncio
import aiohttp
import feedparser
from datetime import datetime
import pytz
from typing import List, Optional
from models.video_metadata import VideoMetadata
from utils.logger import setup_logger
from models.channel_info import ChannelInfo
from contextlib import asynccontextmanager

logger = setup_logger(__name__)

class YouTubeRSSFetcher:
    """Fetches YouTube channel and playlist updates using RSS feeds."""
    
    CHANNEL_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
    PLAYLIST_FEED_URL = "https://www.youtube.com/feeds/videos.xml?playlist_id={}"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session
        self._session_owner = session is None
        self._session_lock = asyncio.Lock()
        self._context_depth = 0  # Track nested context depth
    
    @asynccontextmanager
    async def _get_session(self):
        """Get or create a session with proper timeout configuration."""
        async with self._session_lock:
            if not self.session or self.session.closed:
                # Create new session only if we don't have one or it's closed
                timeout = aiohttp.ClientTimeout(total=10)
                self.session = aiohttp.ClientSession(timeout=timeout)
                self._session_owner = True
            self._context_depth += 1
        
        try:
            yield self.session
        finally:
            async with self._session_lock:
                self._context_depth -= 1
                if self._context_depth == 0 and self._session_owner and self.session and not self.session.closed:
                    await self.session.close()
                    self.session = None
    
    async def close(self):
        """Close the session if we own it."""
        async with self._session_lock:
            if self._session_owner and self.session and not self.session.closed:
                await self.session.close()
                self.session = None
                self._context_depth = 0
    
    async def fetch_feed(self, url: str) -> Optional[str]:
        """Fetches RSS feed content from URL."""
        try:
            async with self._get_session() as session:
                async with asyncio.timeout(10):  # Modern asyncio timeout
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.text()
                        logger.error(f"Failed to fetch RSS feed. Status: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching RSS feed from {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {str(e)}")
            return None

    async def fetch_channel_videos(self, channel_id: str, max_videos: int = 15) -> List[VideoMetadata]:
        """Fetches latest videos from a channel using RSS feed."""
        feed_url = self.CHANNEL_FEED_URL.format(channel_id)
        feed_content = await self.fetch_feed(feed_url)
        
        if not feed_content:
            return []
        
        feed = feedparser.parse(feed_content)
        videos = []
        
        for entry in feed.entries[:max_videos]:
            video = self.parse_feed_entry(entry)
            if video:
                video.channel_id = channel_id
                videos.append(video)
        
        return videos

    async def fetch_playlist_videos(self, playlist_id: str, max_videos: int = 15) -> List[VideoMetadata]:
        """Fetches latest videos from a playlist using RSS feed."""
        feed_url = self.PLAYLIST_FEED_URL.format(playlist_id)
        feed_content = await self.fetch_feed(feed_url)
        
        if not feed_content:
            return []
        
        feed = feedparser.parse(feed_content)
        videos = []
        
        for entry in feed.entries[:max_videos]:
            video = self.parse_feed_entry(entry)
            if video:
                videos.append(video)
        
        return videos

    def parse_feed_entry(self, entry) -> Optional[VideoMetadata]:
        """Parses a feed entry into VideoMetadata."""
        try:
            video_id = entry.get('yt_videoid')
            if not video_id:
                return None
            
            channel_id = entry.get('yt_channelid')
            if not channel_id:
                return None
                
            published = entry.get('published')
            if published:
                uploaded_at = datetime.strptime(published, "%Y-%m-%dT%H:%M:%S%z")
            else:
                uploaded_at = datetime.now(pytz.UTC)
            
            return VideoMetadata(
                youtube_video_id=video_id,
                title=entry.get('title'),
                channel_id=channel_id,
                url=entry.get('link'),
                uploaded_at=uploaded_at,
                created_at=datetime.now(pytz.UTC)
            )
        except Exception as e:
            logger.error(f"Error parsing feed entry: {e}")
            return None

    async def fetch_channel_info(self, channel_id: str) -> Optional[ChannelInfo]:
        """Fetches channel information from RSS feed."""
        feed_url = self.CHANNEL_FEED_URL.format(channel_id)
        
        try:
            feed_content = await self.fetch_feed(feed_url)
            if not feed_content:
                return None
            
            feed = feedparser.parse(feed_content)
            
            if not feed.feed:
                return None
                
            return ChannelInfo(
                youtube_channel_id=channel_id,
                title=feed.feed.get('title', '').replace("- YouTube", "").strip(),
                description=feed.feed.get('subtitle', ''),
                channel_url=f"https://www.youtube.com/channel/{channel_id}"
            )
                
        except Exception as e:
            logger.error(f"Error fetching channel info: {e}")
            return None 