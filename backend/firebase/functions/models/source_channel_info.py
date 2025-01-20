from pydantic import BaseModel, Field
import uuid

class SourceChannelInfo(BaseModel):
    source_id: uuid.UUID = Field(..., description="ID of the source")
    youtube_channel_id: str = Field(..., description="The YouTube Channel ID") 