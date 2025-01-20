from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Any, Optional, Dict
import uuid

class JobStatus(str, Enum):
    QUEUED = 'QUEUED'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class JobConfig(BaseModel):
    model_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    processing_options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class GenerationJob(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the job")
    user_id: str = Field(..., description="Firebase UID of the user who started the job")
    source_id: Optional[uuid.UUID] = Field(None, description="ID of the source related to the job")
    status: JobStatus = Field(..., description="Status of the job (QUEUED, PROCESSING, COMPLETED, FAILED)")
    config: JobConfig = Field(default_factory=JobConfig, description="Configuration details for the job")
    error_message: Optional[str] = Field(None, description="Error message if the job failed")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of job creation")
    updated_at: datetime = Field(default_factory=datetime.now, description="Timestamp of job update")
    started_at: Optional[datetime] = Field(None, description="Timestamp of when the job started")
    finished_at: Optional[datetime] = Field(None, description="Timestamp of when the job finished") 

    @field_validator('status')
    def validate_status(cls, v):
        if v not in [JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.COMPLETED, JobStatus.FAILED]:
            raise ValueError(f'Invalid job status: {v}')
        return v