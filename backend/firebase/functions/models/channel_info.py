from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class ChannelInfo(BaseModel):
    """Channel information model."""
    
    model_config = ConfigDict(
        from_attributes=True
    )
    
    youtube_channel_id: str = Field(
        ..., 
        description="The YouTube Channel ID",
        json_schema_extra={"unique": True}
    )
    title: Optional[str] = Field(
        None, 
        description="Title of the YouTube channel"
    )
    description: Optional[str] = Field(
        None, 
        description="Description of the YouTube channel"
    )
    channel_url: Optional[str] = Field(
        None, 
        description="Url of the channel in youtube"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of channel creation"
    )
