import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import uuid
from utils.database import (
    Database, DatabaseError, MigrationError, MigrationInfo, RecordNotFoundError, DuplicateRecordError,
    FirebaseUID, YoutubeVideoID, YoutubeChannelID
)
from models.user_info import UserInfo
from models.channel_info import ChannelInfo
from models.source_info import SourceInfo, SourceType
from models.source_channel_info import SourceChannelInfo
from models.video_metadata import VideoMetadata
from models.source_video_info import SourceVideoInfo
from models.transcript import Transcript, TranscriptSource
from models.podcast_metadata import PodcastMetadata
from models.podcast_video_info import PodcastVideoInfo
from models.generation_job import GenerationJob, JobStatus, JobConfig
from typing import Any

# Test data fixtures
@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client with all necessary method chains."""
    mock = MagicMock()
    # Setup method chaining
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.in_.return_value = mock
    mock.is_.return_value = mock
    mock.range.return_value = mock
    mock.execute.return_value = MagicMock()
    mock.upsert.return_value = mock
    return mock

class TestCache:
    """Cache class for testing."""
    def __init__(self):
        self._cache = {}
        
    def get(self, key: str) -> Any:
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry > datetime.now(timezone.utc):
                return value
            del self._cache[key]
        return None
        
    def set(self, key: str, value: Any, ttl: timedelta) -> None:
        expiry = datetime.now(timezone.utc) + ttl
        self._cache[key] = (value, expiry)

# Patch the Cache class onto Database
Database.Cache = TestCache

@pytest.fixture
def db(mock_supabase):
    """Create a Database instance with mocked Supabase client."""
    with patch('utils.database.Database._get_client', return_value=mock_supabase):
        db = Database()
        return db

@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    now = datetime.now(timezone.utc)
    return UserInfo(
        id="test_user_id",
        email="test@example.com",
        display_name="Test User",
        created_at=now,
        updated_at=now
    )

@pytest.fixture
def sample_channel():
    """Create a sample channel for testing."""
    now = datetime.now(timezone.utc)
    return ChannelInfo(
        youtube_channel_id="test_channel_id",
        title="Test Channel",
        description="Test Description",
        channel_url="https://youtube.com/c/test",
        created_at=now
    )

@pytest.fixture
def sample_source():
    """Create a sample source for testing."""
    now = datetime.now(timezone.utc)
    return SourceInfo(
        id=uuid.uuid4(),
        user_id="test_user_id",
        source_type=SourceType.CHANNEL_COLLECTION,
        name="Test Source",
        preferences={},
        created_at=now
    )

@pytest.fixture
def sample_video():
    """Create a sample video for testing."""
    now = datetime.now(timezone.utc)
    return VideoMetadata(
        youtube_video_id="test_video_id",
        title="Test Video",
        description="Test Description",
        url="https://youtube.com/watch?v=test_video_id",
        channel_id="test_channel_id",
        uploaded_at=now,
        created_at=now
    )

@pytest.fixture
def sample_transcript():
    """Create a sample transcript for testing."""
    now = datetime.now(timezone.utc)
    return Transcript(
        id=uuid.uuid4(),
        youtube_video_id="test_video_id",
        text="Test transcript text",
        source=TranscriptSource.YOUTUBE_CAPTION,
        storage_url="gs://bucket/transcript.txt",
        created_at=now
    )

@pytest.fixture
def sample_podcast():
    """Create a sample podcast for testing."""
    now = datetime.now(timezone.utc)
    source_id = uuid.uuid4()
    return PodcastMetadata(
        id=uuid.uuid4(),
        user_id="test_user_id",
        source_id=source_id,
        storage_url="gs://bucket/test.mp3",
        title="Test Podcast",
        created_at=now
    )

@pytest.fixture
def sample_generation_job():
    """Create a sample generation job for testing."""
    now = datetime.now(timezone.utc)
    return GenerationJob(
        id=uuid.uuid4(),
        user_id="test_user_id",
        source_id=uuid.uuid4(),
        status=JobStatus.QUEUED,
        config=JobConfig(),
        created_at=now,
        updated_at=now
    )

# Test Database Initialization
def test_database_initialization(db, mock_supabase):
    """Test database initialization and connection caching."""
    # First call to check if table exists
    check_response = MagicMock()
    check_response.data = []  # Table doesn't exist
    check_response.error = None
    
    # Second call to create table
    create_response = MagicMock()
    create_response.data = []
    create_response.error = None
    
    mock_supabase.execute.side_effect = [check_response, create_response]
    
    # Re-initialize database to trigger table creation
    with patch('utils.database.Database._get_client', return_value=mock_supabase):
        db = Database()
        
    assert db.client == mock_supabase
    assert isinstance(db._cache, Database.Cache)
    mock_supabase.table.assert_called_with('migrations')

def test_cache_operations():
    """Test the Cache class operations."""
    cache = Database.Cache()
    
    # Test set and get
    cache.set('test_key', 'test_value', timedelta(minutes=5))
    assert cache.get('test_key') == 'test_value'
    
    # Test expiration
    cache.set('expired_key', 'expired_value', timedelta(seconds=-1))
    assert cache.get('expired_key') is None
    
    # Test non-existent key
    assert cache.get('non_existent') is None

# Test User Operations
class TestUserOperations:
    def test_get_user_success(self, db, mock_supabase, sample_user):
        """Test successful user retrieval."""
        mock_data = {
            'id': sample_user.id,
            'email': sample_user.email,
            'display_name': sample_user.display_name,
            'created_at': sample_user.created_at.isoformat(),
            'updated_at': sample_user.updated_at.isoformat()
        }
        mock_response = MagicMock()
        mock_response.data = [mock_data]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        user = db.get_user(sample_user.id)
        assert isinstance(user, UserInfo)
        assert user.id == sample_user.id
        assert user.email == sample_user.email
        assert user.display_name == sample_user.display_name
        
        # Verify cache was used
        cached_user = db.get_user(sample_user.id)
        assert cached_user.id == user.id
        mock_supabase.execute.assert_called_once()

    def test_get_user_not_found(self, db, mock_supabase):
        """Test user not found scenario."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        with pytest.raises(RecordNotFoundError) as exc_info:
            db.get_user("non_existent_id")
        assert "User with id non_existent_id not found" == str(exc_info.value)

    def test_get_user_database_error(self, db, mock_supabase):
        """Test database error handling."""
        mock_response = MagicMock()
        mock_response.error = "Database error"
        mock_supabase.execute.return_value = mock_response
        
        with pytest.raises(DatabaseError) as exc_info:
            db.get_user("test_id")
        assert "Error in get_user" in str(exc_info.value)

    def test_insert_user_success(self, db, mock_supabase, sample_user):
        """Test successful user insertion."""
        mock_response = MagicMock()
        mock_response.data = [sample_user.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        inserted_user = db.insert_user(sample_user)
        assert isinstance(inserted_user, UserInfo)
        assert inserted_user.id == sample_user.id
        assert inserted_user.email == sample_user.email
        assert inserted_user.display_name == sample_user.display_name

    def test_insert_user_duplicate(self, db, mock_supabase, sample_user):
        """Test duplicate user insertion."""
        mock_response = MagicMock()
        mock_response.error = "duplicate key value violates unique constraint"
        mock_supabase.execute.return_value = mock_response
        
        with pytest.raises(DuplicateRecordError) as exc_info:
            db.insert_user(sample_user)
        assert f"User with email {sample_user.email} already exists" == str(exc_info.value)

    def test_update_user_success(self, db, mock_supabase, sample_user):
        """Test successful user update."""
        updated_data = {"display_name": "Updated Name"}
        mock_response = MagicMock()
        mock_response.data = [{**sample_user.model_dump(), **updated_data}]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        updated_user = db.update_user(sample_user.id, updated_data)
        assert isinstance(updated_user, UserInfo)
        assert updated_user.display_name == "Updated Name"
        assert updated_user.id == sample_user.id
        assert updated_user.email == sample_user.email

    def test_update_user_not_found(self, db, mock_supabase):
        """Test update of non-existent user."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        with pytest.raises(RecordNotFoundError) as exc_info:
            db.update_user("non_existent_id", {"display_name": "New Name"})
        assert "User with id non_existent_id not found" == str(exc_info.value)

# Test Channel Operations
class TestChannelOperations:
    def test_get_channel_success(self, db, mock_supabase, sample_channel):
        """Test successful channel retrieval."""
        mock_response = MagicMock()
        mock_response.data = [sample_channel.model_dump()]
        mock_supabase.execute.return_value = mock_response
        
        channel = db.get_channel(sample_channel.youtube_channel_id)
        assert isinstance(channel, ChannelInfo)
        assert channel.youtube_channel_id == sample_channel.youtube_channel_id
        assert channel.title == sample_channel.title
        assert channel.description == sample_channel.description
        assert channel.channel_url == sample_channel.channel_url

    def test_get_channel_not_found(self, db, mock_supabase):
        """Test channel not found scenario."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.execute.return_value = mock_response
        
        channel = db.get_channel("non_existent_id")
        assert channel is None

    def test_get_channel_database_error(self, db, mock_supabase):
        """Test database error handling."""
        mock_supabase.execute.side_effect = Exception("Database error")
        
        channel = db.get_channel("test_channel_id")
        assert channel is None

    def test_insert_channel_success(self, db, mock_supabase, sample_channel):
        """Test successful channel insertion."""
        mock_response = MagicMock()
        mock_response.data = [sample_channel.model_dump()]
        mock_supabase.execute.return_value = mock_response
        
        inserted_channel = db.insert_channel(sample_channel)
        assert isinstance(inserted_channel, ChannelInfo)
        assert inserted_channel.youtube_channel_id == sample_channel.youtube_channel_id
        assert inserted_channel.title == sample_channel.title
        assert inserted_channel.description == sample_channel.description

    def test_insert_channel_error(self, db, mock_supabase, sample_channel):
        """Test channel insertion error."""
        mock_supabase.execute.side_effect = Exception("Database error")
        
        inserted_channel = db.insert_channel(sample_channel)
        assert inserted_channel is None

# Test Source Operations
class TestSourceOperations:
    def test_get_source_success(self, db, mock_supabase, sample_source):
        """Test successful source retrieval."""
        mock_response = MagicMock()
        mock_response.data = [sample_source.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        source = db.get_source(sample_source.id)
        assert isinstance(source, SourceInfo)
        assert source.id == sample_source.id
        assert source.name == sample_source.name
        assert source.source_type == sample_source.source_type
        assert source.user_id == sample_source.user_id

    def test_get_sources_by_user(self, db, mock_supabase, sample_source):
        """Test retrieving sources for a user."""
        mock_response = MagicMock()
        mock_response.data = [sample_source.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        sources = db.get_sources_by_user(sample_source.user_id)
        assert len(sources) == 1
        assert isinstance(sources[0], SourceInfo)
        assert sources[0].id == sample_source.id
        assert sources[0].user_id == sample_source.user_id

    def test_get_sources_by_user_with_pagination(self, db, mock_supabase, sample_source):
        """Test retrieving sources with pagination."""
        mock_response = MagicMock()
        mock_response.data = [sample_source.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        sources = db.get_sources_by_user(sample_source.user_id, page=2, page_size=10)
        assert len(sources) == 1
        mock_supabase.range.assert_called_once_with(10, 19)

    def test_insert_source_success(self, db, mock_supabase, sample_source):
        """Test successful source insertion."""
        mock_response = MagicMock()
        mock_response.data = [sample_source.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        inserted_source = db.insert_source(sample_source)
        assert isinstance(inserted_source, SourceInfo)
        assert inserted_source.id == sample_source.id
        assert inserted_source.name == sample_source.name
        assert inserted_source.source_type == sample_source.source_type

# Test Video Operations
class TestVideoOperations:
    def test_get_video_success(self, db, mock_supabase, sample_video):
        """Test successful video retrieval."""
        mock_response = MagicMock()
        mock_response.data = [sample_video.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        video = db.get_video(sample_video.youtube_video_id)
        assert isinstance(video, VideoMetadata)
        assert video.youtube_video_id == sample_video.youtube_video_id
        assert video.title == sample_video.title
        assert video.description == sample_video.description
        assert video.channel_id == sample_video.channel_id

    def test_get_video_not_found(self, db, mock_supabase):
        """Test video not found scenario."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        video = db.get_video("non_existent_id")
        assert video is None

    def test_get_video_database_error(self, db, mock_supabase):
        """Test database error handling."""
        mock_response = MagicMock()
        mock_response.error = "Database error"
        mock_supabase.execute.return_value = mock_response
        
        with pytest.raises(DatabaseError) as exc_info:
            db.get_video("test_video_id")
        assert "Database error" in str(exc_info.value)

    def test_insert_video_success(self, db, mock_supabase, sample_video):
        """Test successful video insertion."""
        mock_response = MagicMock()
        mock_response.data = [sample_video.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        inserted_video = db.insert_video(sample_video)
        assert isinstance(inserted_video, VideoMetadata)
        assert inserted_video.youtube_video_id == sample_video.youtube_video_id
        assert inserted_video.title == sample_video.title
        assert inserted_video.description == sample_video.description

    def test_bulk_insert_videos_success(self, db, mock_supabase, sample_video):
        """Test successful bulk video insertion."""
        videos = [sample_video, sample_video]
        mock_response = MagicMock()
        mock_response.data = [v.model_dump() for v in videos]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        inserted_videos = db.bulk_insert_videos(videos)
        assert len(inserted_videos) == 2
        assert all(isinstance(v, VideoMetadata) for v in inserted_videos)
        assert all(v.youtube_video_id == sample_video.youtube_video_id for v in inserted_videos)

    def test_bulk_insert_videos_empty_list(self, db, mock_supabase):
        """Test bulk insertion with empty list."""
        inserted_videos = db.bulk_insert_videos([])
        assert len(inserted_videos) == 0
        mock_supabase.execute.assert_not_called()

    def test_bulk_insert_videos_error(self, db, mock_supabase, sample_video):
        """Test bulk insertion error handling."""
        videos = [sample_video, sample_video]
        mock_response = MagicMock()
        mock_response.error = "Database error"
        mock_supabase.execute.return_value = mock_response
        
        with pytest.raises(DatabaseError) as exc_info:
            db.bulk_insert_videos(videos)
        assert "Database error" in str(exc_info.value)

# Test Transcript Operations
class TestTranscriptOperations:
    def test_get_transcript_success(self, db, mock_supabase, sample_transcript):
        """Test successful transcript retrieval."""
        mock_response = MagicMock()
        mock_response.data = [sample_transcript.model_dump()]
        mock_supabase.execute.return_value = mock_response
        
        transcript = db.get_transcript(sample_transcript.youtube_video_id)
        assert isinstance(transcript, Transcript)
        assert transcript.youtube_video_id == sample_transcript.youtube_video_id
        assert transcript.text == sample_transcript.text
        assert transcript.source == sample_transcript.source
        assert transcript.storage_url == sample_transcript.storage_url

    def test_get_transcript_not_found(self, db, mock_supabase):
        """Test transcript not found scenario."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.execute.return_value = mock_response
        
        transcript = db.get_transcript("non_existent_id")
        assert transcript is None

    def test_get_transcript_database_error(self, db, mock_supabase):
        """Test database error handling."""
        mock_supabase.execute.side_effect = Exception("Database error")
        
        transcript = db.get_transcript("test_video_id")
        assert transcript is None

    def test_insert_transcript_success(self, db, mock_supabase, sample_transcript):
        """Test successful transcript insertion."""
        mock_response = MagicMock()
        mock_response.data = [sample_transcript.model_dump()]
        mock_supabase.execute.return_value = mock_response
        
        inserted_transcript = db.insert_transcript(sample_transcript)
        assert isinstance(inserted_transcript, Transcript)
        assert inserted_transcript.youtube_video_id == sample_transcript.youtube_video_id
        assert inserted_transcript.text == sample_transcript.text
        assert inserted_transcript.source == sample_transcript.source
        assert inserted_transcript.storage_url == sample_transcript.storage_url

    def test_insert_transcript_error(self, db, mock_supabase, sample_transcript):
        """Test transcript insertion error."""
        mock_supabase.execute.side_effect = Exception("Database error")
        
        inserted_transcript = db.insert_transcript(sample_transcript)
        assert inserted_transcript is None

# Test Podcast Operations
class TestPodcastOperations:
    def test_get_podcast_success(self, db, mock_supabase, sample_podcast):
        """Test successful podcast retrieval."""
        mock_response = MagicMock()
        mock_response.data = [sample_podcast.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        podcast = db.get_podcast(sample_podcast.id)
        assert isinstance(podcast, PodcastMetadata)
        assert podcast.id == sample_podcast.id
        assert podcast.user_id == sample_podcast.user_id
        assert podcast.source_id == sample_podcast.source_id
        assert podcast.storage_url == sample_podcast.storage_url
        assert podcast.title == sample_podcast.title

    def test_get_podcast_not_found(self, db, mock_supabase):
        """Test podcast not found scenario."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        podcast = db.get_podcast(uuid.uuid4())
        assert podcast is None

    def test_get_podcast_database_error(self, db, mock_supabase):
        """Test database error handling."""
        mock_response = MagicMock()
        mock_response.error = "Database error"
        mock_supabase.execute.return_value = mock_response
        
        podcast = db.get_podcast(uuid.uuid4())
        assert podcast is None

    def test_insert_podcast_success(self, db, mock_supabase, sample_podcast):
        """Test successful podcast insertion."""
        mock_response = MagicMock()
        mock_response.data = [sample_podcast.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        inserted_podcast = db.insert_podcast(sample_podcast)
        assert isinstance(inserted_podcast, PodcastMetadata)
        assert inserted_podcast.id == sample_podcast.id
        assert inserted_podcast.user_id == sample_podcast.user_id
        assert inserted_podcast.source_id == sample_podcast.source_id
        assert inserted_podcast.storage_url == sample_podcast.storage_url
        assert inserted_podcast.title == sample_podcast.title

    def test_insert_podcast_error(self, db, mock_supabase, sample_podcast):
        """Test podcast insertion error."""
        mock_response = MagicMock()
        mock_response.error = "Database error"
        mock_supabase.execute.return_value = mock_response
        
        inserted_podcast = db.insert_podcast(sample_podcast)
        assert inserted_podcast is None

    def test_get_user_podcasts_success(self, db, mock_supabase, sample_podcast):
        """Test successful retrieval of user podcasts."""
        mock_response = MagicMock()
        mock_response.data = [sample_podcast.model_dump()]
        mock_supabase.execute.return_value = mock_response
        
        podcasts = db.get_user_podcasts(sample_podcast.user_id)
        assert len(podcasts) == 1
        assert isinstance(podcasts[0], PodcastMetadata)
        assert podcasts[0].id == sample_podcast.id
        assert podcasts[0].user_id == sample_podcast.user_id

    def test_get_user_podcasts_error(self, db, mock_supabase):
        """Test error handling in user podcasts retrieval."""
        mock_supabase.execute.side_effect = Exception("Database error")
        
        podcasts = db.get_user_podcasts("test_user_id")
        assert len(podcasts) == 0

# Test Generation Job Operations
class TestGenerationJobOperations:
    def test_get_generation_job_success(self, db, mock_supabase, sample_generation_job):
        """Test successful generation job retrieval."""
        mock_response = MagicMock()
        mock_response.data = [sample_generation_job.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        job = db.get_generation_job(sample_generation_job.id)
        assert isinstance(job, GenerationJob)
        assert job.id == sample_generation_job.id
        assert job.user_id == sample_generation_job.user_id
        assert job.source_id == sample_generation_job.source_id
        assert job.status == sample_generation_job.status
        assert isinstance(job.config, JobConfig)

    def test_get_generation_job_not_found(self, db, mock_supabase):
        """Test generation job not found scenario."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        job = db.get_generation_job(uuid.uuid4())
        assert job is None

    def test_get_generation_job_database_error(self, db, mock_supabase):
        """Test database error handling."""
        mock_response = MagicMock()
        mock_response.error = "Database error"
        mock_supabase.execute.return_value = mock_response
        
        job = db.get_generation_job(uuid.uuid4())
        assert job is None

    def test_insert_generation_job_success(self, db, mock_supabase, sample_generation_job):
        """Test successful generation job insertion."""
        mock_response = MagicMock()
        mock_response.data = [sample_generation_job.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        inserted_job = db.insert_generation_job(sample_generation_job)
        assert isinstance(inserted_job, GenerationJob)
        assert inserted_job.id == sample_generation_job.id
        assert inserted_job.user_id == sample_generation_job.user_id
        assert inserted_job.source_id == sample_generation_job.source_id
        assert inserted_job.status == sample_generation_job.status
        assert isinstance(inserted_job.config, JobConfig)

    def test_insert_generation_job_error(self, db, mock_supabase, sample_generation_job):
        """Test generation job insertion error."""
        mock_response = MagicMock()
        mock_response.error = "Database error"
        mock_supabase.execute.return_value = mock_response
        
        inserted_job = db.insert_generation_job(sample_generation_job)
        assert inserted_job is None

    def test_update_generation_job_success(self, db, mock_supabase, sample_generation_job):
        """Test successful generation job update."""
        updated_data = {
            "status": JobStatus.PROCESSING,
            "started_at": datetime.now(timezone.utc)
        }
        mock_response = MagicMock()
        mock_response.data = [{**sample_generation_job.model_dump(), **updated_data}]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        updated_job = db.update_generation_job(sample_generation_job.id, updated_data)
        assert isinstance(updated_job, GenerationJob)
        assert updated_job.id == sample_generation_job.id
        assert updated_job.status == JobStatus.PROCESSING
        assert updated_job.started_at is not None

    def test_update_generation_job_not_found(self, db, mock_supabase):
        """Test update of non-existent generation job."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        updated_job = db.update_generation_job(uuid.uuid4(), {"status": JobStatus.PROCESSING})
        assert updated_job is None

    def test_update_generation_job_error(self, db, mock_supabase, sample_generation_job):
        """Test generation job update error."""
        mock_response = MagicMock()
        mock_response.error = "Database error"
        mock_supabase.execute.return_value = mock_response
        
        updated_job = db.update_generation_job(sample_generation_job.id, {"status": JobStatus.PROCESSING})
        assert updated_job is None

# Test Error Handling
class TestErrorHandling:
    def test_database_error(self, db, mock_supabase):
        """Test generic database error handling."""
        mock_supabase.execute.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseError) as exc_info:
            db.get_user("test_id")
        assert "Database error" in str(exc_info.value)

    def test_record_not_found_error(self, db, mock_supabase):
        """Test record not found error handling."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        with pytest.raises(RecordNotFoundError) as exc_info:
            db.get_user("non_existent_id")
        assert "User with id non_existent_id not found" == str(exc_info.value)

    def test_duplicate_record_error(self, db, mock_supabase, sample_user):
        """Test duplicate record error handling."""
        mock_response = MagicMock()
        mock_response.error = "duplicate key value violates unique constraint"
        mock_supabase.execute.return_value = mock_response
        
        with pytest.raises(DuplicateRecordError) as exc_info:
            db.insert_user(sample_user)
        assert f"User with email {sample_user.email} already exists" == str(exc_info.value)

# Test Query Monitoring
class TestQueryMonitoring:
    def test_query_monitoring(self, db, mock_supabase, sample_user):
        """Test query monitoring functionality."""
        mock_response = MagicMock()
        mock_response.data = [sample_user.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        # Reset query stats
        db._query_stats = {
            'total_queries': 0,
            'total_duration': 0.0,
            'slow_queries': [],
        }
        
        # Mock time.perf_counter to return consistent values
        with patch('time.perf_counter', side_effect=[0, 0.1]):  # 0.1s duration
            db.get_user(sample_user.id)
        
        stats = db.get_query_stats()
        assert stats['total_queries'] == 1
        assert stats['total_duration'] >= 0
        assert isinstance(stats['slow_queries'], list)

    def test_slow_query_monitoring(self, db, mock_supabase, sample_user):
        """Test slow query detection."""
        mock_response = MagicMock()
        mock_response.data = [sample_user.model_dump()]
        mock_response.error = None
        mock_supabase.execute.return_value = mock_response
        
        # Reset query stats
        db._query_stats = {
            'total_queries': 0,
            'total_duration': 0.0,
            'slow_queries': [],
        }
        
        # Mock time.perf_counter to simulate a slow query
        with patch('time.perf_counter', side_effect=[0, 2.0]):  # 2s duration
            db.get_user(sample_user.id)
        
        stats = db.get_query_stats()
        assert len(stats['slow_queries']) == 1
        assert stats['slow_queries'][0]['duration'] >= 1.0
