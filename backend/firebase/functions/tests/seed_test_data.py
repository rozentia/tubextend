import uuid
from datetime import datetime, timezone, timedelta
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
    
    # Create test users
    test_user = UserInfo(
        id="test_user_123",
        email="test@example.com",
        display_name="Test User",
        refresh_token="1//test_refresh_token_123",
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.insert_user(test_user)
    
    test_user_no_oauth = UserInfo(
        id="test_user_no_oauth",
        email="test_no_oauth@example.com",
        display_name="Test User No OAuth",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.insert_user(test_user_no_oauth)
    
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
    
    inserted_channels = []
    for channel in test_channels:
        inserted_channel = db.insert_channel(channel)
        if inserted_channel:
            inserted_channels.append(inserted_channel)
    
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
    inserted_source = db.insert_source(test_source)
    
    # Create and insert test videos
    test_videos = [
        VideoMetadata(
            youtube_video_id=f"video{i}",
            title=f"Test Video {i}",
            description=f"Test Description {i}",
            channel_id=inserted_channels[0].youtube_channel_id,
            url=f"https://youtube.com/watch?v=video{i}",
            uploaded_at=datetime.now(timezone.utc)
        ) for i in range(1, 3)
    ]
    inserted_videos = db.bulk_insert_videos(test_videos)

    # Create test transcript
    test_transcript = Transcript(
        youtube_video_id=inserted_videos[0].youtube_video_id,
        content="Test transcript content",
        source=TranscriptSource.YOUTUBE_CAPTION,
        created_at=datetime.now(timezone.utc)
    )
    inserted_transcript = db.insert_transcript(test_transcript)

    # Create test podcast
    test_podcast = PodcastMetadata(
        id=uuid.UUID("98765432-9876-5432-9876-987654321098"),
        user_id=test_user.id,
        source_id=inserted_source.id,
        title="Test Podcast",
        storage_url="https://storage.example.com/test-podcast.mp3",
        created_at=datetime.now(timezone.utc)
    )
    inserted_podcast = db.insert_podcast(test_podcast)

    # Create test generation job
    test_job = GenerationJob(
        id=uuid.UUID("abcdef12-abcd-efab-abcd-abcdef123456"),
        user_id=test_user.id,
        source_id=inserted_source.id,
        status=JobStatus.QUEUED,
        config=JobConfig(
            tts_voice="en-US-Neural2-F",
            summarization_style="detailed"
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    inserted_job = db.insert_generation_job(test_job)

    # Link test entities
    db.link_channel_to_source(inserted_source.id, inserted_channels[0].youtube_channel_id)
    db.link_video_to_source(inserted_source.id, inserted_videos[0].youtube_video_id)
    
    # Create test data dictionary with all created entities
    test_data = {
        "user": test_user,
        "user_no_oauth": test_user_no_oauth,
        "channels": inserted_channels,
        "source": inserted_source,
        "videos": inserted_videos,
        "transcript": inserted_transcript,
        "podcast": inserted_podcast,
        "job": inserted_job
    }
    
    return test_data

if __name__ == "__main__":
    seed_test_data() 