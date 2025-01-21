# **Models Documentation**

## User-Related Models

```python
class UserInfo(BaseModel):
    id: str                     # Firebase UID
    email: EmailStr             # User's email address
    display_name: Optional[str] # User's display name
    created_at: datetime        # Creation timestamp
    updated_at: datetime        # Last update timestamp
```

## Channel-Related Models

```python
class ChannelInfo(BaseModel):
    youtube_channel_id: str     # Unique YouTube channel ID
    title: Optional[str]        # Channel title
    description: Optional[str]  # Channel description
    channel_url: Optional[str]  # YouTube channel URL
    created_at: datetime        # Record creation timestamp
```

## Source-Related Models

```python
class SourceType(str, Enum):
    CHANNEL_COLLECTION = 'channel_collection'
    PLAYLIST = 'playlist'

class SourcePreferences(BaseModel):
    tts_voice: Optional[str]
    summarization_style: Optional[str]
    schedule: Optional[Dict[str, Any]]

class SourceInfo(BaseModel):
    id: uuid.UUID              # Unique source identifier
    user_id: str               # Owner's Firebase UID
    source_type: SourceType    # Type (channel_collection/playlist)
    name: str                  # Source name
    youtube_playlist_id: Optional[str]  # YouTube playlist ID if applicable
    preferences: Dict          # Processing preferences (JSONB)
    last_processed_at: Optional[datetime]  # Last processing timestamp
    created_at: datetime       # Creation timestamp
```

## Video-Related Models

```python
class VideoMetadata(BaseModel):
    youtube_video_id: str      # Unique YouTube video ID
    title: Optional[str]       # Video title
    description: Optional[str] # Video description
    url: Optional[HttpUrl]     # Video URL
    channel_id: str           # Source channel ID
    uploaded_at: Optional[datetime]  # YouTube upload timestamp
    created_at: datetime      # Record creation timestamp
```

## Transcript-Related Models

```python
class TranscriptSource(str, Enum):
    YOUTUBE_CAPTION = 'youtube_caption'
    WHISPER = 'whisper'

class Transcript(BaseModel):
    id: uuid.UUID             # Unique transcript identifier
    youtube_video_id: str     # Associated video ID
    text: Optional[str]       # Full transcript text
    source: Optional[TranscriptSource]  # Transcript source
    storage_url: Optional[str]  # Storage location
    created_at: datetime      # Creation timestamp
```

## Podcast-Related Models

```python
class PodcastMetadata(BaseModel):
    id: uuid.UUID             # Unique podcast identifier
    user_id: str              # Creator's Firebase UID
    source_id: uuid.UUID      # Source identifier
    transcript_id: Optional[uuid.UUID]  # Podcast transcript ID
    storage_url: str          # Audio file location
    title: Optional[str]      # Podcast title
    created_at: datetime      # Creation timestamp
```

## Job-Related Models

```python
class JobStatus(str, Enum):
    QUEUED = 'QUEUED'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class JobConfig(BaseModel):
    model_parameters: Optional[Dict[str, Any]]
    processing_options: Optional[Dict[str, Any]]

class GenerationJob(BaseModel):
    id: uuid.UUID             # Unique job identifier
    user_id: str              # Owner's Firebase UID
    source_id: Optional[uuid.UUID]  # Related source ID
    status: JobStatus         # Current job status
    config: JobConfig         # Job configuration
    error_message: Optional[str]  # Error details if failed
    created_at: datetime      # Creation timestamp
    updated_at: datetime      # Last update timestamp
    started_at: Optional[datetime]  # Processing start time
    finished_at: Optional[datetime] # Processing end time
```

## Junction/Relationship Models

```python
class SourceChannelInfo(BaseModel):
    source_id: uuid.UUID      # Source identifier
    youtube_channel_id: str   # YouTube channel ID

class SourceVideoInfo(BaseModel):
    source_id: uuid.UUID      # Source identifier
    youtube_video_id: str     # YouTube video ID
    processed_at: Optional[datetime]  # Processing timestamp

class PodcastVideoInfo(BaseModel):
    podcast_id: uuid.UUID     # Podcast identifier
    youtube_video_id: str     # YouTube video ID
```

## Key Features of the Models

1. All models use Pydantic's BaseModel for validation
2. Most models include creation timestamps
3. Extensive use of Optional fields for flexibility
4. UUID-based identifiers for internal entities
5. String-based IDs for external references (YouTube)
6. Enum classes for constrained choice fields
7. ConfigDict for model configuration
8. Field validators where necessary
9. Detailed field descriptions
10. Type hints throughout

The models are designed to:

- Maintain referential integrity
- Support JSON serialization
- Provide type safety
- Enable validation
- Support database operations
- Handle external API integration
- Track temporal information
- Manage relationships between entities

These models form a complete data structure that supports all the system's requirements for content management, processing, and delivery.
