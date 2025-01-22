# utils/api_wrappers.py
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import os
import googleapiclient.discovery
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import aiohttp

from utils.database import Database
from utils.logger import setup_logger
from models.video_metadata import VideoMetadata
from models.channel_info import ChannelInfo
from utils.config import config
from utils.rss_fetcher import YouTubeRSSFetcher

logger = setup_logger(__name__)

class YouTubeAPI:
    def __init__(self, database: Database, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize YouTubeAPI with API key for public data access.
        
        Args:
            database (Database): Database instance for data operations
            session (Optional[aiohttp.ClientSession]): Optional aiohttp session for RSS fetcher
        """
        self.database = database
        self.api_key = config.youtube_api_key
        self._youtube = None
        self._rss_fetcher = YouTubeRSSFetcher(session=session)

    async def _get_youtube_client(self):
        """
        Get YouTube client using API key.
        
        Returns:
            googleapiclient.discovery.Resource: YouTube API client
        """
        if not self.api_key:
            raise ValueError("YouTube API key must be provided")
        return googleapiclient.discovery.build("youtube", "v3", developerKey=self.api_key)

    async def fetch_channel_videos(self, channel_id: str) -> List[VideoMetadata]:
        """
        Fetches the latest videos from a given YouTube channel.
        Limited to 50 most recent videos to optimize quota usage.
        Falls back to RSS feed if API quota is exceeded.

        Args:
            channel_id (str): The YouTube channel ID.

        Returns:
            List[VideoMetadata]: A list of VideoMetadata objects for the latest videos.
        """
        logger.info(f"Fetching videos for channel ID: {channel_id}")
        try:
            youtube = await self._get_youtube_client()
            request = youtube.search().list(
                part="snippet",
                channelId=channel_id,
                order="date",
                type="video",
                maxResults=50  # Limit to 50 most recent videos
            )
            
            try:
                response = await asyncio.to_thread(request.execute)
            except HttpError as e:
                if e.resp.status == 403:  # Quota exceeded
                    logger.warning(f"YouTube API quota exceeded: {e}. Falling back to RSS feed.")
                    return await self._rss_fetcher.fetch_channel_videos(channel_id)
                raise

            videos = []
            for item in response.get("items", []):
                video_id = item["id"].get("videoId")
                if video_id:
                    videos.append(
                        VideoMetadata(
                            youtube_video_id=video_id,
                            title=item["snippet"]["title"],
                            description=item["snippet"]["description"],
                            channel_id=channel_id,
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            uploaded_at=datetime.fromisoformat(item["snippet"]["publishedAt"][:-1]),
                        )
                    )

            logger.info(f"Found {len(videos)} videos for channel ID: {channel_id}")
            return videos

        except HttpError as e:
            logger.error(f"An error occurred while fetching videos: {e}")
            # Try RSS fallback for any YouTube API error
            try:
                logger.info("Attempting RSS feed fallback...")
                return await self._rss_fetcher.fetch_channel_videos(channel_id)
            except Exception as rss_error:
                logger.error(f"RSS fallback also failed: {rss_error}")
                return []

    async def fetch_playlist_videos(self, playlist_id: str) -> List[VideoMetadata]:
        """
        Fetches videos from a given YouTube playlist.
        Limited to 50 most recent videos to optimize quota usage.
        Falls back to RSS feed if API quota is exceeded.

        Args:
            playlist_id (str): The YouTube playlist ID.

        Returns:
            List[VideoMetadata]: A list of VideoMetadata objects for the playlist's videos.
        """
        logger.info(f"Fetching videos for playlist ID: {playlist_id}")
        try:
            youtube = await self._get_youtube_client()
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50  # Limit to 50 most recent videos
            )
            
            try:
                response = await asyncio.to_thread(request.execute)
            except HttpError as e:
                if e.resp.status == 403:  # Quota exceeded
                    logger.warning(f"YouTube API quota exceeded: {e}. Falling back to RSS feed.")
                    return await self._rss_fetcher.fetch_playlist_videos(playlist_id)
                raise

            videos = []
            for item in response.get("items", []):
                video_id = item["snippet"]["resourceId"].get("videoId")
                if video_id:
                    videos.append(
                        VideoMetadata(
                            youtube_video_id=video_id,
                            title=item["snippet"]["title"],
                            description=item["snippet"]["description"],
                            channel_id=item["snippet"]["channelId"],
                            url=f"https://www.youtube.com/watch?v={video_id}",
                            uploaded_at=datetime.fromisoformat(item["snippet"]["publishedAt"][:-1]),
                        )
                    )

            logger.info(f"Found {len(videos)} videos for playlist ID: {playlist_id}")
            return videos
            
        except HttpError as e:
            logger.error(f"An error occurred while fetching videos from playlist ID {playlist_id}: {e}")
            # Try RSS fallback for any YouTube API error
            try:
                logger.info("Attempting RSS feed fallback...")
                return await self._rss_fetcher.fetch_playlist_videos(playlist_id)
            except Exception as rss_error:
                logger.error(f"RSS fallback also failed: {rss_error}")
                return []

    async def fetch_channel_info(self, channel_id: str) -> Optional[ChannelInfo]:
        """
        Fetches channel information by its youtube id

        Args:
            channel_id (str): The YouTube channel ID.

        Returns:
            ChannelInfo: A channel info record or none if no channel is found.
        """
        logger.info(f"Fetching channel info for channel ID: {channel_id}")
        try:
            youtube = await self._get_youtube_client()
            request = youtube.channels().list(
                part="snippet",
                id=channel_id
            )
            response = await asyncio.to_thread(request.execute)
            items = response.get("items", [])
            if items:
                item = items[0]
                channel_info = ChannelInfo(
                    youtube_channel_id=channel_id,
                    title=item["snippet"]["title"],
                    description=item["snippet"]["description"],
                    channel_url=f"https://www.youtube.com/channel/{channel_id}"
                )
                logger.info(f"Fetched channel info for channel ID: {channel_id}: {channel_info}")
                return channel_info
            else:
                logger.warning(f"Could not fetch channel info for channel ID: {channel_id}, channel was not found.")
                return None

        except HttpError as e:
            logger.error(f"An error occurred while fetching channel info for channel ID {channel_id}: {e}")
            return None

    async def close(self):
        """Close resources."""
        if self._rss_fetcher:
            await self._rss_fetcher.close()