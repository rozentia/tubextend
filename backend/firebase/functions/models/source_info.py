from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Any, Optional, Dict
import uuid

class SourceType(str, Enum):
    CHANNEL_COLLECTION = 'channel_collection'
    PLAYLIST = 'playlist'

class SourcePreferences(BaseModel):
    tts_voice: Optional[str]
    summarization_style: Optional[str]
    schedule: Optional[Dict[str, Any]]

class SourceInfo(BaseModel):
    """Source information model."""
    
    model_config = ConfigDict(
        from_attributes=True
    )
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for the source",
        json_schema_extra={"unique": True}
    )
    user_id: str = Field(
        ...,
        description="ID of the user owning the source"
    )
    source_type: SourceType = Field(
        ...,
        description="Type of source (channel_collection, playlist)"
    )
    name: str = Field(
        ...,
        description="Name of the source"
    )
    youtube_playlist_id: Optional[str] = Field(
        None,
        description="YouTube playlist ID (if source is a playlist)"
    )
    preferences: Dict = Field(
        default_factory=dict,
        description="Preferences for processing (JSONB)"
    )
    last_processed_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the last processing"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of source creation"
    )

    @field_validator('source_type')
    def validate_source_type(cls, v):
        if v not in [SourceType.CHANNEL_COLLECTION, SourceType.PLAYLIST]:
            raise ValueError(f'Invalid source type: {v}')
        return v 