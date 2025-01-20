import pytest
from tests.seed_test_data import seed_test_data
from tests.cleanup_test_data import cleanup_test_data

def pytest_sessionstart(session):
    """Called before test session starts."""
    # Clean up any existing test data first
    cleanup_test_data()

def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    # Clean up test data after tests
    cleanup_test_data() 