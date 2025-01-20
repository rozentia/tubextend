from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional


class UserInfo(BaseModel):
    """User information model."""
    
    model_config = ConfigDict(
        from_attributes=True  # Replaces the deprecated Config class
    )
    
    id: str = Field(..., description="Firebase UID", min_length=1, max_length=255)
    email: EmailStr = Field(..., description="User's email address")
    display_name: Optional[str] = Field(None, description="User's display name", max_length=255)
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of user creation")
    updated_at: datetime = Field(default_factory=datetime.now, description="Timestamp of user update") 