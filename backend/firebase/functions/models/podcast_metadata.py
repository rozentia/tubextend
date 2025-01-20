from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid


class PodcastMetadata(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the podcast")
    user_id: str = Field(..., description="Firebase UID of the user who created the podcast")
    source_id: uuid.UUID = Field(..., description="ID of the source of the podcast")
    transcript_id: Optional[uuid.UUID] = Field(None, description="Transcript of the entire podcast")
    storage_url: str = Field(..., description="URL of the podcast audio in storage")
    title: Optional[str] = Field(None, description="Title of the podcast")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of podcast creation")
