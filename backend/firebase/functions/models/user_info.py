from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime, timezone
from typing import Optional


class UserInfo(BaseModel):
    """User information model."""
    
    model_config = ConfigDict(
        from_attributes=True  # Replaces the deprecated Config class
    )
    
    id: str = Field(..., description="Firebase UID", min_length=1, max_length=255)
    email: EmailStr = Field(..., description="User's email address")
    display_name: Optional[str] = Field(None, description="User's display name", max_length=255)
    refresh_token: Optional[str] = Field(None, description="YouTube OAuth refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration timestamp")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of user creation")
    updated_at: datetime = Field(default_factory=datetime.now, description="Timestamp of user update")

    def needs_token_refresh(self) -> bool:
        """Check if the token needs to be refreshed"""
        if not self.token_expires_at:
            return True
        # Ensure we're comparing timezone-aware datetimes
        now = datetime.now(timezone.utc)
        # Refresh if token expires in less than 5 minutes
        return (self.token_expires_at - now).total_seconds() < 300 