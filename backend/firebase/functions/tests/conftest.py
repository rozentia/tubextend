import pytest
from tests.seed_test_data import seed_test_data
from tests.cleanup_test_data import cleanup_test_data
from utils.database import Database
from unittest.mock import patch
import os

@pytest.fixture(scope="session")
def db():
    """Fixture to create database instance once per test session."""
    return Database()

@pytest.fixture(scope="session")
def test_data(db):
    """Fixture to provide test data for the entire test session."""
    # Clean any existing test data first
    cleanup_test_data()
    
    # Seed fresh test data
    data = seed_test_data()
    
    # Cleanup after all tests are done
    yield data
    cleanup_test_data()

@pytest.fixture(autouse=True)
def reset_test_data(db, test_data):
    """Reset test data to initial state before each test."""
    # No cleanup at start - we want to keep the session test data
    yield
    
    # After each test, restore the test data to its original state
    # by updating the records instead of deleting and recreating
    db.update_user(test_data["user"].id, {
        "refresh_token": test_data["user"].refresh_token,
        "token_expires_at": test_data["user"].token_expires_at
    })
    
    # Reset source to original state
    if test_data["source"]:
        db.update_source(test_data["source"].id, {"preferences": test_data["source"].preferences})

def pytest_sessionstart(session):
    """Called before test session starts."""
    # Clean up any existing test data first
    cleanup_test_data()

def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    # Clean up test data after tests
    cleanup_test_data()

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment variables for YouTube API."""
    # Store original env vars
    original_vars = {
        'YOUTUBE_CLIENT_ID': os.getenv('YOUTUBE_CLIENT_ID'),
        'YOUTUBE_CLIENT_SECRET': os.getenv('YOUTUBE_CLIENT_KEY'),
        'YOUTUBE_API_KEY': os.getenv('YOUTUBE_API_KEY'),
        'YOUTUBE_REFRESH_TOKEN': os.getenv('YOUTUBE_REFRESH_TOKEN')
    }
    
    # Set test env vars
    os.environ['YOUTUBE_CLIENT_ID'] = 'test_client_id'
    os.environ['YOUTUBE_CLIENT_KEY'] = 'test_client_secret'
    os.environ['YOUTUBE_API_KEY'] = 'test_api_key'
    os.environ['YOUTUBE_REFRESH_TOKEN'] = 'test_refresh_token'
    
    yield
    
    # Restore original env vars
    for key, value in original_vars.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None) 