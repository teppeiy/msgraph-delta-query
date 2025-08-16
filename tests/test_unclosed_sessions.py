"""Test cases for unclosed session bug fixes."""

import pytest
import asyncio
import warnings
from unittest.mock import Mock, AsyncMock, patch
from contextlib import contextmanager
from typing import List

from msgraph_delta_query.client import AsyncDeltaQueryClient
from msgraph_delta_query.storage import (
    LocalFileDeltaLinkStorage
)


class ResourceWarningCapture:
    """Capture ResourceWarnings to test for unclosed sessions."""

    def __init__(self):
        self.warnings: List[warnings.WarningMessage] = []

    def warning_handler(
        self, message, category, filename, lineno, file=None, line=None
    ):
        """Custom warning handler to capture warnings."""
        if category == ResourceWarning and "Unclosed" in str(message):
            self.warnings.append(
                warnings.WarningMessage(category, message, filename, lineno, file, line)
            )


@contextmanager
def capture_resource_warnings():
    """Context manager to capture ResourceWarnings about unclosed sessions."""
    capture = ResourceWarningCapture()

    # Set up warning capture
    old_showwarning = warnings.showwarning
    warnings.showwarning = capture.warning_handler
    warnings.filterwarnings("default", category=ResourceWarning)

    try:
        yield capture
    finally:
        warnings.showwarning = old_showwarning


@pytest.fixture
def mock_storage():
    """Provide a mock storage instance that has close method."""
    storage = Mock()
    storage.close = AsyncMock()
    return storage


class TestUnclosedSessionBugFixes:
    """Test cases for the unclosed session bug fixes."""

    @pytest.mark.asyncio
    async def test_explicit_close_prevents_unclosed_sessions(self, mock_storage):
        """Test that calling close() explicitly prevents unclosed session warnings."""
        with capture_resource_warnings() as capture:
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Explicitly close the client
            await client.close()

            # Allow some time for any delayed warnings
            await asyncio.sleep(0.1)

        # Check that no unclosed session warnings were captured
        unclosed_warnings = [
            w for w in capture.warnings if "client session" in str(w.message).lower()
        ]
        assert (
            len(unclosed_warnings) == 0
        ), f"Found unclosed session warnings: {[str(w.message) for w in unclosed_warnings]}"

    @pytest.mark.asyncio
    async def test_context_manager_prevents_unclosed_sessions(self, mock_storage):
        """Test that using async context manager prevents unclosed session warnings."""
        with capture_resource_warnings() as capture:
            async with AsyncDeltaQueryClient(delta_link_storage=mock_storage) as client:
                # Client is used within context
                assert client is not None

            # Allow some time for any delayed warnings
            await asyncio.sleep(0.1)

        # Check that no unclosed session warnings were captured
        unclosed_warnings = [
            w for w in capture.warnings if "client session" in str(w.message).lower()
        ]
        assert (
            len(unclosed_warnings) == 0
        ), f"Found unclosed session warnings: {[str(w.message) for w in unclosed_warnings]}"

    @pytest.mark.asyncio
    async def test_multiple_close_calls_safe(self, mock_storage):
        """Test that calling close() multiple times is safe and doesn't cause issues."""
        with capture_resource_warnings() as capture:
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Call close multiple times
            await client.close()
            await client.close()
            await client.close()

            # Allow some time for any delayed warnings
            await asyncio.sleep(0.1)

        # Check that no warnings were generated from multiple close calls
        assert (
            len(capture.warnings) == 0
        ), f"Unexpected warnings from multiple close calls: {[str(w.message) for w in capture.warnings]}"

    @pytest.mark.asyncio
    async def test_context_manager_with_exception_cleanup(self, mock_storage):
        """Test that context manager properly cleans up even when exceptions occur."""
        with capture_resource_warnings() as capture:
            try:
                async with AsyncDeltaQueryClient(
                    delta_link_storage=mock_storage
                ) as client:
                    # Simulate an exception during usage
                    raise ValueError("Test exception")
            except ValueError:
                # Exception is expected
                pass

            # Allow some time for any delayed warnings
            await asyncio.sleep(0.1)

        # Check that cleanup happened despite the exception
        unclosed_warnings = [
            w for w in capture.warnings if "client session" in str(w.message).lower()
        ]
        assert (
            len(unclosed_warnings) == 0
        ), f"Found unclosed session warnings after exception: {[str(w.message) for w in unclosed_warnings]}"

    @pytest.mark.asyncio
    async def test_local_file_storage_cleanup(self):
        """Test cleanup with LocalFileDeltaLinkStorage."""
        with capture_resource_warnings() as capture:
            storage = LocalFileDeltaLinkStorage()
            client = AsyncDeltaQueryClient(delta_link_storage=storage)
            await client.close()

            await asyncio.sleep(0.1)

        unclosed_warnings = [
            w for w in capture.warnings if "client session" in str(w.message).lower()
        ]
        assert (
            len(unclosed_warnings) == 0
        ), f"Found unclosed session warnings with LocalFileDeltaLinkStorage: {[str(w.message) for w in unclosed_warnings]}"

    @pytest.mark.asyncio
    async def test_close_calls_storage_close(self):
        """Test that closing the client also closes the storage if it has a close method."""
        mock_storage = Mock()
        mock_storage.close = AsyncMock()

        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)
        await client.close()

        # Verify that storage.close() was called
        mock_storage.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_handles_storage_without_close_method(self):
        """Test that closing works even if storage doesn't have a close method."""
        mock_storage = Mock()
        # Intentionally don't add close method to storage

        with capture_resource_warnings() as capture:
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)
            # This should not raise an exception
            await client.close()

            await asyncio.sleep(0.1)

        # Should not generate warnings even if storage doesn't have close
        unclosed_warnings = [
            w for w in capture.warnings if "client session" in str(w.message).lower()
        ]
        assert len(unclosed_warnings) == 0

    @pytest.mark.asyncio
    async def test_close_idempotent(self, mock_storage):
        """Test that close() is idempotent and internal state is managed correctly."""
        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

        # Check initial state
        assert not client._closed

        # First close
        await client.close()
        assert client._closed

        # Second close should be safe
        await client.close()
        assert client._closed

    @pytest.mark.asyncio
    async def test_context_manager_initialization(self, mock_storage):
        """Test that context manager properly initializes the client."""
        async with AsyncDeltaQueryClient(delta_link_storage=mock_storage) as client:
            # Client should be initialized when entering context
            assert client._initialized
            assert not client._closed

        # Client should be closed when exiting context
        assert client._closed

    @pytest.mark.asyncio
    @patch("msgraph_delta_query.client.GraphServiceClient")
    async def test_graph_client_httpx_cleanup(self, mock_graph_service, mock_storage):
        """Test that the httpx client in GraphServiceClient is properly closed."""
        # Mock the GraphServiceClient and its request adapter
        mock_adapter = Mock()
        mock_http_client = Mock()
        # Ensure is_closed is False so aclose will be called
        type(mock_http_client).is_closed = property(lambda self: False)
        mock_http_client.aclose = AsyncMock()
        mock_adapter._http_client = mock_http_client

        mock_graph_instance = Mock()
        mock_graph_instance.request_adapter = mock_adapter
        mock_graph_service.return_value = mock_graph_instance

        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

        # Initialize the client to create the graph client
        await client._initialize()

        # Close the client
        await client.close()

        # Verify that the httpx client's aclose method was called
        mock_http_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_credential_cleanup(self, mock_storage):
        """Test that credentials are properly closed when client is closed."""
        with patch(
            "msgraph_delta_query.client.DefaultAzureCredential"
        ) as mock_cred_class:
            mock_credential = AsyncMock()
            mock_credential.close = AsyncMock()
            mock_cred_class.return_value = mock_credential

            # Create client without providing credential (so it creates one)
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Initialize the client to trigger credential creation
            await client._initialize()

            # Close the client
            await client.close()

            # Verify that credential.close() was called
            mock_credential.close.assert_called_once()
