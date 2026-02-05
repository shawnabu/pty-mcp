"""Pytest configuration and fixtures."""

import pytest
import asyncio


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
