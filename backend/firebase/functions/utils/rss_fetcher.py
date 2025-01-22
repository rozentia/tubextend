import asyncio
import aiohttp
import feedparser
from datetime import datetime
import pytz
from typing import List, Optional
from models.video_metadata import VideoMetadata
from utils.logger import setup_logger
from models.channel_info import ChannelInfo

logger = setup_logger(__name__)

class YouTubeRSSFetcher:
    """Fetches YouTube channel and playlist updates using RSS feeds instead of API calls."""
    
    CHANNEL_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
    PLAYLIST_FEED_URL = "https://www.youtube.com/feeds/videos.xml?playlist_id={}"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize with optional existing session."""
        self.session = session
        self._session_owner = session is None  # Track if we created the session
    
    async def _ensure_session(self):
        """Ensures an aiohttp session exists with proper timeout configuration."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)  # 10 seconds total timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
            self._session_owner = True
    
    async def close(self):
        """Closes the aiohttp session if we own it."""
        if self._session_owner and self.session and not self.session.closed:
            await self.session.close()
    
    async def fetch_feed(self, url: str) -> Optional[str]:
        """Fetches RSS feed content from URL."""
        await self._ensure_session()
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                logger.error(f"Failed to fetch RSS feed. Status: {response.status}")
                return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching RSS feed from {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}")
            return None
    
    def parse_feed_entry(self, entry) -> Optional[VideoMetadata]:
        """Parses a feed entry into VideoMetadata."""
        try:
            # Extract video ID from yt:videoId
            video_id = entry.get('yt_videoid')
            if not video_id:
                return None
            
            # Extract channel ID from yt:channelId
            channel_id = entry.get('yt_channelid')
            if not channel_id:
                return None
            
            # Parse the published date
            published = datetime.fromtimestamp(
                datetime.strptime(entry.published, "%Y-%m-%dT%H:%M:%S%z").timestamp(),
                tz=pytz.UTC
            )
            
            return VideoMetadata(
                youtube_video_id=video_id,
                title=entry.title,
                description=entry.get('summary', ''),
                url=f"https://www.youtube.com/watch?v={video_id}",
                channel_id=channel_id,
                uploaded_at=published,
                created_at=datetime.now(pytz.UTC)
            )
        except Exception as e:
            logger.error(f"Error parsing feed entry: {e}")
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
    
    async def fetch_channel_info(self, channel_id: str) -> Optional[ChannelInfo]:
        """Fetches channel information from YouTube RSS feed."""
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        
        try:
            feed_content = await self.fetch_feed(feed_url)
            if not feed_content:
                return None
            
            feed = feedparser.parse(feed_content).feed
            
            if feed.author and feed.title:
                return ChannelInfo(
                    youtube_channel_id=channel_id,
                    title=feed.title.replace("- YouTube", "").strip(),
                    description=feed.author,
                    channel_url=f"https://www.youtube.com/channel/{channel_id}"
                )
            return None
                
        except Exception as e:
            logger.error(f"Error fetching RSS feed for channel: {channel_id} - {e}")
            return None 