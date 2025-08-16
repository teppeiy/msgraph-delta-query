"""Test configuration and fixtures."""

import pytest
import logging
import asyncio
from typing import Generator

# Load environment variables for all tests
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("🔑 Loaded environment variables from .env file for tests")
except ImportError:
    print("ℹ️  python-dotenv not available, using system environment variables")


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Set up logging for tests
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def cleanup_deltalinks():
    """Clean up any deltalinks folder created during tests."""
    import os
    import shutil

    yield  # Run the test

    # Clean up after test
    if os.path.exists("deltalinks"):
        try:
            shutil.rmtree("deltalinks")
        except Exception:
            pass  # Best effort cleanup
