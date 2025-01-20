from utils.database import Database

def cleanup_test_data():
    """Clean up all test data from the database."""
    db = Database()
    
    # Get test user ID
    test_user_id = "test_user_123"
    
    try:
        # Delete in reverse order of dependencies
        
        # Delete all podcast_videos for test user's podcasts
        user_podcasts = db.get_user_podcasts(test_user_id)
        for podcast in user_podcasts:
            db.client.table('podcast_videos').delete().eq('podcast_id', podcast.id).execute()
        
        # Delete source_videos and source_channels for test user's sources
        sources = db.get_sources_by_user(test_user_id)
        for source in sources:
            # Delete source_videos first
            db.client.table('source_videos').delete().eq('source_id', source.id).execute()
            # Then delete source_channels
            db.client.table('source_channels').delete().eq('source_id', source.id).execute()
        
        # Delete all podcasts for test user
        for podcast in user_podcasts:
            db.client.table('podcasts').delete().eq('id', podcast.id).execute()
        
        # Delete all generation jobs for test user
        db.client.table('generation_jobs').delete().eq('user_id', test_user_id).execute()
        
        # Delete test videos and their transcripts
        test_video_ids = ["video123", "video456"]
        # Add bulk inserted video IDs
        test_video_ids.extend([f"new_video_{i}" for i in range(3)])
        for video_id in test_video_ids:
            # Delete transcript first (if exists)
            db.client.table('transcripts').delete().eq('youtube_video_id', video_id).execute()
            # Then delete video
            db.client.table('videos').delete().eq('youtube_video_id', video_id).execute()
        
        # Delete all sources for test user
        for source in sources:
            db.client.table('sources').delete().eq('id', source.id).execute()
        
        # Delete test channels and bulk inserted channels
        test_channel_ids = ["UCtest123", "UCtest456"]
        # Add bulk inserted channel IDs
        test_channel_ids.extend([f"bulk_channel_{i}" for i in range(3)])
        # Add bulk inserted channels from test_bulk_operations
        test_channel_ids.extend([f"bulk_inserted_channel_{i}" for i in range(3)])
        
        for channel_id in test_channel_ids:
            db.client.table('channels').delete().eq('youtube_channel_id', channel_id).execute()
        
        # Finally, delete test user
        db.client.table('users').delete().eq('id', test_user_id).execute()
        
        print("Successfully cleaned up all test data")
        
    except Exception as e:
        print(f"Error cleaning up test data: {str(e)}")
        raise

if __name__ == "__main__":
    cleanup_test_data() 