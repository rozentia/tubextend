from pydantic import BaseModel, Field
import uuid

class PodcastVideoInfo(BaseModel):
    podcast_id: uuid.UUID = Field(..., description="ID of the podcast")
    youtube_video_id: str = Field(..., description="YouTube Video ID") 