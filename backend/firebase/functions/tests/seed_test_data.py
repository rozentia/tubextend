import uuid
from datetime import datetime, timezone
from utils.database import Database
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

def seed_test_data():
    """Seed the test database with sample data for integration tests."""
    db = Database()
    
    # Create test user
    test_user = UserInfo(
        id="test_user_123",
        email="test@example.com",
        display_name="Test User",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.insert_user(test_user)
    
    # Create test channels
    test_channels = [
        ChannelInfo(
            youtube_channel_id="UCtest123",
            title="Test Channel 1",
            description="Test Description 1",
            channel_url="https://youtube.com/c/test1",
            created_at=datetime.now(timezone.utc)
        ),
        ChannelInfo(
            youtube_channel_id="UCtest456",
            title="Test Channel 2",
            description="Test Description 2",
            channel_url="https://youtube.com/c/test2",
            created_at=datetime.now(timezone.utc)
        )
    ]
    for channel in test_channels:
        db.insert_channel(channel)
    
    # Create test source
    test_source = SourceInfo(
        id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        user_id=test_user.id,
        source_type=SourceType.CHANNEL_COLLECTION,
        name="Test Source Collection",
        preferences={
            "tts_voice": "en-US-Neural2-F",
            "summarization_style": "detailed"
        },
        created_at=datetime.now(timezone.utc)
    )
    db.insert_source(test_source)
    
    # Link channels to source
    for channel in test_channels:
        source_channel = SourceChannelInfo(
            source_id=test_source.id,
            youtube_channel_id=channel.youtube_channel_id
        )
        db.insert_source_channel(source_channel)
    
    # Create test videos
    test_videos = [
        VideoMetadata(
            youtube_video_id="video123",
            title="Test Video 1",
            description="Test Video Description 1",
            url="https://youtube.com/watch?v=video123",
            channel_id=test_channels[0].youtube_channel_id,
            uploaded_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        ),
        VideoMetadata(
            youtube_video_id="video456",
            title="Test Video 2",
            description="Test Video Description 2",
            url="https://youtube.com/watch?v=video456",
            channel_id=test_channels[1].youtube_channel_id,
            uploaded_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
    ]
    db.bulk_insert_videos(test_videos)
    
    # Link videos to source
    for video in test_videos:
        source_video = SourceVideoInfo(
            source_id=test_source.id,
            youtube_video_id=video.youtube_video_id,
            processed_at=None  # Not processed yet
        )
        db.insert_source_video(source_video)
    
    # Create test transcripts
    test_transcript = Transcript(
        id=uuid.UUID("98765432-9876-5432-9876-987654321098"),
        youtube_video_id=test_videos[0].youtube_video_id,
        text="This is a test transcript content.",
        source=TranscriptSource.YOUTUBE_CAPTION,
        storage_url="gs://test-bucket/transcripts/video123.txt",
        created_at=datetime.now(timezone.utc)
    )
    db.insert_transcript(test_transcript)
    
    # Create test podcast
    test_podcast = PodcastMetadata(
        id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        user_id=test_user.id,
        source_id=test_source.id,
        transcript_id=test_transcript.id,
        storage_url="gs://test-bucket/podcasts/test_podcast.mp3",
        title="Test Podcast",
        created_at=datetime.now(timezone.utc)
    )
    db.insert_podcast(test_podcast)
    
    # Link videos to podcast
    podcast_video = PodcastVideoInfo(
        podcast_id=test_podcast.id,
        youtube_video_id=test_videos[0].youtube_video_id
    )
    db.insert_podcast_video(podcast_video)
    
    # Create test generation job
    test_job = GenerationJob(
        id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        user_id=test_user.id,
        source_id=test_source.id,
        status=JobStatus.QUEUED,
        config=JobConfig(
            model_parameters={"temperature": 0.7},
            processing_options={"format": "mp3"}
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.insert_generation_job(test_job)
    
    return {
        "user": test_user,
        "channels": test_channels,
        "source": test_source,
        "videos": test_videos,
        "transcript": test_transcript,
        "podcast": test_podcast,
        "job": test_job
    }

if __name__ == "__main__":
    seed_test_data() 