# utils/api_wrappers.py
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import os
import googleapiclient.discovery
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from utils.database import Database
from utils.logger import setup_logger
from models.video_metadata import VideoMetadata
from models.channel_info import ChannelInfo
from utils.config import config

logger = setup_logger(__name__)

class YouTubeAPI:
    def __init__(self, database: Database):
        """
        Initialize YouTubeAPI with either database (for OAuth) or API key (for public data).
        
        Args:
            database (Database): Database instance for OAuth token management
            api_key (Optional[str]): YouTube API key for public data access
        """
        self.database = database
        self.api_key = config.youtube_api_key
        self.client_id = config.youtube_client_id
        self.client_secret = config.youtube_client_key
        self._youtube = None

    async def _get_youtube_client(self, user_id: Optional[str] = None):
        """
        Get YouTube client using either OAuth credentials or API key.
        
        Args:
            user_id (Optional[str]): User ID for OAuth flow. If None, uses API key.
        
        Returns:
            googleapiclient.discovery.Resource: YouTube API client
        """
        if user_id:
            credentials = await self._get_credentials(user_id)
            return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
        else:
            if not self.api_key:
                raise ValueError("Either user_id or api_key must be provided")
            return googleapiclient.discovery.build("youtube", "v3", developerKey=self.api_key)

    async def _get_credentials(self, user_id: str) -> Credentials:
        """
        Retrieves or refreshes the user's credentials.
        """
        logger.info(f"Getting/Refreshing credentials for user ID: {user_id}")
        user_info = self.database.get_user(user_id=user_id)

        if not user_info or not user_info.refresh_token:
            logger.error(f"No refresh token for user with id {user_id}")
            raise ValueError(f"No refresh token for user with id {user_id}")

        credentials = Credentials.from_authorized_user_info(
            {
                'refresh_token': user_info.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'token_uri': 'https://oauth2.googleapis.com/token',
                'scopes': ["https://www.googleapis.com/auth/youtube.readonly"]
            }
        )

        if not credentials.valid:
            request = Request()
            credentials.refresh(request)
            
            # Update the token in the database
            self.database.update_user_token(
                user_id=user_id,
                refresh_token=credentials.refresh_token,
                expires_at=credentials.expiry
            )

        return credentials

    async def fetch_channel_videos(self, channel_id: str, user_id: Optional[str] = None) -> List[VideoMetadata]:
        """
        Fetches the latest videos from a given YouTube channel.

        Args:
            channel_id (str): The YouTube channel ID.
            user_id (Optional[str]): User ID for OAuth flow. If None, uses API key.

        Returns:
            List[VideoMetadata]: A list of VideoMetadata objects for the latest videos.
        """
        logger.info(f"Fetching videos for channel ID: {channel_id}")
        try:
            youtube = await self._get_youtube_client(user_id)
            videos = []
            next_page_token = None
            
            while True:
                request = youtube.search().list(
                    part="snippet",
                    channelId=channel_id,
                    order="date",
                    type="video",
                    maxResults=50,
                    pageToken=next_page_token
                )
                
                try:
                    response = await asyncio.to_thread(request.execute)
                except HttpError as e:
                    if e.resp.status == 403:  # Quota exceeded
                        logger.error(f"YouTube API quota exceeded: {e}")
                        break
                    raise

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

                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break

            logger.info(f"Found {len(videos)} videos for channel ID: {channel_id}")
            return videos

        except HttpError as e:
            logger.error(f"An error occurred while fetching videos: {e}")
            return []


    async def fetch_playlist_videos(self, playlist_id: str, user_id: Optional[str] = None) -> List[VideoMetadata]:
      """
      Fetches videos from a given YouTube playlist.

      Args:
          playlist_id (str): The YouTube playlist ID.
          user_id (Optional[str]): User ID for OAuth flow. If None, uses API key.

      Returns:
          List[VideoMetadata]: A list of VideoMetadata objects for the playlist's videos.
      """
      logger.info(f"Fetching videos for playlist ID: {playlist_id}")
      try:
        youtube = await self._get_youtube_client(user_id)
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
        )
        response = await asyncio.to_thread(request.execute)
        videos = []

        for item in response.get("items", []):
          video_id = item["snippet"]["resourceId"].get("videoId")
          if video_id:
            videos.append(
                VideoMetadata(
                    youtube_video_id = video_id,
                    title=item["snippet"]["title"],
                    description=item["snippet"]["description"],
                    channel_id = item["snippet"]["channelId"],
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    uploaded_at=datetime.fromisoformat(item["snippet"]["publishedAt"][:-1]),
                  )
              )
        next_page_token = response.get('nextPageToken')

        while next_page_token:
          request = youtube.playlistItems().list(
              part="snippet",
              playlistId=playlist_id,
              maxResults=50,
              pageToken=next_page_token,
          )
          response = await asyncio.to_thread(request.execute)
          for item in response.get("items", []):
              video_id = item["snippet"]["resourceId"].get("videoId")
              if video_id:
                videos.append(
                    VideoMetadata(
                        youtube_video_id = video_id,
                        title=item["snippet"]["title"],
                        description=item["snippet"]["description"],
                        channel_id = item["snippet"]["channelId"],
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        uploaded_at=datetime.fromisoformat(item["snippet"]["publishedAt"][:-1]),
                    )
                )
          next_page_token = response.get('nextPageToken')


        logger.info(f"Found {len(videos)} videos for playlist ID: {playlist_id}")
        return videos
      except HttpError as e:
          logger.error(f"An error occurred while fetching videos from playlist ID {playlist_id}: {e}")
          return []

    async def fetch_channel_info(self, channel_id: str, user_id: Optional[str] = None) -> Optional[ChannelInfo]:
        """
        Fetches channel information by its youtube id

        Args:
            channel_id (str): The YouTube channel ID.
            user_id (Optional[str]): User ID for OAuth flow. If None, uses API key.

        Returns:
            ChannelInfo: A channel info record or none if no channel is found.
        """
        logger.info(f"Fetching channel info for channel ID: {channel_id}")
        try:
          youtube = await self._get_youtube_client(user_id)
          request = youtube.channels().list(
              part="snippet",
              id=channel_id
          )
          response = await asyncio.to_thread(request.execute)
          items = response.get("items", [])
          if items:
            item = items[0]
            channel_info =  ChannelInfo(
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