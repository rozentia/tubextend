from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional


class VideoMetadata(BaseModel):
    """Video metadata model."""
    
    model_config = ConfigDict(
        from_attributes=True,  # Replaces the deprecated Config class
        json_schema_extra={
            "example": {
                "youtube_video_id": "dQw4w9WgXcQ",
                "title": "Sample Video Title",
                "description": "This is a sample video description",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "channel_id": "UC38IQsAvIsxxjztdMZQtwHA"
            }
        }
    )
    
    youtube_video_id: str = Field(
        ..., 
        description="The YouTube video ID",
        min_length=1,
        max_length=255,
        json_schema_extra={"unique": True}  # Replaces the deprecated unique parameter
    )
    title: Optional[str] = Field(
        None,
        description="Title of the video",
        max_length=500
    )
    description: Optional[str] = Field(
        None,
        description="Description of the video",
        max_length=5000
    )
    url: Optional[HttpUrl] = Field(
        None,
        description="URL of the video"
    )
    channel_id: str = Field(
        ...,
        description="The YouTube channel id of the source channel",
        min_length=1,
        max_length=255
    )
    uploaded_at: Optional[datetime] = Field(
        None,
        description="Timestamp of video upload"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of video creation"
    )
