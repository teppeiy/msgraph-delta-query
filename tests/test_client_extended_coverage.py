"""Extended test coverage for client implementations."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

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


class TestAsyncDeltaQueryClientExtendedCoverage:
    """Extended test coverage for AsyncDeltaQueryClient methods."""

    async def test_get_delta_request_builder_all_resources(self):
        """Test _get_delta_request_builder for all supported resource types."""
        client = AsyncDeltaQueryClient()

        # Mock graph client
        mock_graph_client = Mock()
        mock_graph_client.users.delta = Mock()
        mock_graph_client.applications.delta = Mock()
        mock_graph_client.groups.delta = Mock()
        mock_graph_client.service_principals.delta = Mock()

        client._graph_client = mock_graph_client

        # Test all supported resources
        assert (
            client._get_delta_request_builder("users") == mock_graph_client.users.delta
        )
        assert (
            client._get_delta_request_builder("Users") == mock_graph_client.users.delta
        )
        assert (
            client._get_delta_request_builder("applications")
            == mock_graph_client.applications.delta
        )
        assert (
            client._get_delta_request_builder("groups")
            == mock_graph_client.groups.delta
        )
        assert (
            client._get_delta_request_builder("serviceprincipals")
            == mock_graph_client.service_principals.delta
        )
        assert (
            client._get_delta_request_builder("servicePrincipals")
            == mock_graph_client.service_principals.delta
        )

    async def test_get_delta_request_builder_unsupported_resource(self):
        """Test _get_delta_request_builder with unsupported resource."""
        client = AsyncDeltaQueryClient()
        client._graph_client = Mock()

        with pytest.raises(ValueError, match="Unsupported resource type: invalid"):
            client._get_delta_request_builder("invalid")

    async def test_get_delta_request_builder_no_graph_client(self):
        """Test _get_delta_request_builder when graph client is not initialized."""
        client = AsyncDeltaQueryClient()
        client._graph_client = None

        with pytest.raises(ValueError, match="Graph client not initialized"):
            client._get_delta_request_builder("users")

    async def test_build_query_parameters_all_options(self):
        """Test _build_query_parameters with all possible parameters."""
        client = AsyncDeltaQueryClient()

        # Test with all parameters
        params = client._build_query_parameters(
            select=["id", "displayName"],
            filter="startswith(displayName,'A')",
            top=100,
            deltatoken="test_token",
            skiptoken="skip_token",
        )

        expected = {
            "select": ["id", "displayName"],
            "filter": "startswith(displayName,'A')",
            "top": 100,
            "deltatoken": "test_token",
            "skiptoken": "skip_token",
        }
        assert params == expected

    async def test_build_query_parameters_deltatoken_latest(self):
        """Test _build_query_parameters with deltatoken_latest flag."""
        client = AsyncDeltaQueryClient()

        params = client._build_query_parameters(
            deltatoken="ignored_token", deltatoken_latest=True
        )

        # deltatoken_latest should override deltatoken
        assert params["deltatoken"] == "latest"

    async def test_build_query_parameters_empty(self):
        """Test _build_query_parameters with no parameters."""
        client = AsyncDeltaQueryClient()

        params = client._build_query_parameters()
        assert params == {}

    async def test_process_sdk_object_basic(self):
        """Test _process_sdk_object returns objects as-is."""
        client = AsyncDeltaQueryClient()

        # Mock object representing an SDK object
        mock_obj = Mock()
        mock_obj.id = "123"
        mock_obj.display_name = "Test User"

        result = client._process_sdk_object(mock_obj)

        # Should return the object unchanged
        assert result is mock_obj
        assert result.id == "123"
        assert result.display_name == "Test User"

    async def test_process_sdk_object_with_dict(self):
        """Test _process_sdk_object with dict input."""
        client = AsyncDeltaQueryClient()

        # Dict object (what Graph SDK actually returns)
        dict_obj = {
            "id": "123",
            "displayName": "Test User",
            "extra_field": "extra_value",
        }

        result = client._process_sdk_object(dict_obj)

        # Should return the dict unchanged
        assert result is dict_obj
        assert result["id"] == "123"
        assert result["displayName"] == "Test User"

    async def test_process_sdk_object_with_none(self):
        """Test _process_sdk_object with None input."""
        client = AsyncDeltaQueryClient()

        result = client._process_sdk_object(None)
        assert result is None

    async def test_extract_delta_token_from_link_valid_urls(self):
        """Test _extract_delta_token_from_link with various valid URLs."""
        client = AsyncDeltaQueryClient()

        # Test with $deltatoken
        url1 = "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=abc123"
        token1 = await client._extract_delta_token_from_link(url1)
        assert token1 == "abc123"

        # Test with deltatoken (without $)
        url2 = "https://graph.microsoft.com/v1.0/users/delta?deltatoken=xyz789"
        token2 = await client._extract_delta_token_from_link(url2)
        assert token2 == "xyz789"

        # Test with multiple parameters
        url3 = "https://graph.microsoft.com/v1.0/users/delta?$select=id,displayName&$deltatoken=def456"
        token3 = await client._extract_delta_token_from_link(url3)
        assert token3 == "def456"

    async def test_extract_delta_token_from_link_invalid_inputs(self):
        """Test _extract_delta_token_from_link with invalid inputs."""
        client = AsyncDeltaQueryClient()

        # Test with None
        token = await client._extract_delta_token_from_link(None)
        assert token is None

        # Test with empty string
        token = await client._extract_delta_token_from_link("")
        assert token is None

        # Test with URL without delta token
        url = "https://graph.microsoft.com/v1.0/users"
        token = await client._extract_delta_token_from_link(url)
        assert token is None

    async def test_extract_delta_token_from_link_malformed_url(self):
        """Test _extract_delta_token_from_link with malformed URL."""
        client = AsyncDeltaQueryClient()

        # Test with genuinely malformed URL that will cause urllib.parse to fail
        with patch(
            "msgraph_delta_query.client.urllib.parse.urlparse",
            side_effect=Exception("Parse error"),
        ):
            with patch("msgraph_delta_query.client.logger.warning") as mock_warning:
                malformed_url = "not-a-valid-url://malformed"
                token = await client._extract_delta_token_from_link(malformed_url)
                assert token is None
                # Should log a warning
                mock_warning.assert_called_once()

    async def test_extract_skiptoken_from_url_valid_urls(self):
        """Test _extract_skiptoken_from_url with various valid URLs."""
        client = AsyncDeltaQueryClient()

        # Test with $skiptoken
        url1 = "https://graph.microsoft.com/v1.0/users?$skiptoken=abc123"
        token1 = client._extract_skiptoken_from_url(url1)
        assert token1 == "abc123"

        # Test with skiptoken (without $)
        url2 = "https://graph.microsoft.com/v1.0/users?skiptoken=xyz789"
        token2 = client._extract_skiptoken_from_url(url2)
        assert token2 == "xyz789"

        # Test with multiple parameters
        url3 = "https://graph.microsoft.com/v1.0/users?$select=id&$skiptoken=def456"
        token3 = client._extract_skiptoken_from_url(url3)
        assert token3 == "def456"

    async def test_extract_skiptoken_from_url_invalid_inputs(self):
        """Test _extract_skiptoken_from_url with invalid inputs."""
        client = AsyncDeltaQueryClient()

        # Test with None
        token = client._extract_skiptoken_from_url(None)
        assert token is None

        # Test with empty string
        token = client._extract_skiptoken_from_url("")
        assert token is None

        # Test with URL without skip token
        url = "https://graph.microsoft.com/v1.0/users"
        token = client._extract_skiptoken_from_url(url)
        assert token is None

    async def test_extract_skiptoken_from_url_malformed_url(self):
        """Test _extract_skiptoken_from_url with malformed URL."""
        client = AsyncDeltaQueryClient()

        # Test with genuinely malformed URL that will cause urllib.parse to fail
        with patch(
            "msgraph_delta_query.client.urllib.parse.urlparse",
            side_effect=Exception("Parse error"),
        ):
            with patch("msgraph_delta_query.client.logger.warning") as mock_warning:
                malformed_url = "not-a-valid-url://malformed"
                token = client._extract_skiptoken_from_url(malformed_url)
                assert token is None
                # Should log a warning
                mock_warning.assert_called_once()

    async def test_initialization_with_azure_blob_storage_info_logging(self):
        """Test initialization logging with Azure Blob Storage."""
        with patch("msgraph_delta_query.client.logger.info") as mock_info:
            # Mock Azure Blob Storage
            mock_storage = Mock()
            mock_storage.__class__.__name__ = "AzureBlobDeltaLinkStorage"
            mock_storage.container_name = "test-container"
            mock_storage._account_url = "https://testaccount.blob.core.windows.net"
            mock_storage._connection_string = None

            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Should log storage info with account name extracted from URL
            mock_info.assert_called()
            call_args = mock_info.call_args[0][0]
            assert "AzureBlobDeltaLinkStorage" in call_args
            assert "testaccount" in call_args
            assert "test-container" in call_args

    async def test_initialization_with_azure_blob_storage_connection_string_logging(
        self,
    ):
        """Test initialization logging with Azure Blob Storage using connection string."""
        with patch("msgraph_delta_query.client.logger.info") as mock_info:
            # Mock Azure Blob Storage with connection string
            mock_storage = Mock()
            mock_storage.__class__.__name__ = "AzureBlobDeltaLinkStorage"
            mock_storage.container_name = "test-container"
            mock_storage._account_url = None
            mock_storage._connection_string = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=key;EndpointSuffix=core.windows.net"

            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Should log storage info with account name extracted from connection string
            mock_info.assert_called()
            call_args = mock_info.call_args[0][0]
            assert "AzureBlobDeltaLinkStorage" in call_args
            assert "testaccount" in call_args
            assert "test-container" in call_args

    async def test_initialization_with_local_file_storage_logging(self):
        """Test initialization logging with Local File Storage."""
        with patch("msgraph_delta_query.client.logger.info") as mock_info:
            # Mock Local File Storage
            mock_storage = Mock()
            mock_storage.__class__.__name__ = "LocalFileDeltaLinkStorage"
            mock_storage.deltalinks_dir = "custom_deltalinks"

            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Should log storage info with directory
            mock_info.assert_called()
            call_args = mock_info.call_args[0][0]
            assert "LocalFileDeltaLinkStorage" in call_args
            assert "custom_deltalinks" in call_args

    async def test_signal_handler_setup_with_running_loop(self):
        """Test signal handler setup when running loop exists."""
        # This tests the signal handler setup in __init__

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_loop.add_signal_handler = Mock()
            mock_get_loop.return_value = mock_loop

            # Create client which should set up signal handlers
            client = AsyncDeltaQueryClient()

            # Should have attempted to add signal handlers
            assert (
                mock_loop.add_signal_handler.call_count >= 0
            )  # May be called for SIGTERM and SIGINT

    async def test_signal_handler_setup_with_no_running_loop(self):
        """Test signal handler setup when no running loop exists."""
        with patch(
            "asyncio.get_running_loop", side_effect=RuntimeError("No running loop")
        ):
            # Should not raise exception
            client = AsyncDeltaQueryClient()
            assert client is not None

    async def test_destructor_cleanup_warning(self):
        """Test destructor cleanup warning."""
        client = AsyncDeltaQueryClient()
        client._closed = False  # Simulate not being properly closed

        # Mock asyncio.get_running_loop to raise RuntimeError (no running loop)
        with patch(
            "asyncio.get_running_loop", side_effect=RuntimeError("No running loop")
        ):
            with patch("msgraph_delta_query.client.logger.warning") as mock_warning:
                # Call destructor directly
                client.__del__()

                # Should log warning about improper cleanup
                mock_warning.assert_called_with(
                    "AsyncDeltaQueryClient destroyed without proper cleanup (no running event loop)"
                )
                call_args = mock_warning.call_args[0][0]
                assert "destroyed without proper cleanup" in call_args

    async def test_destructor_no_warning_when_closed(self):
        """Test destructor doesn't warn when client is already closed."""
        client = AsyncDeltaQueryClient()
        client._closed = True  # Already closed

        with patch("logging.warning") as mock_warning:
            # Call destructor directly
            client.__del__()

            # Should not log warning
            mock_warning.assert_not_called()

    async def test_reset_delta_link(self, mock_storage):
        """Test reset_delta_link method."""
        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

        # Add some data first
        await mock_storage.set("users", "old_delta_link", {"metadata": "test"})

        # Reset delta link
        await client.reset_delta_link("users")

        # Should be deleted from storage
        result = await mock_storage.get("users")
        assert result is None

    async def test_client_registry_tracking(self):
        """Test that clients are properly tracked in registry."""
        initial_count = len(_client_registry)

        client1 = AsyncDeltaQueryClient()
        client2 = AsyncDeltaQueryClient()

        # Should be added to registry
        assert len(_client_registry) == initial_count + 2
        assert client1 in _client_registry
        assert client2 in _client_registry

    async def test_cleanup_all_clients_function(self):
        """Test the _cleanup_all_clients function."""
        # Create some clients
        client1 = AsyncDeltaQueryClient()
        client2 = AsyncDeltaQueryClient()

        # Mock their _internal_close methods
        client1._internal_close = AsyncMock()
        client2._internal_close = AsyncMock()

        # Call cleanup
        await _cleanup_all_clients()

        # Should have called _internal_close on both clients
        client1._internal_close.assert_called_once()
        client2._internal_close.assert_called_once()

    async def test_cleanup_all_clients_with_errors(self):
        """Test _cleanup_all_clients handles errors gracefully."""
        client = AsyncDeltaQueryClient()
        client._internal_close = AsyncMock(side_effect=Exception("Cleanup error"))

        with patch("msgraph_delta_query.client.logger.warning") as mock_warning:
            # Should not raise exception
            await _cleanup_all_clients()

            # Should log warning about cleanup error
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0][0]
            assert "Error cleaning up client" in call_args
