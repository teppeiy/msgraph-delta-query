"""Test client implementations for SDK-based architecture."""

import pytest
import asyncio
import json
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from msgraph_delta_query.client import (
    AsyncDeltaQueryClient,
    _cleanup_all_clients,
    _client_registry,
)
from msgraph_delta_query.storage import DeltaLinkStorage


class MockDeltaLinkStorage(DeltaLinkStorage):
    """Mock storage for testing."""

    def __init__(self):
        self.storage = {}
        self.metadata_storage = {}

    async def get(self, resource: str):
        return self.storage.get(resource)

    async def set(self, resource: str, delta_link: str, metadata=None):
        self.storage[resource] = delta_link
        if metadata:
            self.metadata_storage[resource] = metadata

    async def delete(self, resource: str):
        self.storage.pop(resource, None)
        self.metadata_storage.pop(resource, None)

    async def get_metadata(self, resource: str):
        return self.metadata_storage.get(resource)


@pytest.fixture
def mock_storage():
    """Provide a mock storage instance."""
    return MockDeltaLinkStorage()


@pytest.fixture
def mock_credential():
    """Provide a mock Azure credential."""
    mock_cred = AsyncMock()
    mock_cred.get_token = AsyncMock()
    mock_cred.close = AsyncMock()
    return mock_cred


class TestAsyncDeltaQueryClientSDK:
    """Test AsyncDeltaQueryClient with SDK-based architecture."""

    async def test_init_default_parameters(self):
        """Test client initialization with default parameters."""
        client = AsyncDeltaQueryClient()

        assert client.credential is None
        assert client.delta_link_storage is not None
        assert client.scopes == ["https://graph.microsoft.com/.default"]
        assert not client._initialized
        assert not client._closed
        assert not client._credential_created
        assert client in _client_registry

    async def test_init_custom_parameters(self, mock_credential, mock_storage):
        """Test client initialization with custom parameters."""
        custom_scopes = ["https://graph.microsoft.com/User.Read.All"]
        client = AsyncDeltaQueryClient(
            credential=mock_credential,
            delta_link_storage=mock_storage,
            scopes=custom_scopes,
        )

        assert client.credential == mock_credential
        assert client.delta_link_storage == mock_storage
        assert client.scopes == custom_scopes
        assert not client._initialized
        assert not client._closed
        assert not client._credential_created

    async def test_initialize_creates_graph_client(self):
        """Test that _initialize creates GraphServiceClient."""
        client = AsyncDeltaQueryClient()

        with patch("msgraph_delta_query.client.GraphServiceClient") as mock_graph_class:
            mock_graph_client = Mock()
            mock_graph_class.return_value = mock_graph_client

            with patch(
                "msgraph_delta_query.client.DefaultAzureCredential"
            ) as mock_cred_class:
                mock_credential = AsyncMock()
                mock_cred_class.return_value = mock_credential

                await client._initialize()

                assert client._initialized
                assert client._graph_client == mock_graph_client
                assert client.credential == mock_credential
                assert client._credential_created
                mock_graph_class.assert_called_once()
                mock_cred_class.assert_called_once()

    async def test_initialize_idempotent(self):
        """Test that _initialize can be called multiple times safely."""
        client = AsyncDeltaQueryClient()

        with patch("msgraph_delta_query.client.GraphServiceClient") as mock_graph_class:
            with patch(
                "msgraph_delta_query.client.DefaultAzureCredential"
            ) as mock_cred_class:
                await client._initialize()
                await client._initialize()  # Second call should not create new instances

                assert mock_graph_class.call_count == 1
                assert mock_cred_class.call_count == 1

    async def test_initialize_skipped_when_closed(self):
        """Test that _initialize resets state when client was previously closed."""
        client = AsyncDeltaQueryClient()
        client._closed = True

        with patch("msgraph_delta_query.client.GraphServiceClient") as mock_graph_class:
            with patch(
                "msgraph_delta_query.client.DefaultAzureCredential"
            ) as mock_cred_class:
                await client._initialize()

                # Should reset closed state and initialize
                assert not client._closed
                assert client._initialized
                mock_graph_class.assert_called_once()
                mock_cred_class.assert_called_once()

    async def test_internal_close(self, mock_credential):
        """Test internal cleanup."""
        client = AsyncDeltaQueryClient(credential=mock_credential)
        client._graph_client = Mock()
        client._initialized = True
        client._credential_created = True  # Simulate that we created the credential

        await client._internal_close()

        assert client._closed
        assert client._graph_client is None
        assert client.credential is None
        mock_credential.close.assert_called_once()

    async def test_internal_close_idempotent(self):
        """Test that _internal_close can be called multiple times."""
        client = AsyncDeltaQueryClient()

        await client._internal_close()
        await client._internal_close()  # Should not raise

        assert client._closed

    async def test_internal_close_handles_credential_error(self, mock_credential):
        """Test that _internal_close handles credential errors gracefully."""
        client = AsyncDeltaQueryClient(credential=mock_credential)
        client._credential_created = True  # Simulate that we created the credential
        mock_credential.close.side_effect = Exception("Close error")

        with patch("logging.warning") as mock_warning:
            await client._internal_close()
            mock_warning.assert_called_with("Error closing credential: Close error")

    async def test_extract_delta_token_from_link(self):
        """Test delta token extraction from delta links."""
        client = AsyncDeltaQueryClient()

        # Test valid delta link
        delta_link = "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=abc123"
        token = await client._extract_delta_token_from_link(delta_link)
        assert token == "abc123"

        # Test invalid delta link
        invalid_link = "https://graph.microsoft.com/v1.0/users"
        token = await client._extract_delta_token_from_link(invalid_link)
        assert token is None

        # Test None
        token = await client._extract_delta_token_from_link(None)
        assert token is None

    async def test_delta_query_stream_basic(self, mock_credential, mock_storage):
        """Test basic delta query streaming with SDK."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Create mock graph client and set it directly
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Mock SDK response
        mock_response = Mock()
        mock_response.value = [{"id": "1", "display_name": "User1"}]
        mock_response.odata_next_link = None
        mock_response.odata_delta_link = "https://example.com/delta?token=xyz"

        # Mock the entire _execute_delta_request method to return the mock response
        async def mock_execute_delta_request(*args, **kwargs):
            return mock_response, False  # response, fallback_occurred

        with patch.object(
            client, "_execute_delta_request", side_effect=mock_execute_delta_request
        ):
            objects = []
            async for page_objects, metadata in client.delta_query_stream("users"):
                objects.extend(page_objects)

            assert len(objects) == 1
            assert objects[0]["id"] == "1"
            assert objects[0]["display_name"] == "User1"

    async def test_delta_query_success(self, mock_credential, mock_storage):
        """Test delta_query successful execution."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the stream method
        async def mock_stream(*args, **kwargs):
            from msgraph_delta_query.models import PageMetadata

            page1_meta = PageMetadata(
                page=1,
                object_count=1,
                has_next_page=True,
                delta_link=None,
                raw_response_size=100,
                page_new_or_updated=1,
                page_deleted=0,
                page_changed=0,
                total_new_or_updated=1,
                total_deleted=0,
                total_changed=0,
            )
            page2_meta = PageMetadata(
                page=2,
                object_count=1,
                has_next_page=False,
                delta_link="final_link",
                raw_response_size=100,
                page_new_or_updated=1,
                page_deleted=0,
                page_changed=0,
                total_new_or_updated=2,
                total_deleted=0,
                total_changed=0,
            )
            yield [{"id": "1"}], page1_meta
            yield [{"id": "2"}], page2_meta

        with patch.object(client, "delta_query_stream", side_effect=mock_stream):
            objects, delta_link, meta = await client.delta_query("users")

            assert len(objects) == 2
            assert objects[0]["id"] == "1"
            assert objects[1]["id"] == "2"
            assert delta_link == "final_link"
            assert meta.change_summary.new_or_updated == 2
            assert meta.pages_fetched == 2
            assert hasattr(meta, "duration_seconds")
            assert hasattr(meta, "start_time")
            assert hasattr(meta, "end_time")

    async def test_delta_query_with_max_objects(self, mock_credential, mock_storage):
        """Test delta_query respects max_objects limit."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the stream method to return more objects than the limit
        async def mock_stream(*args, **kwargs):
            from msgraph_delta_query.models import PageMetadata

            page1_meta = PageMetadata(
                page=1,
                object_count=2,
                has_next_page=True,
                delta_link=None,
                raw_response_size=100,
                page_new_or_updated=2,
                page_deleted=0,
                page_changed=0,
                total_new_or_updated=2,
                total_deleted=0,
                total_changed=0,
            )
            page2_meta = PageMetadata(
                page=2,
                object_count=2,
                has_next_page=False,
                delta_link="final_link",
                raw_response_size=100,
                page_new_or_updated=2,
                page_deleted=0,
                page_changed=0,
                total_new_or_updated=4,
                total_deleted=0,
                total_changed=0,
            )
            yield [{"id": "1"}, {"id": "2"}], page1_meta
            yield [{"id": "3"}, {"id": "4"}], page2_meta

        with patch.object(client, "delta_query_stream", side_effect=mock_stream):
            objects, delta_link, meta = await client.delta_query("users", max_objects=3)

            assert len(objects) == 3  # Limited to 3 despite having 4 available
            assert objects[0]["id"] == "1"
            assert objects[1]["id"] == "2"
            assert objects[2]["id"] == "3"

    async def test_reset_delta_link(self, mock_storage):
        """Test delta link reset functionality."""
        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

        # Set a delta link first
        await mock_storage.set("users", "some_delta_link")
        assert await mock_storage.get("users") == "some_delta_link"

        # Reset it
        await client.reset_delta_link("users")
        assert await mock_storage.get("users") is None

    async def test_destructor_cleanup_warning(self):
        """Test that destructor warns about improper cleanup."""
        with patch("logging.warning") as mock_warning:
            client = AsyncDeltaQueryClient()
            client._closed = False  # Simulate not closed
            del client
            # Warning should be called about improper cleanup

    async def test_supported_resources(self):
        """Test that supported resources are correctly defined."""
        client = AsyncDeltaQueryClient()

        assert "users" in client.SUPPORTED_RESOURCES
        assert "applications" in client.SUPPORTED_RESOURCES
        assert "groups" in client.SUPPORTED_RESOURCES
        assert "serviceprincipals" in client.SUPPORTED_RESOURCES


# Global utility function tests
async def test_cleanup_all_clients():
    """Test cleanup of all clients."""
    client1 = AsyncDeltaQueryClient()
    client2 = AsyncDeltaQueryClient()

    with patch.object(client1, "_internal_close") as mock_close1:
        with patch.object(client2, "_internal_close") as mock_close2:
            await _cleanup_all_clients()

            mock_close1.assert_called_once()
            mock_close2.assert_called_once()


async def test_cleanup_all_clients_with_errors():
    """Test cleanup handles errors gracefully."""
    client = AsyncDeltaQueryClient()

    with patch.object(client, "_internal_close", side_effect=Exception("Test error")):
        with patch("logging.warning") as mock_warning:
            await _cleanup_all_clients()
            mock_warning.assert_called()
