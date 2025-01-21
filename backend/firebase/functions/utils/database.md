# Database Class Overview

Here's a comprehensive overview of the Database class's public methods, organized by functionality:

### User Management
```python
def get_user(self, user_id: FirebaseUID, columns: Optional[Set[str]] = None, use_cache: bool = True) -> UserInfo:
    """Retrieves user information by Firebase UID with optional column selection and caching"""

def insert_user(self, user: UserInfo) -> UserInfo:
    """Creates a new user record in the database"""

def update_user(self, user_id: str, updated_data: Dict[str, Any]) -> UserInfo:
    """Updates existing user information"""
```

### Channel Management
```python
def get_channel(self, youtube_channel_id: str) -> Optional[ChannelInfo]:
    """Retrieves channel information by YouTube channel ID"""

def insert_channel(self, channel: ChannelInfo) -> Optional[ChannelInfo]:
    """Creates a new channel record"""

def update_channel(self, youtube_channel_id: str, updated_data: Dict) -> Optional[ChannelInfo]:
    """Updates existing channel information"""

def bulk_insert_channels(self, channels: List[ChannelInfo]) -> List[ChannelInfo]:
    """Inserts multiple channels in a single operation"""
```

### Source Management
```python
def get_source(self, source_id: Union[uuid.UUID, str]) -> Optional[SourceInfo]:
    """Retrieves source information by ID"""

def get_sources_by_user(self, user_id: str, page: int = 1, page_size: int = 20) -> List[SourceInfo]:
    """Gets paginated list of sources for a user"""

def insert_source(self, source: SourceInfo) -> Optional[SourceInfo]:
    """Creates a new source record"""

def update_source(self, source_id: uuid.UUID, updated_data: Dict) -> Optional[SourceInfo]:
    """Updates existing source information"""

def delete_source(self, source_id: uuid.UUID) -> bool:
    """Deletes a source and its related records"""
```

### Source-Channel Relations
```python
def link_channel_to_source(self, source_id: uuid.UUID, youtube_channel_id: str) -> None:
    """Links a channel to a source"""

def unlink_channel_from_source(self, source_id: uuid.UUID, youtube_channel_id: str) -> None:
    """Removes channel from source"""

def get_source_channels(self, source_id: uuid.UUID) -> List[ChannelInfo]:
    """Gets all channels linked to a source"""
```

### Video Management
```python
def get_video(self, youtube_video_id: str) -> Optional[VideoMetadata]:
    """Retrieves video metadata by YouTube video ID"""

def insert_video(self, video: VideoMetadata) -> Optional[VideoMetadata]:
    """Creates a new video record"""

def bulk_insert_videos(self, videos: List[VideoMetadata]) -> List[VideoMetadata]:
    """Inserts multiple videos in a single operation"""
```

### Source-Video Relations
```python
def get_source_video(self, source_id: uuid.UUID, youtube_video_id: str) -> Optional[SourceVideoInfo]:
    """Retrieves source-video relationship information"""

def insert_source_video(self, source_video: SourceVideoInfo) -> Optional[SourceVideoInfo]:
    """Creates new source-video relationship"""

def get_source_videos(self, source_id: uuid.UUID) -> List[SourceVideoInfo]:
    """Gets all videos linked to a source"""

def link_video_to_source(self, source_id: uuid.UUID, youtube_video_id: str) -> None:
    """Links a video to a source"""

def mark_video_processed(self, source_id: uuid.UUID, youtube_video_id: str, processed_at: datetime) -> None:
    """Marks a video as processed for a source"""

def get_processed_videos(self, source_id: uuid.UUID) -> List[SourceVideoInfo]:
    """Gets all processed videos for a source"""

def get_unprocessed_videos(self, source_id: uuid.UUID) -> List[SourceVideoInfo]:
    """Gets all unprocessed videos for a source"""

def bulk_mark_videos_processed(self, videos: List[Tuple[uuid.UUID, str]], processed_at: datetime) -> None:
    """Marks multiple videos as processed in a single operation"""
```

### Transcript Management
```python
def get_transcript(self, youtube_video_id: str) -> Optional[Transcript]:
    """Retrieves transcript for a video"""

def insert_transcript(self, transcript: Transcript) -> Optional[Transcript]:
    """Creates a new transcript record"""
```

### Podcast Management
```python
def get_podcast(self, podcast_id: uuid.UUID) -> Optional[PodcastMetadata]:
    """Retrieves podcast metadata by ID"""

def insert_podcast(self, podcast: PodcastMetadata) -> Optional[PodcastMetadata]:
    """Creates a new podcast record"""

def get_user_podcasts(self, user_id: str) -> List[PodcastMetadata]:
    """Gets all podcasts for a user"""
```

### Podcast-Video Relations
```python
def insert_podcast_video(self, podcast_video: PodcastVideoInfo) -> Optional[PodcastVideoInfo]:
    """Creates new podcast-video relationship"""

def get_podcast_videos(self, podcast_id: uuid.UUID) -> List[PodcastVideoInfo]:
    """Gets all videos linked to a podcast"""

def link_video_to_podcast(self, podcast_id: uuid.UUID, youtube_video_id: str) -> None:
    """Links a video to a podcast"""
```

### Generation Job Management
```python
def get_generation_job(self, job_id: uuid.UUID) -> Optional[GenerationJob]:
    """Retrieves generation job information"""

def insert_generation_job(self, job: GenerationJob) -> Optional[GenerationJob]:
    """Creates a new generation job"""

def update_generation_job(self, job_id: uuid.UUID, updated_data: Dict) -> Optional[GenerationJob]:
    """Updates existing generation job information"""
```

### System Monitoring
```python
def get_query_stats(self) -> Dict[str, Any]:
    """Retrieves database query statistics including performance metrics"""
```

Each method includes error handling and logging, and many support caching for improved performance. The class uses type hints throughout and returns Pydantic models for structured data handling.

