from datetime import datetime, timezone, timedelta
import pytest
from models.user_info import UserInfo

class TestDatabaseOAuth:
    """Integration tests for Database OAuth operations."""

    def test_user_oauth_operations(self, db, test_data):
        """Test user OAuth token operations."""
        # Get fresh user data
        user = db.get_user(test_data["user"].id)
        assert user is not None
        assert user.refresh_token == test_data["user"].refresh_token
        
        # Test update token
        new_token = "1//new_refresh_token_456"
        new_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Update using the update_user method instead of update_user_token
        updated_data = {
            "refresh_token": new_token,
            "token_expires_at": new_expires,
            "updated_at": datetime.now(timezone.utc)
        }
        updated_user = db.update_user(user.id, updated_data)
        
        assert updated_user is not None
        assert updated_user.refresh_token == new_token
        assert updated_user.token_expires_at == new_expires

    def test_user_token_validation(self, db, test_data):
        """Test user token validation methods."""
        # Test user with valid token
        user = db.get_user(test_data["user"].id)
        
        # Update token expiration to ensure it's valid
        new_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.update_user(user.id, {
            "token_expires_at": new_expires,
            "updated_at": datetime.now(timezone.utc)
        })
        
        # Fetch updated user
        updated_user = db.get_user(test_data["user"].id)
        assert updated_user.needs_token_refresh() is False

        # Test user without token
        no_oauth_user = db.get_user(test_data["user_no_oauth"].id)
        assert no_oauth_user.needs_token_refresh() is True

    def test_update_user_token_error_handling(self, db):
        """Test error handling for token updates."""
        # Test updating non-existent user
        result = db.update_user_token(
            user_id="non_existent_user",
            refresh_token="test_token",
            expires_at=datetime.now(timezone.utc)
        )
        assert result is None
