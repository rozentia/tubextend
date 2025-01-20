from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid

class TranscriptSource(str, Enum):
    YOUTUBE_CAPTION = 'youtube_caption'
    WHISPER = 'whisper'

class Transcript(BaseModel):
    """Transcript model."""
    
    model_config = ConfigDict(
        from_attributes=True
    )
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for the transcript"
    )
    youtube_video_id: str = Field(
        ..., 
        description="The YouTube video id",
        json_schema_extra={"unique": True}
    )
    text: Optional[str] = Field(
        None,
        description="The full text of the transcript"
    )
    source: Optional[TranscriptSource] = Field(
        None,
        description="Source of the transcript (e.g., youtube_caption)"
    )
    storage_url: Optional[str] = Field(
        None,
        description="URL of the transcript file in storage"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of transcript creation"
    )