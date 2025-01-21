import pytest
import uuid
from datetime import datetime, timezone
from utils.database import (
    Database, DatabaseError, RecordNotFoundError, DuplicateRecordError
)
from models.user_info import UserInfo
from models.channel_info import ChannelInfo
from models.source_info import SourceInfo, SourceType
from models.video_metadata import VideoMetadata
from models.transcript import Transcript, TranscriptSource
from models.podcast_metadata import PodcastMetadata
from models.generation_job import GenerationJob, JobStatus, JobConfig
from tests.seed_test_data import seed_test_data
from unittest.mock import patch

@pytest.fixture(scope="session")
def test_data():
    """Fixture to seed and return test data once per test session."""
    return seed_test_data()

@pytest.fixture(scope="session")
def db():
    """Fixture to create database instance once per test session."""
    return Database()

class TestDatabaseIntegration:
    """Integration tests for Database class using real Supabase instance."""
    
    def test_user_operations(self, db, test_data):
        """Test user CRUD operations."""
        # Test get user
        user = db.get_user(test_data["user"].id)
        assert user.id == test_data["user"].id
        assert user.email == test_data["user"].email
        assert user.display_name == test_data["user"].display_name
        
        # Test update user
        updated_name = "Updated Test User"
        updated_user = db.update_user(user.id, {"display_name": updated_name})
        assert updated_user.display_name == updated_name
        
        # Test duplicate user error
        with pytest.raises(DuplicateRecordError):
            db.insert_user(test_data["user"])
            
        # Test user not found
        with pytest.raises(RecordNotFoundError):
            db.get_user("nonexistent_user")
    
    def test_channel_operations(self, db, test_data):
        """Test channel operations."""
        # Test get channel
        channel = db.get_channel(test_data["channels"][0].youtube_channel_id)
        assert channel.youtube_channel_id == test_data["channels"][0].youtube_channel_id
        assert channel.title == test_data["channels"][0].title
        
        # Test channel not found
        assert db.get_channel("nonexistent_channel") is None
    
    def test_source_operations(self, db, test_data):
        """Test source operations."""
        # Test get source
        source = db.get_source(test_data["source"].id)
        assert source.id == test_data["source"].id
        assert source.name == test_data["source"].name
        assert source.source_type == test_data["source"].source_type
        
        # Test get sources by user
        sources = db.get_sources_by_user(test_data["user"].id)
        assert len(sources) > 0
        assert any(s.id == test_data["source"].id for s in sources)

        # Create new source for subsequent tests
        new_source = SourceInfo(
            id=uuid.uuid4(),
            user_id=test_data["user"].id,
            source_type=SourceType.CHANNEL_COLLECTION,
            name="New Test Source",
            preferences={}
        )
        db.insert_source(new_source)
        test_data["source"] = new_source
    
    def test_video_operations(self, db, test_data):
        """Test video operations."""
        # Verify test data exists
        assert test_data["videos"] is not None
        assert len(test_data["videos"]) > 0
        assert test_data["videos"][0].youtube_video_id is not None, f"YouTube video ID is missing for {test_data['videos'][0].youtube_video_id}"
        
        # Test get video
        video = db.get_video(test_data["videos"][0].youtube_video_id)
        assert video is not None, f"Video with ID {test_data['videos'][0].youtube_video_id} not found…"
        assert video.youtube_video_id == test_data["videos"][0].youtube_video_id, f"Video ID mismatch for {test_data['videos'][0].youtube_video_id}"
        assert video.title == test_data["videos"][0].title, f"Title mismatch for {test_data['videos'][0].youtube_video_id}"
        
        # Test bulk insert videos
        new_videos = [
            VideoMetadata(
                youtube_video_id=f"new_video_{i}",
                title=f"New Test Video {i}",
                description=f"New Test Description {i}",
                channel_id=test_data["channels"][0].youtube_channel_id,
                uploaded_at=datetime.now(timezone.utc)
            ) for i in range(3)
        ]
        inserted_videos = db.bulk_insert_videos(new_videos)
        assert len(inserted_videos) == len(new_videos)
    
    def test_transcript_operations(self, db, test_data):
        """Test transcript operations."""
        # Test get transcript
        transcript = db.get_transcript(test_data["transcript"].youtube_video_id)
        assert transcript.youtube_video_id == test_data["transcript"].youtube_video_id
        assert transcript.text == test_data["transcript"].text
        
        # Test transcript not found
        assert db.get_transcript("nonexistent_video") is None
    
    def test_podcast_operations(self, db, test_data):
        """Test podcast operations."""
        # Test get podcast
        podcast = db.get_podcast(test_data["podcast"].id)
        assert podcast.id == test_data["podcast"].id
        assert podcast.title == test_data["podcast"].title
        
        # Test get user podcasts
        user_podcasts = db.get_user_podcasts(test_data["user"].id)
        assert len(user_podcasts) > 0
        assert any(p.id == test_data["podcast"].id for p in user_podcasts)
    
    def test_generation_job_operations(self, db, test_data):
        """Test generation job operations."""
        # Test get job
        job = db.get_generation_job(test_data["job"].id)
        assert job.id == test_data["job"].id
        assert job.status == test_data["job"].status
        
        # Test update job
        updated_status = JobStatus.PROCESSING
        updated_job = db.update_generation_job(
            job.id,
            {
                "status": updated_status,
                "started_at": datetime.now(timezone.utc)
            }
        )
        assert updated_job.status == updated_status
        assert updated_job.started_at is not None
    
    def test_query_monitoring(self, db, test_data):
        """Test query monitoring functionality."""
        # Reset query stats before test
        db._query_stats = {
            'total_queries': 0,
            'total_duration': 0.0,
            'slow_queries': []
        }
        
        # Perform some operations to generate stats
        try:
            db.get_user(test_data["user"].id)
        except DatabaseError:
            pass  # We're testing monitoring, not the query success
        
        try:
            db.get_channel(test_data["channels"][0].youtube_channel_id)
        except DatabaseError:
            pass
        
        # Get query stats
        stats = db.get_query_stats()
        assert stats["total_queries"] > 0, "No queries were counted"
        assert stats["total_duration"] >= 0, "Duration should be non-negative"
        assert "avg_duration" in stats, "Average duration not calculated"
        assert "slow_queries" in stats, "Slow queries not tracked"

    def test_slow_query_monitoring(self, db, test_data):
        """Test slow query detection."""
        # Reset query stats
        db._query_stats = {
            'total_queries': 0,
            'total_duration': 0.0,
            'slow_queries': [],
        }
        
        # Mock time.perf_counter to simulate a slow query
        with patch('time.perf_counter', side_effect=[0, 2.0]):  # 2s duration
            try:
                db.get_user(test_data["user"].id)
            except DatabaseError:
                pass  # We're testing monitoring, not the query success
        
        stats = db.get_query_stats()
        assert len(stats['slow_queries']) == 1, "Slow query not detected"
        assert stats['slow_queries'][0]['duration'] >= 1.0, "Slow query duration incorrect"

    def test_source_channel_operations(self, db, test_data):
        """Test source channel linking operations."""
        # Test linking channel to source
        db.link_channel_to_source(test_data["source"].id, test_data["channels"][0].youtube_channel_id)
        
        # Test get channels by source
        source_channels = db.get_source_channels(test_data["source"].id)
        assert len(source_channels) > 0
        assert any(c.youtube_channel_id == test_data["channels"][0].youtube_channel_id for c in source_channels)
        
        # Test unlinking channel from source
        db.unlink_channel_from_source(test_data["source"].id, test_data["channels"][0].youtube_channel_id)
        updated_channels = db.get_source_channels(test_data["source"].id)
        assert len(updated_channels) == 0

    def test_source_video_operations(self, db, test_data):
        """Test source video linking and processing operations."""
        # Test linking video to source
        db.link_video_to_source(test_data["source"].id, test_data["videos"][0].youtube_video_id)
        
        # Test get videos by source
        source_videos = db.get_source_videos(test_data["source"].id)
        assert len(source_videos) > 0
        assert any(v.youtube_video_id == test_data["videos"][0].youtube_video_id for v in source_videos)
        
        # Test marking video as processed
        db.mark_video_processed(
            test_data["source"].id,
            test_data["videos"][0].youtube_video_id,
            datetime.now(timezone.utc)
        )
        processed_videos = db.get_processed_videos(test_data["source"].id)
        assert len(processed_videos) > 0
        
        # Test get unprocessed videos
        unprocessed = db.get_unprocessed_videos(test_data["source"].id)
        assert all(v.processed_at is None for v in unprocessed)

    def test_podcast_video_operations(self, db, test_data):
        """Test podcast video linking operations."""
        # Test linking video to podcast
        db.link_video_to_podcast(test_data["podcast"].id, test_data["videos"][0].youtube_video_id)
        
        # Test get videos by podcast
        podcast_videos = db.get_podcast_videos(test_data["podcast"].id)
        assert len(podcast_videos) > 0
        assert any(v.youtube_video_id == test_data["videos"][0].youtube_video_id for v in podcast_videos)

    def test_bulk_operations(self, db, test_data):
        """Test bulk insert and update operations."""
        # Test bulk insert channels
        new_channels = [
            ChannelInfo(
                youtube_channel_id=f"bulk_inserted_channel_{i}",
                title=f"Bulk Channel {i}"
            ) for i in range(3)
        ]
        inserted_channels = db.bulk_insert_channels(new_channels)
        assert len(inserted_channels) == len(new_channels), \
            f"Expected {len(new_channels)} channels to be inserted, got {len(inserted_channels)}"
        
        # Get initial count of processed videos (there is 1 because of the test data)
        initial_processed = db.get_processed_videos(test_data["source"].id)
        assert len(initial_processed) == 1, \
            f"Expected 1 processed videos, got {len(initial_processed)}"
        initial_count = len(initial_processed) - 1 #! Subtract the test data video
        
        # Test bulk update source videos
        videos_to_update = [
            (test_data["source"].id, v.youtube_video_id)
            for v in test_data["videos"][:2]
        ]
        
        # First, ensure videos are linked to source
        for source_id, video_id in videos_to_update:
            db.link_video_to_source(source_id, video_id)

        # Then mark them as processed
        processed_time = datetime.now(timezone.utc)
        db.bulk_mark_videos_processed(videos_to_update, processed_time)
        
        # Verify the videos were processed
        processed = db.get_processed_videos(test_data["source"].id)
        expected_count = initial_count + len(videos_to_update)
        assert len(processed) == expected_count, \
            f"Expected {expected_count} processed videos, got {len(processed)}"
        
        # Verify the specific videos were processed
        processed_video_ids = {v.youtube_video_id for v in processed}
        expected_video_ids = {video_id for _, video_id in videos_to_update}
        assert expected_video_ids.issubset(processed_video_ids), \
            f"Not all expected videos were processed. Missing: {expected_video_ids - processed_video_ids}"

    def test_source_preferences(self, db, test_data):
        """Test source preferences operations."""
        # Test updating source preferences
        new_preferences = {
            "tts_voice": "voice_1",
            "summarization_style": "concise",
            "schedule": {"frequency": "daily"}
        }
        updated_source = db.update_source(
            test_data["source"].id,
            {"preferences": new_preferences}
        )
        assert updated_source.preferences == new_preferences

    def test_error_handling(self, db, test_data):
        """Test error handling for invalid operations."""
        # Test invalid UUID format
        with pytest.raises(DatabaseError, match="Invalid UUID format"):
            db.get_source("invalid-uuid")
            
        # Test invalid foreign key
        with pytest.raises(DatabaseError):
            db.link_channel_to_source(
                uuid.uuid4(),  # Non-existent source
                "non-existent-channel"
            )
            
        # Test duplicate unique constraint
        with pytest.raises(DuplicateRecordError):
            # Create a duplicate channel with same ID
            duplicate_channel = ChannelInfo(
                youtube_channel_id=test_data["channels"][0].youtube_channel_id,
                title="Duplicate Channel"
            )
            db.insert_channel(duplicate_channel) 