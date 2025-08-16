"""
Comprehensive coverage tests for client.py edge cases and error conditions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from msgraph_delta_query.client import AsyncDeltaQueryClient
from msgraph_delta_query.storage.base import DeltaLinkStorage
from azure.identity.aio import DefaultAzureCredential


class TestClientComprehensiveCoverage:
    """Test client edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_init_with_explicit_credential(self):
        """Test initialization with explicit credential."""
        mock_credential = MagicMock(spec=DefaultAzureCredential)
        mock_storage = MagicMock(spec=DeltaLinkStorage)

        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        assert client.credential == mock_credential
        assert client.delta_link_storage == mock_storage

        await client._internal_close()

    @pytest.mark.asyncio
    async def test_init_minimal_parameters(self):
        """Test initialization with minimal parameters (all defaults)."""
        client = AsyncDeltaQueryClient()

        # Should create LocalFileDeltaLinkStorage by default
        assert client.credential is None  # Created on-demand
        assert client.delta_link_storage is not None
        assert client.scopes == ["https://graph.microsoft.com/.default"]

        await client._internal_close()

    @pytest.mark.asyncio
    async def test_del_without_proper_cleanup(self):
        """Test __del__ method when client wasn't properly closed."""
        mock_storage = MagicMock(spec=DeltaLinkStorage)

        # Create client in a way that triggers __del__ warning
        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)
        client._graph_client = MagicMock()  # Simulate active client

        # Mock the logging to capture warning and asyncio.get_running_loop to raise RuntimeError
        with patch("msgraph_delta_query.client.logging") as mock_logging, patch(
            "msgraph_delta_query.client.asyncio.get_running_loop",
            side_effect=RuntimeError("No event loop"),
        ):
            # Manually call __del__ to test the warning
            client.__del__()

            # Should log warning about improper cleanup
            mock_logging.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_delta_link_with_storage_error(self):
        """Test reset_delta_link when storage.delete raises error."""
        mock_storage = AsyncMock(spec=DeltaLinkStorage)
        mock_storage.delete.side_effect = Exception("Storage error")

        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

        # Should not raise exception (error is logged)
        await client.reset_delta_link("users")

    @pytest.mark.asyncio
    async def test_storage_info_logging_azure_blob_with_account_url(self):
        """Test storage info logging for Azure Blob Storage with account URL."""
        from msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage

        mock_storage = MagicMock(spec=AzureBlobDeltaLinkStorage)
        mock_storage.container_name = "test-container"
        mock_storage._account_url = "https://testaccount.blob.core.windows.net"
        mock_storage._connection_string = None

        with patch("msgraph_delta_query.client.logging") as mock_logging:
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Should log storage info with account name
            mock_logging.info.assert_called()
            logged_message = mock_logging.info.call_args[0][0]
            assert "testaccount" in logged_message
            assert "test-container" in logged_message

    @pytest.mark.asyncio
    async def test_storage_info_logging_azure_blob_with_connection_string(self):
        """Test storage info logging for Azure Blob Storage with connection string."""
        from msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage

        mock_storage = MagicMock(spec=AzureBlobDeltaLinkStorage)
        mock_storage.container_name = "test-container"
        mock_storage._account_url = None
        mock_storage._connection_string = (
            "DefaultEndpointsProtocol=https;AccountName=testconn;AccountKey=key123"
        )

        with patch("msgraph_delta_query.client.logging") as mock_logging:
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Should log storage info with account name from connection string
            mock_logging.info.assert_called()
            logged_message = mock_logging.info.call_args[0][0]
            assert "testconn" in logged_message
            assert "test-container" in logged_message

    @pytest.mark.asyncio
    async def test_storage_info_logging_local_file(self):
        """Test storage info logging for LocalFile storage."""
        from msgraph_delta_query.storage.local_file import LocalFileDeltaLinkStorage

        mock_storage = MagicMock(spec=LocalFileDeltaLinkStorage)
        mock_storage.deltalinks_dir = "custom-deltalinks"

        with patch("msgraph_delta_query.client.logging") as mock_logging:
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Should log storage info with directory
            mock_logging.info.assert_called()
            logged_message = mock_logging.info.call_args[0][0]
            assert "custom-deltalinks" in logged_message

    @pytest.mark.asyncio
    async def test_credential_error_handling_in_close(self):
        """Test error handling when closing credential."""
        mock_storage = AsyncMock(spec=DeltaLinkStorage)
        mock_credential = MagicMock()
        mock_credential.close = AsyncMock(side_effect=Exception("Close error"))

        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )
        client._credential_created = True

        # Should not raise exception when credential.close() fails
        await client._internal_close()

    @pytest.mark.asyncio
    async def test_storage_error_handling_in_close(self):
        """Test error handling when closing storage."""
        mock_storage = AsyncMock(spec=DeltaLinkStorage)
        mock_storage.close.side_effect = Exception("Storage close error")

        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

        # Should not raise exception when storage.close() fails
        await client._internal_close()

    @pytest.mark.asyncio
    async def test_azure_blob_storage_account_url_parsing_error(self):
        """Test Azure Blob Storage account URL parsing with malformed URL."""
        from msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage

        mock_storage = MagicMock(spec=AzureBlobDeltaLinkStorage)
        mock_storage.container_name = "test-container"
        mock_storage._account_url = "malformed_url_without_proper_format"
        mock_storage._connection_string = None

        with patch("msgraph_delta_query.client.logging") as mock_logging:
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Should handle malformed URL gracefully
            mock_logging.info.assert_called()
            logged_message = mock_logging.info.call_args[0][0]
            assert "from account URL" in logged_message

    @pytest.mark.asyncio
    async def test_azure_blob_storage_connection_string_parsing_error(self):
        """Test Azure Blob Storage connection string parsing with malformed string."""
        from msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage

        mock_storage = MagicMock(spec=AzureBlobDeltaLinkStorage)
        mock_storage.container_name = "test-container"
        mock_storage._account_url = None
        mock_storage._connection_string = "malformed_connection_string_no_account_name"

        with patch("msgraph_delta_query.client.logging") as mock_logging:
            client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

            # Should handle malformed connection string gracefully
            mock_logging.info.assert_called()
            logged_message = mock_logging.info.call_args[0][0]
            assert "from connection string" in logged_message

    @pytest.mark.asyncio
    async def test_extract_skiptoken_from_url_edge_cases(self):
        """Test _extract_skiptoken_from_url with edge cases."""
        client = AsyncDeltaQueryClient()

        # Test with None URL
        result = client._extract_skiptoken_from_url(None)
        assert result is None

        # Test with empty URL
        result = client._extract_skiptoken_from_url("")
        assert result is None

        # Test with URL without skiptoken
        result = client._extract_skiptoken_from_url("https://example.com/api")
        assert result is None

        # Test with URL with skiptoken
        result = client._extract_skiptoken_from_url(
            "https://example.com/api?$skiptoken=abc123"
        )
        assert result == "abc123"

    @pytest.mark.asyncio
    async def test_process_sdk_object_with_none(self):
        """Test _process_sdk_object with None object."""
        client = AsyncDeltaQueryClient()

        result = client._process_sdk_object(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_process_sdk_object_with_dict(self):
        """Test _process_sdk_object with dictionary object."""
        client = AsyncDeltaQueryClient()

        test_obj = {"id": "123", "name": "test"}
        result = client._process_sdk_object(test_obj)
        assert result == test_obj  # Should return as-is

    @pytest.mark.asyncio
    async def test_get_delta_request_builder_unsupported_resource(self):
        """Test _get_delta_request_builder with unsupported resource."""
        client = AsyncDeltaQueryClient()

        with pytest.raises(ValueError, match="Unsupported resource"):
            client._get_delta_request_builder("unsupported_resource")

    @pytest.mark.asyncio
    async def test_initialize_with_existing_graph_client(self):
        """Test _initialize when graph client already exists."""
        mock_storage = AsyncMock(spec=DeltaLinkStorage)
        client = AsyncDeltaQueryClient(delta_link_storage=mock_storage)

        # Mock existing graph client
        mock_graph_client = MagicMock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Should not recreate graph client
        await client._initialize()
        assert client._graph_client == mock_graph_client

    @pytest.mark.asyncio
    async def test_build_query_parameters_with_select_and_filter(self):
        """Test _build_query_parameters with select and filter."""
        client = AsyncDeltaQueryClient()

        params = client._build_query_parameters(
            select=["id", "displayName"], filter="startswith(displayName,'Test')"
        )

        assert hasattr(params, "select")
        assert hasattr(params, "filter")
