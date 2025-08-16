"""
Simplified Azure Blob Storage test with focused mocking strategy.

Tests core functionality with strategic mocking to achieve high coverage.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

# Import Azure exceptions
try:
    from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError
except ImportError:
    ResourceNotFoundError = Exception
    ServiceRequestError = Exception


class TestAzureBlobStorageSimpleMocking:
    """Test Azure Blob Storage with simplified, effective mocking."""

    @pytest.mark.asyncio
    async def test_full_storage_operations_mocked(self):
        """Test complete storage operations with comprehensive mocking."""
        try:
            from msgraph_delta_query.storage import AzureBlobDeltaLinkStorage
        except ImportError:
            pytest.skip("Azure Blob Storage dependencies not available")

        # Test data
        test_delta_link = (
            "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=test123"
        )
        test_metadata = {
            "last_sync": "2025-08-02T10:00:00Z",
            "change_summary": {"new_or_updated": 5, "deleted": 1},
            "total_pages": 2,
        }

        storage = AzureBlobDeltaLinkStorage(container_name="test-storage")

        # Mock the individual storage methods directly
        with patch.object(
            storage, "_ensure_container_exists", new_callable=AsyncMock
        ), patch.object(
            storage, "_get_blob_service_client", new_callable=AsyncMock
        ) as mock_get_client:

            # Mock the blob service client chain
            mock_service = MagicMock()
            mock_container = MagicMock()
            mock_blob = MagicMock()

            mock_get_client.return_value = mock_service
            mock_service.get_blob_client.return_value = mock_blob

            # Configure async methods
            mock_blob.upload_blob = AsyncMock()
            mock_blob.download_blob = AsyncMock()
            mock_blob.delete_blob = AsyncMock()

            # Test SET operation
            await storage.set("users", test_delta_link, test_metadata)

            # Verify upload was called
            mock_blob.upload_blob.assert_called_once()
            upload_args = mock_blob.upload_blob.call_args
            uploaded_data = json.loads(upload_args[0][0].decode("utf-8"))
            assert uploaded_data["delta_link"] == test_delta_link
            assert uploaded_data["metadata"] == test_metadata
            assert "last_updated" in uploaded_data
            assert "resource" in uploaded_data

            # Setup download mock for GET operations
            mock_download_result = MagicMock()
            mock_download_result.readall = AsyncMock(
                return_value=json.dumps(uploaded_data).encode()
            )
            mock_blob.download_blob.return_value = mock_download_result

            # Test GET operation
            result = await storage.get("users")
            assert result == test_delta_link

            # Test GET_METADATA operation
            metadata = await storage.get_metadata("users")
            assert metadata is not None
            assert metadata["metadata"] == test_metadata

            # Test DELETE operation
            await storage.delete("users")
            mock_blob.delete_blob.assert_called_once()

            await storage.close()

    @pytest.mark.asyncio
    async def test_container_management_scenarios(self):
        """Test container creation and management scenarios."""
        try:
            from msgraph_delta_query.storage import AzureBlobDeltaLinkStorage
        except ImportError:
            pytest.skip("Azure Blob Storage dependencies not available")

        storage = AzureBlobDeltaLinkStorage(container_name="new-container")

        # Mock the container management methods directly
        with patch.object(
            storage, "_get_blob_service_client", new_callable=AsyncMock
        ) as mock_get_client:
            mock_service = MagicMock()
            mock_container = MagicMock()

            mock_get_client.return_value = mock_service
            mock_service.get_container_client.return_value = mock_container

            # Test container creation when it doesn't exist
            mock_container.get_container_properties = AsyncMock(
                side_effect=ResourceNotFoundError("Container not found")
            )
            mock_container.create_container = AsyncMock(return_value=True)

            # This will trigger container creation
            await storage._ensure_container_exists()

            # Verify container creation was called
            mock_container.create_container.assert_called_once()

            await storage.close()

    @pytest.mark.asyncio
    async def test_connection_string_detection(self):
        """Test connection string detection methods."""
        try:
            from msgraph_delta_query.storage import AzureBlobDeltaLinkStorage
        except ImportError:
            pytest.skip("Azure Blob Storage dependencies not available")

        storage = AzureBlobDeltaLinkStorage(container_name="test")

        # Test the connection detection method
        connection_info = storage._detect_connection_with_priority()

        # Should find some form of connection (environment, local settings, or Azurite)
        assert "connection_string" in connection_info
        assert connection_info["connection_string"]

        # Test blob name sanitization
        test_cases = [
            ("simple", "simple.json"),
            ("with spaces", "with spaces.json"),
            ("with/slashes", "with_slashes.json"),
            ("with@special#chars!", "with@special#chars!.json"),
        ]

        for resource_name, expected in test_cases:
            blob_name = storage._get_blob_name(resource_name)
            assert blob_name == expected

        await storage.close()

    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """Test that critical errors are properly propagated."""
        try:
            from msgraph_delta_query.storage import AzureBlobDeltaLinkStorage
        except ImportError:
            pytest.skip("Azure Blob Storage dependencies not available")

        storage = AzureBlobDeltaLinkStorage(container_name="error-test")

        # Mock to raise ServiceRequestError during upload
        with patch.object(
            storage, "_ensure_container_exists", new_callable=AsyncMock
        ), patch.object(
            storage, "_get_blob_service_client", new_callable=AsyncMock
        ) as mock_get_client:

            mock_service = MagicMock()
            mock_blob = MagicMock()

            mock_get_client.return_value = mock_service
            mock_service.get_blob_client.return_value = mock_blob

            # Test service error propagation
            mock_blob.upload_blob = AsyncMock(
                side_effect=ServiceRequestError("Service unavailable")
            )

            with pytest.raises(ServiceRequestError):
                await storage.set("test", "https://example.com", {})

            await storage.close()
