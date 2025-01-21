# agents/channel_monitor.py
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from models.user_info import UserInfo
from models.channel_info import ChannelInfo
from models.source_info import SourceInfo, SourceType
from models.source_channel_info import SourceChannelInfo
from models.video_metadata import VideoMetadata
from models.generation_job import GenerationJob, JobStatus
from utils.api_wrappers import YouTubeAPI
from utils.database import Database
from utils.logger import setup_logger
from models.source_video_info import SourceVideoInfo

logger = setup_logger(__name__)

class ChannelMonitorAgent:
    def __init__(self, database: Database, youtube_api: YouTubeAPI):
        self.database = database
        self.youtube_api = youtube_api

    async def run(self, user_id: str) -> List[GenerationJob]:
        """
        Monitors YouTube channels and playlists for new videos, creates jobs, and updates the database.

        Args:
            user_id (str): The Firebase UID of the user.

        Returns:
            List[GenerationJob]: A list of created generation jobs.
        """
        logger.info(f"Starting channel monitoring for user ID: {user_id}")

        user = self.database.get_user(user_id=user_id)
        if not user:
          logger.error(f"User with ID {user_id} not found.")
          return []


        sources = self.database.get_sources_by_user(user_id=user_id)
        if not sources:
            logger.info(f"No sources found for user ID: {user_id}")
            return []

        jobs = []

        for source in sources:
            logger.info(f"Checking source: {source.name} (ID: {source.id})")

            if source.source_type == SourceType.CHANNEL_COLLECTION:
                await self._process_channel_collection(user, source, jobs)
            elif source.source_type == SourceType.PLAYLIST:
                await self._process_playlist(user, source, jobs)

        logger.info(f"Channel monitoring finished, {len(jobs)} jobs were generated.")
        return jobs


    async def _process_channel_collection(self, user: UserInfo, source: SourceInfo, jobs: List[GenerationJob]):
        """Processes a channel collection for new videos."""
        logger.info(f"Processing channel collection: {source.name} (ID: {source.id})")
        source_channels = self.database.get_source_channels_by_source(source.id)
        if not source_channels:
          logger.warning(f"No channels found for source: {source.name} (ID: {source.id})")
          return

        all_new_videos = []
        for source_channel in source_channels:
            channel = self.database.get_channel(youtube_channel_id=source_channel.youtube_channel_id)
            if not channel:
              logger.warning(f"Channel with youtube id {source_channel.youtube_channel_id} not found in database.")
              continue

            new_videos = await self._fetch_new_videos_from_channel(channel=channel, user_id=user.id)
            all_new_videos.extend(new_videos)

        await self._process_new_videos(user=user, source=source, new_videos=all_new_videos, jobs=jobs)

    async def _process_playlist(self, user: UserInfo, source: SourceInfo, jobs: List[GenerationJob]):
        """Processes a playlist for new videos."""
        logger.info(f"Processing playlist: {source.name} (ID: {source.id})")
        new_videos = await self._fetch_new_videos_from_playlist(source=source, user_id=user.id)
        await self._process_new_videos(user=user, source=source, new_videos=new_videos, jobs=jobs)

    async def _process_videos(self, videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """Helper method to process and store videos."""
        processed_videos = []
        for video in videos:
            stored_video = self.database.get_video(youtube_video_id=video.youtube_video_id)
            if not stored_video:
                inserted_video = self.database.insert_video(video=video)
                if inserted_video:
                    processed_videos.append(inserted_video)
                else:
                    logger.error(f"Could not insert video with id {video.youtube_video_id}")
            else:
                processed_videos.append(stored_video)
        return processed_videos

    async def _fetch_new_videos_from_channel(self, channel: ChannelInfo, user_id: str) -> List[VideoMetadata]:
        """Fetches new videos from a YouTube channel."""
        logger.info(f"Fetching new videos from channel: {channel.title}")
        latest_videos = await self.youtube_api.fetch_channel_videos(
            channel_id=channel.youtube_channel_id,
            user_id=user_id
        )
        processed_videos = await self._process_videos(latest_videos)
        logger.info(f"Found {len(processed_videos)} new videos from channel: {channel.title}")
        return processed_videos

    async def _fetch_new_videos_from_playlist(self, source: SourceInfo, user_id: str) -> List[VideoMetadata]:
        """Fetches new videos from a YouTube playlist."""
        logger.info(f"Fetching new videos from playlist: {source.name}")
        if not source.youtube_playlist_id:
            logger.error(f"Playlist ID not found for source: {source.name}")
            return []

        latest_videos = await self.youtube_api.fetch_playlist_videos(
            playlist_id=source.youtube_playlist_id,
            user_id=user_id
        )
        processed_videos = await self._process_videos(latest_videos)
        logger.info(f"Found {len(processed_videos)} new videos from playlist: {source.name}")
        return processed_videos

    async def _process_new_videos(self, user: UserInfo, source: SourceInfo, new_videos: List[VideoMetadata], jobs: List[GenerationJob]):
        """Processes new videos from a source, updates the database, and creates a generation job."""

        logger.info(f"Processing {len(new_videos)} new videos from source: {source.name} (ID: {source.id})")

        for video in new_videos:
            source_video = self.database.get_source_video(source_id=source.id, youtube_video_id=video.youtube_video_id)
            if not source_video:
                new_source_video = SourceVideoInfo(source_id = source.id, youtube_video_id=video.youtube_video_id)
                self.database.insert_source_video(source_video=new_source_video)
                logger.info(f"Linking video {video.youtube_video_id} to source {source.name}")
            else:
              logger.info(f"Video {video.youtube_video_id} is already linked to source {source.name}")
        # Create a new generation job
        job = GenerationJob(
            user_id=user.id,
            source_id=source.id,
            status=JobStatus.QUEUED,
            created_at=datetime.now()
        )
        inserted_job = self.database.insert_generation_job(job=job)
        if inserted_job:
          jobs.append(inserted_job)
          logger.info(f"Created generation job with id {job.id} for source: {source.name} (ID: {source.id})")
        else:
          logger.error(f"Could not create generation job for source: {source.name} (ID: {source.id})")

        # Update the last_processed_at timestamp
        updated_source = self.database.update_source(source_id=source.id, updated_data={"last_processed_at": datetime.now()})
        if updated_source:
          logger.info(f"Updated last processed timestamp for source: {source.name} (ID: {source.id}) to {updated_source.last_processed_at}")
        else:
          logger.error(f"Could not update last processed timestamp for source: {source.name} (ID: {source.id})")