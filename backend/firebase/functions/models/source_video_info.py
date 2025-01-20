from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class SourceVideoInfo(BaseModel):
    source_id: uuid.UUID = Field(..., description="ID of the source")
    youtube_video_id: str = Field(..., description="YouTube Video ID")
    processed_at: Optional[datetime] = Field(None, description="Timestamp when the video was processed") 