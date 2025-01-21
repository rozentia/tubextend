# agents/channel_monitor.py
import asyncio
from typing import List, Optional, Tuple, Dict
from datetime import datetime, timedelta
import uuid
from collections import defaultdict
import time

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
        self.batch_size = 50  # Maximum videos to process in one batch
        self.max_retries = 3  # Maximum number of retries for API calls
        self.rate_limit = 10000  # Requests per day (YouTube API quota)
        self._request_count = 0
        self._last_request_time = time.time()
        self._progress: Dict[str, Dict] = defaultdict(lambda: {"total": 0, "processed": 0})

    def _update_progress(self, source_id: str, total: Optional[int] = None, processed: Optional[int] = None):
        """Update progress tracking for a source."""
        if total is not None:
            self._progress[str(source_id)]["total"] = total
        if processed is not None:
            self._progress[str(source_id)]["processed"] = processed
        
        # Log progress
        progress = self._progress[str(source_id)]
        if progress["total"] > 0:
            percentage = (progress["processed"] / progress["total"]) * 100
            logger.info(f"Progress for source {source_id}: {percentage:.2f}% ({progress['processed']}/{progress['total']})")

    async def _check_rate_limit(self):
        """Check and handle API rate limiting."""
        current_time = time.time()
        day_seconds = 24 * 60 * 60
        
        # Reset counter if a new day has started
        if current_time - self._last_request_time > day_seconds:
            self._request_count = 0
            self._last_request_time = current_time
            
        # If we're approaching the limit, wait until next reset
        if self._request_count >= self.rate_limit * 0.9:  # 90% of limit
            wait_time = day_seconds - (current_time - self._last_request_time)
            logger.warning(f"Approaching API rate limit. Waiting {wait_time:.2f} seconds.")
            await asyncio.sleep(wait_time)
            self._request_count = 0
            self._last_request_time = time.time()
        
        self._request_count += 1

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
        """Processes a channel collection for new videos with progress tracking."""
        logger.info(f"Processing channel collection: {source.name} (ID: {source.id})")
        source_channels = self.database.get_source_channels_by_source(source.id)
        if not source_channels:
            logger.warning(f"No channels found for source: {source.name} (ID: {source.id})")
            return

        self._update_progress(source.id, total=len(source_channels))
        processed_channels = 0

        all_new_videos = []
        for source_channel in source_channels:
            try:
                channel = self.database.get_channel(youtube_channel_id=source_channel.youtube_channel_id)
                if not channel:
                    logger.warning(f"Channel with youtube id {source_channel.youtube_channel_id} not found in database.")
                    continue

                new_videos = await self._fetch_new_videos_from_channel(channel=channel, user_id=user.id)
                all_new_videos.extend(new_videos)
                
                processed_channels += 1
                self._update_progress(source.id, processed=processed_channels)
                
            except Exception as e:
                logger.error(f"Error processing channel {source_channel.youtube_channel_id}: {e}")
                continue

        await self._process_new_videos(user=user, source=source, new_videos=all_new_videos, jobs=jobs)

    async def _process_playlist(self, user: UserInfo, source: SourceInfo, jobs: List[GenerationJob]):
        """Processes a playlist for new videos."""
        logger.info(f"Processing playlist: {source.name} (ID: {source.id})")
        new_videos = await self._fetch_new_videos_from_playlist(source=source, user_id=user.id)
        await self._process_new_videos(user=user, source=source, new_videos=new_videos, jobs=jobs)

    async def _process_videos(self, videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """Helper method to process and store videos."""
        processed_videos = []
        # Use a set to track processed video IDs in this batch
        processed_ids = set()
        
        for video in videos:
            if video.youtube_video_id in processed_ids:
                continue
                
            stored_video = self.database.get_video(youtube_video_id=video.youtube_video_id)
            if not stored_video:
                inserted_video = self.database.insert_video(video=video)
                if inserted_video:
                    processed_videos.append(inserted_video)
                    processed_ids.add(video.youtube_video_id)
                else:
                    logger.error(f"Could not insert video with id {video.youtube_video_id}")
            else:
                processed_videos.append(stored_video)
                processed_ids.add(video.youtube_video_id)
        return processed_videos

    async def _fetch_new_videos_from_channel(self, channel: ChannelInfo, user_id: str) -> List[VideoMetadata]:
        """Fetches new videos from a YouTube channel with rate limiting."""
        try:
            await self._check_rate_limit()
            logger.info(f"Fetching new videos from channel: {channel.title}")
            latest_videos = await self.youtube_api.fetch_channel_videos(
                channel_id=channel.youtube_channel_id,
                user_id=user_id
            )
            logger.info(f"Found {len(latest_videos)} new videos from channel: {channel.title}")
            return latest_videos  # Return raw videos without processing
        except Exception as e:
            if 'quota exceeded' in str(e).lower():
                logger.error("YouTube API quota exceeded. Waiting before retry...")
                await asyncio.sleep(60)  # Wait a minute before retrying
                return []
            logger.error(f"Error fetching videos from channel {channel.title}: {e}")
            return []

    async def _fetch_new_videos_from_playlist(self, source: SourceInfo, user_id: str) -> List[VideoMetadata]:
        """Fetches new videos from a YouTube playlist."""
        logger.info(f"Fetching new videos from playlist: {source.name}")
        if not source.youtube_playlist_id:
            logger.error(f"Playlist ID not found for source: {source.name}")
            return []

        try:
            latest_videos = await self.youtube_api.fetch_playlist_videos(
                playlist_id=source.youtube_playlist_id,
                user_id=user_id
            )
            logger.info(f"Found {len(latest_videos)} new videos from playlist: {source.name}")
            return latest_videos  # Return raw videos without processing
        except Exception as e:
            logger.error(f"Error fetching videos from playlist: {e}")
            return []

    async def _process_videos_batch(self, videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """Process a batch of videos with retry logic."""
        processed_videos = []
        retry_count = 0
        
        # Create a set to track processed video IDs
        processed_ids = set()
        
        while videos and retry_count < self.max_retries:
            try:
                current_batch = videos[:self.batch_size]
                # Filter out already processed videos
                current_batch = [v for v in current_batch if v.youtube_video_id not in processed_ids]
                
                if not current_batch:
                    videos = videos[self.batch_size:]
                    continue
                    
                processed = await self._process_videos(current_batch)
                processed_videos.extend(processed)
                # Add processed video IDs to the set
                processed_ids.update(v.youtube_video_id for v in processed)
                videos = videos[self.batch_size:]
                retry_count = 0  # Reset retry count on success
            except Exception as e:
                if 'quota exceeded' in str(e).lower():
                    logger.error("YouTube API quota exceeded. Waiting before retry...")
                    await asyncio.sleep(60)  # Wait a minute before retrying
                    retry_count += 1
                else:
                    logger.error(f"Error processing video batch: {e}")
                    retry_count += 1
        
        return processed_videos

    async def _process_new_videos(self, user: UserInfo, source: SourceInfo, new_videos: List[VideoMetadata], jobs: List[GenerationJob]):
        """Processes new videos from a source, updates the database, and creates a generation job."""
        
        logger.info(f"Processing {len(new_videos)} new videos from source: {source.name} (ID: {source.id})")
        
        # Group videos by channel for more efficient processing
        videos_by_channel = defaultdict(list)
        for video in new_videos:
            videos_by_channel[video.channel_id].append(video)
            
        # Process videos in batches by channel
        processed_videos_all = []
        for channel_id, channel_videos in videos_by_channel.items():
            try:
                processed_videos = await self._process_videos_batch(channel_videos)
                processed_videos_all.extend(processed_videos)
                
                # Bulk insert source video links
                source_videos = [
                    SourceVideoInfo(source_id=source.id, youtube_video_id=video.youtube_video_id)
                    for video in processed_videos
                ]
                
                # Use database's bulk operations
                for batch in [source_videos[i:i + self.batch_size] for i in range(0, len(source_videos), self.batch_size)]:
                    try:
                        self.database.bulk_insert_source_videos(batch)
                    except Exception as e:
                        logger.error(f"Error bulk inserting source videos: {e}")
                        # Fall back to individual inserts if bulk fails
                        for source_video in batch:
                            try:
                                self.database.insert_source_video(source_video=source_video)
                            except Exception as e:
                                logger.error(f"Error inserting source video {source_video.youtube_video_id}: {e}")
                                
            except Exception as e:
                logger.error(f"Error processing videos for channel {channel_id}: {e}")
                continue

        if not processed_videos_all:
            logger.info(f"No new videos to process for source: {source.name} (ID: {source.id})")
            return

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