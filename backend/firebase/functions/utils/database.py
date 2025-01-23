# utils/database.py
import supabase
from utils.config import config
from utils.logger import setup_logger
from models.user_info import UserInfo
from models.channel_info import ChannelInfo
from models.source_info import SourceInfo
from models.source_channel_info import SourceChannelInfo
from models.video_metadata import VideoMetadata
from models.source_video_info import SourceVideoInfo
from models.transcript import Transcript
from models.podcast_metadata import PodcastMetadata
from models.podcast_video_info import PodcastVideoInfo
from models.generation_job import GenerationJob
from typing import List, Optional, Dict, Any, Set, NewType, TypeVar, Callable, ParamSpec, Tuple, Union
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
from pydantic import BaseModel
from functools import lru_cache, wraps
import time
from dataclasses import dataclass

logger = setup_logger(__name__)

class DatabaseError(Exception):
    """Base exception for database operations"""
    pass

class RecordNotFoundError(DatabaseError):
    """Raised when a record is not found"""
    pass

class DuplicateRecordError(DatabaseError):
    """Raised when trying to insert a duplicate record"""
    pass

T = TypeVar('T')
P = ParamSpec('P')

# Custom types for better type safety
FirebaseUID = NewType('FirebaseUID', str)
YoutubeVideoID = NewType('YoutubeVideoID', str)
YoutubeChannelID = NewType('YoutubeChannelID', str)

class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._ttls: Dict[str, datetime] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None
        
        if self._ttls[key] < datetime.now():
            del self._cache[key]
            del self._ttls[key]
            return None
            
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: timedelta):
        """Set value in cache with TTL."""
        self._cache[key] = value
        self._ttls[key] = datetime.now() + ttl

class Database:
    """Database interface for TubeXtend.
    
    This class provides a high-level interface to interact with the Supabase database.
    It implements connection pooling, query optimization, performance monitoring,
    and caching for frequently accessed data.
    
    Features:
        - Connection pooling using lru_cache
        - Query performance monitoring and logging
        - Soft delete support for relevant tables
        - Database migration tracking
        - In-memory caching with TTL
        - Comprehensive error handling
    
    Examples:
        Initialize database connection:
        >>> db = Database()
        
        Fetch user with caching:
        >>> user = db.get_user("firebase_uid")
        
        Apply database migration:
        >>> migration = db.apply_migration(
        ...     version="001",
        ...     name="add_users_table",
        ...     sql="CREATE TABLE users (...)",
        ...     description="Initial users table"
        ... )
        
        Monitor query performance:
        >>> stats = db.get_query_stats()
        >>> print(f"Average query time: {stats['avg_duration']:.3f}s")
    """
    
    @staticmethod
    @lru_cache(maxsize=1)
    def _get_client():
        """Get or create a cached Supabase client instance."""
        return supabase.create_client(config.supabase_url, config.supabase_anon_key)

    def __init__(self):
        """Initialize database connection and caching."""
        self.client = self._get_client()
        self._query_stats = {
            'total_queries': 0,
            'total_duration': 0.0,
            'slow_queries': [],
        }
        self._cache = Cache()

    def _handle_error(self, error: Exception, operation: str) -> None:
        """Centralized error handling for database operations.
        
        Args:
            error: The caught exception
            operation: Description of the operation that failed
            
        Raises:
            DatabaseError: With appropriate context
            RecordNotFoundError: For missing records
            DuplicateRecordError: For duplicate key violations
        """
        error_str = str(error)
        
        if 'duplicate key value violates unique constraint' in error_str:
            raise DuplicateRecordError(f"Duplicate record in {operation}: {error_str}")
        elif 'record not found' in error_str:
            raise RecordNotFoundError(f"Record not found in {operation}: {error_str}")
        else:
            logger.error(f"Database error in {operation}: {error_str}")
            raise DatabaseError(f"Error in {operation}: {error_str}")

    def _serialize_model(self, model: BaseModel) -> dict:
        """Serialize model data for database operations.
        
        Converts:
        - datetime objects to ISO format strings
        - UUID objects to strings
        - Enum values to their string representation
        """
        data = model.model_dump()
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                data[key] = str(value)
            elif isinstance(value, Enum):
                data[key] = value.value
            elif isinstance(value, dict):
                # Handle nested dictionaries (like preferences)
                for k, v in value.items():
                    if isinstance(v, (datetime, uuid.UUID, Enum)):
                        value[k] = str(v)
        return data

    def _select_columns(self, table: str, columns: Optional[Set[str]] = None) -> str:
        """Helper method to generate optimized SELECT statement.
        
        Args:
            table: Table name
            columns: Set of column names to select. If None, selects all columns.
            
        Returns:
            str: Comma-separated list of columns or '*'
        """
        if not columns:
            return '*'
        return ','.join(columns)

    def _log_slow_query(self, operation: str, duration: float, table: str):
        """Log slow queries for monitoring.
        
        Args:
            operation: Name of the database operation
            duration: Time taken in seconds
            table: Name of the table being operated on
        """
        if duration > 1.0:  # Consider queries taking > 1s as slow
            self._query_stats['slow_queries'].append({
                'operation': operation,
                'duration': duration,
                'table': table,
                'timestamp': datetime.now()
            })
            logger.warning(
                f"Slow query detected - Operation: {operation}, "
                f"Table: {table}, Duration: {duration:.3f}s"
            )

    def _cache_key(self, prefix: str, *args) -> str:
        """Generate cache key from prefix and arguments.
        
        Args:
            prefix: Cache key prefix
            *args: Additional arguments to include in key
            
        Returns:
            str: Cache key
        """
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"

    def _cached_query(
        self,
        cache_key: str,
        query_func: Callable[[], T],
        ttl: timedelta = timedelta(minutes=5)
    ) -> T:
        """Execute query with caching.
        
        Args:
            cache_key: Key for caching result
            query_func: Function to execute if cache miss
            ttl: Time-to-live for cached result
            
        Returns:
            Query result (from cache or fresh)
        """
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
            
        result = query_func()
        self._cache.set(cache_key, result, ttl)
        return result

    def _monitor_query(func):
        """Decorator to monitor query execution time and collect stats."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(self, *args, **kwargs)
                duration = time.perf_counter() - start_time
                
                # Update query stats
                self._query_stats['total_queries'] += 1
                self._query_stats['total_duration'] += duration
                
                # Track slow queries (over 1 second)
                if duration >= 1.0:
                    self._query_stats['slow_queries'].append({
                        'query': func.__name__,
                        'duration': duration,
                        'timestamp': datetime.now(timezone.utc)
                    })
                    
                return result
            except Exception as e:
                # Still count failed queries
                duration = time.perf_counter() - start_time
                self._query_stats['total_queries'] += 1
                self._query_stats['total_duration'] += duration
                raise e
        return wrapper

    @_monitor_query
    def get_user(
        self,
        user_id: FirebaseUID,
        columns: Optional[Set[str]] = None,
        use_cache: bool = True
    ) -> UserInfo:
        """Get user information by ID with optional column selection and caching.
        
        This method supports column selection for optimized queries and optional
        caching for frequently accessed users.
        
        Args:
            user_id (FirebaseUID): Firebase UID of the user
            columns (Optional[Set[str]]): Specific columns to retrieve
            use_cache (bool): Whether to use caching (default: True)
            
        Returns:
            UserInfo: User information object
            
        Raises:
            RecordNotFoundError: If user is not found
            DatabaseError: If there's an error querying the database
            
        Examples:
            Fetch all user fields:
            >>> user = db.get_user("firebase_uid")
            
            Fetch specific fields:
            >>> user = db.get_user(
            ...     "firebase_uid",
            ...     columns={"email", "display_name"}
            ... )
            
            Bypass cache:
            >>> user = db.get_user(
            ...     "firebase_uid",
            ...     use_cache=False
            ... )
        """
        def query_func():
            try:
                select_cols = self._select_columns('users', columns)
                query = self.client.table('users').select(select_cols).eq('id', user_id)
                response = query.execute()
                
                if not response.data:
                    logger.warning(f"User with id {user_id} was not found in the database")
                    raise RecordNotFoundError(f"User with id {user_id} not found")
                return UserInfo(**response.data[0])
            except RecordNotFoundError:
                raise  # Re-raise RecordNotFoundError
            except Exception as e:
                self._handle_error(e, f"get_user(user_id={user_id})")
        
        if not use_cache:
            return query_func()
            
        cache_key = self._cache_key('user', user_id, sorted(columns) if columns else 'all')
        return self._cached_query(cache_key, query_func)

    def insert_user(self, user: UserInfo) -> UserInfo:
        """Insert a new user into the database.
        
        Args:
            user (UserInfo): User information to insert
        
        Returns:
            UserInfo: Inserted user information
            
        Raises:
            DuplicateRecordError: If user with same email already exists
            DatabaseError: If there's an error inserting the user
        """
        logger.info(f"Inserting user in DB: {user}")
        try:
            response = self.client.table('users').insert(self._serialize_model(user)).execute()
            return UserInfo(**response.data[0])
        except Exception as e:
            error_msg = str(e)
            if 'duplicate key value violates unique constraint' in error_msg:
                logger.error(f"Duplicate user error: {error_msg}")
                raise DuplicateRecordError(f"User with email {user.email} already exists")
            logger.error(f"Error inserting user: {error_msg}")
            raise DatabaseError(f"Error inserting user: {error_msg}")

    def _serialize_update_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize dictionary data for database updates.
        
        This method handles partial updates where the data might not conform
        to a complete model schema.
        
        Args:
            data: Dictionary of fields to update
            
        Returns:
            Dict with serialized values
        """
        serialized = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                serialized[key] = str(value)
            elif isinstance(value, Enum):
                serialized[key] = value.value
            elif isinstance(value, dict):
                # Handle nested dictionaries
                serialized[key] = self._serialize_update_data(value)
            else:
                serialized[key] = value
        return serialized

    def update_user(self, user_id: str, updated_data: Dict[str, Any]) -> UserInfo:
        """Update user information.
        
        Args:
            user_id (str): Firebase UID of the user to update
            updated_data (Dict[str, Any]): Dictionary of fields to update
        
        Returns:
            UserInfo: Updated user information
            
        Raises:
            RecordNotFoundError: If user is not found
            DatabaseError: If there's an error updating the user
        """
        updated_data['updated_at'] = datetime.now()
        serialized_data = self._serialize_update_data(updated_data)
        
        logger.info(f"Updating user with id: {user_id}, with data: {serialized_data}")
        try:
            response = self.client.table('users').update(serialized_data).eq('id', user_id).execute()
            if not response.data:
                raise RecordNotFoundError(f"User with id {user_id} not found")
            return UserInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise DatabaseError(f"Error updating user: {str(e)}")

    def update_user_token(self, user_id: str, refresh_token: str, expires_at: datetime) -> Optional[UserInfo]:
        """
        Update user's OAuth token information.

        Args:
            user_id (str): The Firebase UID of the user
            refresh_token (str): The new refresh token
            expires_at (datetime): Token expiration timestamp

        Returns:
            Optional[UserInfo]: Updated user info or None if update failed
        """
        try:
            updated_data = {
                'refresh_token': refresh_token,
                'token_expires_at': expires_at,
                'updated_at': datetime.now()
            }
            serialized_data = self._serialize_update_data(updated_data)

            result = self.client.table('users').update(serialized_data).eq('id', user_id).execute()
            
            if result.data:
                return UserInfo.model_validate(result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error updating user token: {e}")
            return None

    #- Channel Operations
    @_monitor_query
    def get_channel(self, youtube_channel_id: str) -> Optional[ChannelInfo]:
        """Get channel information by YouTube channel ID."""
        logger.info(f"Fetching channel with ID: {youtube_channel_id}")
        try:
            response = self.client.table('channels').select('*').eq('youtube_channel_id', youtube_channel_id).execute()
            if not response.data:
                logger.warning(f"Channel with id {youtube_channel_id} was not found in the database")
                return None
            return ChannelInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error fetching channel: {str(e)}")
            raise DatabaseError(f"Error fetching channel: {str(e)}")

    @_monitor_query
    def insert_channel(self, channel: ChannelInfo) -> ChannelInfo:
        """Insert or update a channel.
        
        Args:
            channel: Channel information to insert/update
            
        Returns:
            ChannelInfo: Inserted/updated channel information
            
        Raises:
            DatabaseError: If there's an error upserting the channel
        """
        logger.info(f"Upserting channel in DB: {channel}")
        try:
            response = self.client.table('channels')\
                .upsert(self._serialize_model(channel), 
                       on_conflict='youtube_channel_id')\
                .execute()
            return ChannelInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error upserting channel: {e}")
            raise DatabaseError(f"Error upserting channel: {e}")

    def update_channel(self, youtube_channel_id: str, updated_data: Dict) -> Optional[ChannelInfo]:
        """Update channel information.
        
        Args:
            youtube_channel_id (str): YouTube channel ID
            updated_data (Dict): Data to update
        
        Returns:
            Optional[ChannelInfo]: Updated channel information or None if error
        """
        serialized_data = self._serialize_update_data(updated_data)
        logger.info(f"Updating channel with id: {youtube_channel_id}, with data: {serialized_data}")
        try:
            response = self.client.table('channels').update(serialized_data).eq('youtube_channel_id', youtube_channel_id).execute()
            if not response.data:
                logger.warning(f"Channel with id {youtube_channel_id} was not found in the database")
                return None
            return ChannelInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error updating channel: {str(e)}")
            return None

    #- Source Operations
    @_monitor_query
    def get_source(self, source_id: Union[uuid.UUID, str]) -> Optional[SourceInfo]:
        """Get source by ID.
        
        Args:
            source_id: UUID of the source (can be string or UUID object)
            
        Returns:
            Optional[SourceInfo]: Source if found, None otherwise
            
        Raises:
            DatabaseError: If there's an error fetching the source or if UUID is invalid
        """
        logger.info(f"Fetching source with ID: {source_id}")
        try:
            # Validate and convert UUID
            if isinstance(source_id, str):
                try:
                    source_id = uuid.UUID(source_id)
                except ValueError as e:
                    logger.error(f"Invalid UUID format: {source_id}")
                    raise DatabaseError(f"Invalid UUID format: {source_id}") from e
            
            response = self.client.table('sources')\
                .select('*')\
                .eq('id', str(source_id))\
                .execute()
            
            if not response.data:
                logger.warning(f"Source with id {source_id} was not found in the database")
                return None
            
            return SourceInfo(**response.data[0])
        
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error fetching source: {str(e)}")
            raise DatabaseError(f"Error fetching source: {str(e)}")

    def get_sources_by_user(self, user_id: str, page: int = 1, page_size: int = 20) -> List[SourceInfo]:
        """Get paginated sources for a user."""
        logger.info(f"Fetching sources for user ID: {user_id} (page {page})")
        try:
            offset = (page - 1) * page_size
            response = self.client.table('sources')\
                .select('*')\
                .eq('user_id', user_id)\
                .range(offset, offset + page_size - 1)\
                .execute()
            return [SourceInfo(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching sources: {str(e)}")
            raise DatabaseError(f"Error fetching sources: {str(e)}")

    def insert_source(self, source: SourceInfo) -> Optional[SourceInfo]:
        """Insert a new source."""
        logger.info(f"Inserting source in DB: {source}")
        try:
            response = self.client.table('sources').insert(self._serialize_model(source)).execute()
            return SourceInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error inserting source: {str(e)}")
            return None

    def update_source(self, source_id: uuid.UUID, updated_data: Dict) -> Optional[SourceInfo]:
        """Update source information."""
        serialized_data = self._serialize_update_data(updated_data)
        logger.info(f"Updating source with id: {source_id}, with data: {serialized_data}")
        try:
            response = self.client.table('sources').update(serialized_data).eq('id', source_id).execute()
            if not response.data:
                logger.warning(f"Source with id {source_id} was not found in the database")
                return None
            return SourceInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error updating source: {str(e)}")
            return None

    def delete_source(self, source_id: uuid.UUID) -> bool:
        """Delete a source and all related records."""
        logger.info(f"Deleting source with id: {source_id}")
        try:
            self.client.table('sources').delete().eq('id', source_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting source: {str(e)}")
            return False

    #- SourceChannel Operations
    def insert_source_channel(self, source_channel: SourceChannelInfo) -> Optional[SourceChannelInfo]:
        """Insert a new source channel."""
        logger.info(f"Inserting source channel in DB: {source_channel}")
        try:
            response = self.client.table('source_channels').insert(self._serialize_model(source_channel)).execute()
            return SourceChannelInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error inserting source channel: {str(e)}")
            return None

    def get_source_channels_by_source(self, source_id: uuid.UUID) -> List[SourceChannelInfo]:
        """Get source channels for a source."""
        logger.info(f"Fetching source channels for source with ID: {source_id}")
        try:
            response = self.client.table('source_channels').select('*').eq('source_id', source_id).execute()
            return [SourceChannelInfo(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching source channels: {str(e)}")
            return []

    #- Video Operations
    @_monitor_query
    def get_video(self, youtube_video_id: str) -> Optional[VideoMetadata]:
        """Get video metadata by YouTube video ID.
        
        Args:
            youtube_video_id (str): YouTube video ID
            
        Returns:
            Optional[VideoMetadata]: Video metadata if found, None otherwise
            
        Raises:
            DatabaseError: If there's an error querying the database
        """
        logger.info(f"Fetching video with ID: {youtube_video_id}")
        try:
            response = self.client.table('videos')\
                .select('*')\
                .eq('youtube_video_id', youtube_video_id)\
                .execute()
            
            if not response.data:
                logger.warning(f"Video with id {youtube_video_id} was not found in the database")
                return None
            
            return VideoMetadata(**response.data[0])
        except Exception as e:
            logger.error(f"Error fetching video: {str(e)}")
            raise DatabaseError(f"Error fetching video: {str(e)}")

    def insert_video(self, video: VideoMetadata) -> Optional[VideoMetadata]:
        """Insert or update a video."""
        logger.info(f"Upserting video in DB: {video.title} ({video.youtube_video_id})")
        try:
            response = self.client.table('videos').upsert(
                self._serialize_model(video),
                on_conflict='youtube_video_id'
            ).execute()
            return VideoMetadata(**response.data[0])
        except Exception as e:
            logger.error(f"Error upserting video: {str(e)}")
            return None

    def bulk_insert_videos(self, videos: List[VideoMetadata]) -> List[VideoMetadata]:
        """Bulk insert multiple videos.
        
        Args:
            videos (List[VideoMetadata]): List of videos to insert
            
        Returns:
            List[VideoMetadata]: List of inserted videos
            
        Raises:
            DatabaseError: If there's an error inserting the videos
            
        Note:
            This method is optimized for inserting multiple videos in a single query.
        """
        if not videos:
            return []
            
        logger.info(f"Bulk inserting {len(videos)} videos")
        try:
            video_data = [self._serialize_model(v) for v in videos]
            response = self.client.table('videos').upsert(video_data).execute()
            return [VideoMetadata(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error bulk inserting videos: {str(e)}")
            raise DatabaseError(f"Error bulk inserting videos: {str(e)}")

    #- SourceVideo Operations
    def get_source_video(self, source_id: uuid.UUID, youtube_video_id:str) -> Optional[SourceVideoInfo]:
        """Get source video by source ID and video ID."""
        logger.info(f"Fetching source video with source ID: {source_id} and video ID: {youtube_video_id}")
        try:
            response = self.client.table('source_videos').select("*").eq('source_id', source_id).eq('youtube_video_id',youtube_video_id).execute()
            if not response.data:
                logger.warning(f"Source video with source id {source_id} and video id {youtube_video_id} not found in database")
                return None
            return SourceVideoInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error fetching source video: {str(e)}")
            return None

    def insert_source_video(self, source_video: SourceVideoInfo) -> Optional[SourceVideoInfo]:
        """Insert a new source video."""
        logger.info(f"Inserting source video in DB: {source_video}")
        try:
            response = self.client.table('source_videos').insert(self._serialize_model(source_video)).execute()
            return SourceVideoInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error inserting source video: {str(e)}")
            return None
    
    def bulk_insert_source_videos(self, source_videos: List[SourceVideoInfo]) -> List[SourceVideoInfo]:
        """Bulk insert multiple source videos."""
        logger.info(f"Bulk inserting {len(source_videos)} source videos")
        try:
            source_video_data = [self._serialize_model(v) for v in source_videos]
            response = self.client.table('source_videos').upsert(source_video_data).execute()
            return [SourceVideoInfo(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error bulk inserting source videos: {str(e)}")
            return []

    def get_source_videos_by_source(self, source_id:uuid.UUID) -> List[SourceVideoInfo]:
        logger.info(f"Fetching source videos for source ID: {source_id}")
        try:
            response = self.client.table('source_videos').select('*').eq('source_id', source_id).execute()
            return [SourceVideoInfo(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching source videos: {str(e)}")
            return []

    def update_source_video(self, source_id: uuid.UUID, youtube_video_id: str, updated_data: Dict) -> Optional[SourceVideoInfo]:
        """Update source video information."""
        serialized_data = self._serialize_update_data(updated_data)
        logger.info(f"Updating source video with source ID: {source_id} and video id: {youtube_video_id}, with data {serialized_data}")
        try:
            response = self.client.table('source_videos').update(serialized_data)\
                .eq('source_id', source_id)\
                .eq('youtube_video_id', youtube_video_id)\
                .execute()
            if not response.data:
                logger.warning(f"Source video not found for source {source_id} and video {youtube_video_id}")
                return None
            return SourceVideoInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error updating source video: {str(e)}")
            return None

    def get_videos_to_process(self, source_id: uuid.UUID) -> List[SourceVideoInfo]:
        """Get unprocessed videos for a source.
        
        Args:
            source_id (uuid.UUID): ID of the source to get unprocessed videos for
            
        Returns:
            List[SourceVideoInfo]: List of unprocessed video information
            
        Raises:
            DatabaseError: If there's an error fetching the videos
        """
        logger.info(f"Fetching unprocessed videos for source id: {source_id}")
        try:
            response = self.client.table('source_videos').select('*').eq('source_id', source_id).is_('processed_at', None).execute()
            return [SourceVideoInfo(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching unprocessed videos: {str(e)}")
            raise DatabaseError(f"Error fetching unprocessed videos: {str(e)}")

    def bulk_update_source_videos(self, source_id: uuid.UUID, video_ids: List[str], processed_at: datetime) -> bool:
        """Bulk update the processed_at timestamp for multiple source videos.
        
        Args:
            source_id (uuid.UUID): The ID of the source
            video_ids (List[str]): List of YouTube video IDs to update
            processed_at (datetime): Timestamp to set for all videos
        
        Returns:
            bool: True if update was successful
            
        Raises:
            DatabaseError: If there's an error updating the videos
            
        Example:
            >>> db = Database()
            >>> video_ids = ["video1", "video2", "video3"]
            >>> success = db.bulk_update_source_videos(
            ...     source_id=uuid.uuid4(),
            ...     video_ids=video_ids,
            ...     processed_at=datetime.now()
            ... )
        """
        logger.info(f"Bulk updating {len(video_ids)} source videos for source {source_id}")
        try:
            update_data = {'processed_at': processed_at}
            response = self.client.table('source_videos')\
                .update(self._serialize_update_data(update_data))\
                .eq('source_id', source_id)\
                .in_('youtube_video_id', video_ids)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Error bulk updating source videos: {str(e)}")
            raise DatabaseError(f"Error bulk updating source videos: {str(e)}")

    #- Transcript Operations
    def get_transcript(self, youtube_video_id: str) -> Optional[Transcript]:
        """Get transcript for a video."""
        logger.info(f"Fetching transcript for video ID: {youtube_video_id}")
        try:
            response = self.client.table('transcripts').select('*').eq('youtube_video_id', youtube_video_id).execute()
            if not response.data:
                logger.warning(f"Transcript for video with id {youtube_video_id} was not found in the database")
                return None
            return Transcript(**response.data[0])
        except Exception as e:
            logger.error(f"Error fetching transcript: {str(e)}")
            return None

    def insert_transcript(self, transcript: Transcript) -> Optional[Transcript]:
        """Insert a new transcript."""
        logger.info(f"Inserting transcript in DB: {transcript}")
        try:
            response = self.client.table('transcripts').insert(self._serialize_model(transcript)).execute()
            return Transcript(**response.data[0])
        except Exception as e:
            logger.error(f"Error inserting transcript: {str(e)}")
            return None

    #- Podcast Operations
    def get_podcast(self, podcast_id: uuid.UUID) -> Optional[PodcastMetadata]:
        """Get podcast metadata by ID."""
        logger.info(f"Fetching podcast with id: {podcast_id}")
        try:
            response = self.client.table('podcasts').select('*').eq('id', podcast_id).execute()
            if not response.data:
                logger.warning(f"Podcast with id {podcast_id} was not found in the database")
                return None
            return PodcastMetadata(**response.data[0])
        except Exception as e:
            logger.error(f"Error fetching podcast: {str(e)}")
            return None

    def insert_podcast(self, podcast: PodcastMetadata) -> Optional[PodcastMetadata]:
        """Insert a new podcast."""
        logger.info(f"Inserting podcast in DB: {podcast}")
        try:
            response = self.client.table('podcasts').insert(self._serialize_model(podcast)).execute()
            return PodcastMetadata(**response.data[0])
        except Exception as e:
            logger.error(f"Error inserting podcast: {str(e)}")
            return None
    
    def delete_podcast(self, podcast_id: uuid.UUID) -> bool:
        """Delete a podcast."""
        logger.info(f"Deleting podcast with id: {podcast_id}")
        try:
            self.client.table('podcasts').delete().eq('id', podcast_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting podcast: {str(e)}")
            return False

    #- PodcastVideo Operations
    def insert_podcast_video(self, podcast_video: PodcastVideoInfo) -> Optional[PodcastVideoInfo]:
        """Insert a new podcast video relation."""
        logger.info(f"Inserting podcast video relation in DB: {podcast_video}")
        try:
            response = self.client.table('podcast_videos').insert(self._serialize_model(podcast_video)).execute()
            return PodcastVideoInfo(**response.data[0])
        except Exception as e:
            logger.error(f"Error inserting podcast video relation: {str(e)}")
            return None

    def get_podcast_videos_by_podcast(self, podcast_id: uuid.UUID) -> List[PodcastVideoInfo]:
        """Get podcast videos for a podcast."""
        logger.info(f"Fetching podcast videos for podcast id: {podcast_id}")
        try:
            response = self.client.table('podcast_videos').select('*').eq('podcast_id', podcast_id).execute()
            return [PodcastVideoInfo(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching podcast videos for podcast id: {podcast_id}")
            return []
    
    def delete_podcast_videos_by_podcast(self, podcast_id: uuid.UUID) -> bool:
        """Delete all podcast videos for a podcast."""
        logger.info(f"Deleting podcast videos for podcast id: {podcast_id}")
        try:
            self.client.table('podcast_videos').delete().eq('podcast_id', podcast_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting podcast videos: {str(e)}")
            return False

    #- GenerationJob Operations
    def get_generation_job(self, job_id: uuid.UUID) -> Optional[GenerationJob]:
        """Get generation job by ID."""
        logger.info(f"Fetching generation job with id: {job_id}")
        try:
            response = self.client.table('generation_jobs').select('*').eq('id', job_id).execute()
            if not response.data:
                logger.warning(f"Generation job with id {job_id} was not found in the database")
                return None
            return GenerationJob(**response.data[0])
        except Exception as e:
            logger.error(f"Error fetching generation job: {str(e)}")
            return None

    def insert_generation_job(self, job: GenerationJob) -> Optional[GenerationJob]:
        """Insert a new generation job."""
        logger.info(f"Inserting generation job in DB: {job}")
        try:
            response = self.client.table('generation_jobs').insert(self._serialize_model(job)).execute()
            return GenerationJob(**response.data[0])
        except Exception as e:
            logger.error(f"Error inserting generation job: {str(e)}")
            return None

    def update_generation_job(self, job_id: uuid.UUID, updated_data: Dict) -> Optional[GenerationJob]:
        """Update a generation job."""
        serialized_data = self._serialize_update_data(updated_data)
        logger.info(f"Updating generation job with id: {job_id}, with data: {serialized_data}")
        try:
            response = self.client.table('generation_jobs').update(serialized_data).eq('id', job_id).execute()
            if not response.data:
                logger.warning(f"Generation job with id {job_id} was not found in the database")
                return None
            return GenerationJob(**response.data[0])
        except Exception as e:
            logger.error(f"Error updating generation job: {str(e)}")
            return None

    def get_user_podcasts(self, user_id: str) -> List[PodcastMetadata]:
        """Get all podcasts for a user.
        
        Args:
            user_id (str): ID of the user
            
        Returns:
            List[PodcastMetadata]: List of podcasts owned by the user
        """
        logger.info(f"Fetching podcasts for user ID: {user_id}")
        try:
            response = (
                self.client.table('podcasts')
                .select('*')
                .eq('user_id', user_id)
                .execute()
            )
            return [PodcastMetadata(**podcast) for podcast in response.data]
        except Exception as e:
            logger.error(f"Error fetching podcasts for user {user_id}: {str(e)}")
            return []

    def get_query_stats(self) -> Dict[str, Any]:
        """Get database query statistics.
        
        Returns:
            Dict containing query statistics including:
            - total_queries: Total number of queries executed
            - total_duration: Total time spent in queries
            - avg_duration: Average query duration
            - slow_queries: List of slow queries (>1s)
        """
        stats = self._query_stats.copy()
        if stats['total_queries'] > 0:
            stats['avg_duration'] = stats['total_duration'] / stats['total_queries']
        else:
            stats['avg_duration'] = 0.0
        return stats

    @_monitor_query
    def link_channel_to_source(self, source_id: uuid.UUID, youtube_channel_id: str) -> None:
        """Link a channel to a source.
        
        Args:
            source_id: UUID of the source
            youtube_channel_id: YouTube channel ID
            
        Raises:
            DatabaseError: If there's an error linking the channel
        """
        logger.info(f"Linking channel {youtube_channel_id} to source {source_id}")
        try:
            self.client.table('source_channels').insert({
                'source_id': str(source_id),
                'youtube_channel_id': youtube_channel_id
            }).execute()
        except Exception as e:
            logger.error(f"Error linking channel to source: {str(e)}")
            raise DatabaseError(f"Error linking channel to source: {str(e)}")

    @_monitor_query
    def unlink_channel_from_source(self, source_id: uuid.UUID, youtube_channel_id: str) -> None:
        """Unlink a channel from a source."""
        logger.info(f"Unlinking channel {youtube_channel_id} from source {source_id}")
        try:
            self.client.table('source_channels')\
                .delete()\
                .eq('source_id', source_id)\
                .eq('youtube_channel_id', youtube_channel_id)\
                .execute()
        except Exception as e:
            logger.error(f"Error unlinking channel from source: {str(e)}")
            raise DatabaseError(f"Error unlinking channel from source: {str(e)}")

    @_monitor_query
    def get_source_channels(self, source_id: uuid.UUID) -> List[ChannelInfo]:
        """Get all channels linked to a source.
        
        Args:
            source_id: UUID of the source
            
        Returns:
            List[ChannelInfo]: List of channels linked to the source
            
        Raises:
            DatabaseError: If there's an error getting the channels
        """
        logger.info(f"Getting channels for source {source_id}")
        try:
            # First get the channel IDs from source_channels
            source_channels_response = self.client.table('source_channels')\
                .select('youtube_channel_id')\
                .eq('source_id', source_id)\
                .execute()
            
            if not source_channels_response.data:
                return []
            
            # Get the channel IDs
            channel_ids = [sc['youtube_channel_id'] for sc in source_channels_response.data]
            
            # Then get the channel details
            channels_response = self.client.table('channels')\
                .select('*')\
                .in_('youtube_channel_id', channel_ids)\
                .execute()
            
            return [ChannelInfo(**channel) for channel in channels_response.data]
        
        except Exception as e:
            logger.error(f"Error getting source channels: {str(e)}")
            raise DatabaseError(f"Error getting source channels: {str(e)}")

    @_monitor_query
    def link_video_to_source(self, source_id: uuid.UUID, youtube_video_id: str) -> None:
        """Link a video to a source if not already linked.
        
        Args:
            source_id: UUID of the source
            youtube_video_id: YouTube video ID
            
        Raises:
            DatabaseError: If there's an error linking the video
        """
        logger.info(f"Linking video {youtube_video_id} to source {source_id}")
        try:
            # Check if link already exists
            existing = self.client.table('source_videos')\
                .select('*')\
                .eq('source_id', source_id)\
                .eq('youtube_video_id', youtube_video_id)\
                .execute()
            
            if existing.data:
                logger.info(f"Video {youtube_video_id} already linked to source {source_id}")
                return
            
            # Create new link if it doesn't exist
            self.client.table('source_videos').insert({
                'source_id': str(source_id),
                'youtube_video_id': youtube_video_id
            }).execute()
        except Exception as e:
            logger.error(f"Error linking video to source: {str(e)}")
            raise DatabaseError(f"Error linking video to source: {str(e)}")

    @_monitor_query
    def get_source_videos(self, source_id: uuid.UUID) -> List[SourceVideoInfo]:
        """Get all videos linked to a source."""
        logger.info(f"Getting videos for source {source_id}")
        try:
            response = self.client.table('source_videos')\
                .select('*')\
                .eq('source_id', source_id)\
                .execute()
            return [SourceVideoInfo(**video) for video in response.data]
        except Exception as e:
            logger.error(f"Error getting source videos: {str(e)}")
            raise DatabaseError(f"Error getting source videos: {str(e)}")

    @_monitor_query
    def mark_video_processed(
        self,
        source_id: uuid.UUID,
        youtube_video_id: str,
        processed_at: datetime
    ) -> None:
        """Mark a video as processed for a source."""
        logger.info(f"Marking video {youtube_video_id} as processed for source {source_id}")
        try:
            self.client.table('source_videos')\
                .update({'processed_at': processed_at.isoformat()})\
                .eq('source_id', source_id)\
                .eq('youtube_video_id', youtube_video_id)\
                .execute()
        except Exception as e:
            logger.error(f"Error marking video as processed: {str(e)}")
            raise DatabaseError(f"Error marking video as processed: {str(e)}")

    @_monitor_query
    def get_processed_videos(self, source_id: uuid.UUID) -> List[SourceVideoInfo]:
        """Get all processed videos for a source."""
        logger.info(f"Getting processed videos for source {source_id}")
        try:
            response = self.client.table('source_videos')\
                .select('*')\
                .eq('source_id', source_id)\
                .not_.is_('processed_at', None)\
                .execute()
            return [SourceVideoInfo(**video) for video in response.data]
        except Exception as e:
            logger.error(f"Error getting processed videos: {str(e)}")
            raise DatabaseError(f"Error getting processed videos: {str(e)}")

    @_monitor_query
    def get_unprocessed_videos(self, source_id: uuid.UUID) -> List[SourceVideoInfo]:
        """Get all unprocessed videos for a source."""
        logger.info(f"Getting unprocessed videos for source {source_id}")
        try:
            response = self.client.table('source_videos')\
                .select('*')\
                .eq('source_id', source_id)\
                .is_('processed_at', None)\
                .execute()
            return [SourceVideoInfo(**video) for video in response.data]
        except Exception as e:
            logger.error(f"Error getting unprocessed videos: {str(e)}")
            raise DatabaseError(f"Error getting unprocessed videos: {str(e)}")

    @_monitor_query
    def bulk_insert_channels(self, channels: List[ChannelInfo]) -> List[ChannelInfo]:
        """Bulk insert multiple channels."""
        logger.info(f"Bulk inserting {len(channels)} channels")
        try:
            data = [self._serialize_model(channel) for channel in channels]
            response = self.client.table('channels').insert(data).execute()
            return [ChannelInfo(**channel) for channel in response.data]
        except Exception as e:
            logger.error(f"Error bulk inserting channels: {str(e)}")
            raise DatabaseError(f"Error bulk inserting channels: {str(e)}")

    @_monitor_query
    def bulk_mark_videos_processed(
        self,
        videos: List[Tuple[uuid.UUID, str]],
        processed_at: datetime
    ) -> None:
        """Bulk mark multiple videos as processed.
        
        Args:
            videos: List of tuples containing (source_id, youtube_video_id)
            processed_at: Timestamp when videos were processed
            
        Raises:
            DatabaseError: If there's an error marking videos as processed
        """
        logger.info(f"Bulk marking {len(videos)} videos as processed")
        try:
            # Create data array for bulk update
            data = [
                {
                    'source_id': str(source_id),
                    'youtube_video_id': video_id,
                    'processed_at': processed_at.isoformat()
                }
                for source_id, video_id in videos
            ]
            
            # Use upsert to update all records in one query
            self.client.table('source_videos')\
                .upsert(data)\
                .execute()
            
        except Exception as e:
            logger.error(f"Error bulk marking videos as processed: {str(e)}")
            raise DatabaseError(f"Error bulk marking videos as processed: {str(e)}")

    @_monitor_query
    def link_video_to_podcast(self, podcast_id: uuid.UUID, youtube_video_id: str) -> None:
        """Link a video to a podcast."""
        logger.info(f"Linking video {youtube_video_id} to podcast {podcast_id}")
        try:
            self.client.table('podcast_videos').insert({
                'podcast_id': str(podcast_id),
                'youtube_video_id': youtube_video_id
            }).execute()
        except Exception as e:
            logger.error(f"Error linking video to podcast: {str(e)}")
            raise DatabaseError(f"Error linking video to podcast: {str(e)}")

    @_monitor_query
    def get_podcast_videos(self, podcast_id: uuid.UUID) -> List[PodcastVideoInfo]:
        """Get all videos linked to a podcast."""
        logger.info(f"Getting videos for podcast {podcast_id}")
        try:
            response = self.client.table('podcast_videos')\
                .select('*')\
                .eq('podcast_id', podcast_id)\
                .execute()
            return [PodcastVideoInfo(**video) for video in response.data]
        except Exception as e:
            logger.error(f"Error getting podcast videos: {str(e)}")
            raise DatabaseError(f"Error getting podcast videos: {str(e)}")

    def get_source_video_status(self, source_id: uuid.UUID, youtube_video_id: str) -> Optional[datetime]:
        """Get processing status of a video for a source."""
        try:
            source_video = self.get_source_video(source_id, youtube_video_id)
            return source_video.processed_at if source_video else None
        except Exception as e:
            logger.error(f"Error getting source video status: {e}")
            return None

    def get_videos_for_job(self, job_id: uuid.UUID) -> List[VideoMetadata]:
        """Get all videos associated with a generation job."""
        try:
            job = self.get_generation_job(job_id)
            if not job or not job.config.processing_options.get('video_ids'):
                return []
            
            video_ids = job.config.processing_options['video_ids']
            videos = []
            for video_id in video_ids:
                video = self.get_video(video_id)
                if video:
                    videos.append(video)
            return videos
        except Exception as e:
            logger.error(f"Error getting videos for job: {e}")
            return []