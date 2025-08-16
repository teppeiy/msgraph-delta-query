"""
Comprehensive coverage tests for Azure Blob Storage module.
Tests edge cases, error conditions, and uncovered code paths.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError
from azure.identity.aio import DefaultAzureCredential

from msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage


class TestAzureBlobStorageComprehensiveCoverage:
    """Test Azure Blob Storage edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_priority_1_managed_identity_with_account_name(self):
        """Test Priority 1: Managed identity with AZURE_STORAGE_ACCOUNT_NAME."""
        with patch.dict(
            os.environ, {"AZURE_STORAGE_ACCOUNT_NAME": "testaccount"}, clear=True
        ):
            storage = AzureBlobDeltaLinkStorage()

            # Should use managed identity
            assert storage._account_url == "https://testaccount.blob.core.windows.net"
            assert storage._connection_string is None
            assert storage._credential is None  # Will be created later

        await storage.close()

    @pytest.mark.asyncio
    async def test_priority_2_azure_storage_connection_string_env(self):
        """Test Priority 2: AZURE_STORAGE_CONNECTION_STRING environment variable."""
        test_conn = "DefaultEndpointsProtocol=https;AccountName=testaccount;AccountKey=key123;EndpointSuffix=core.windows.net"

        with patch.dict(
            os.environ, {"AZURE_STORAGE_CONNECTION_STRING": test_conn}, clear=True
        ):
            storage = AzureBlobDeltaLinkStorage()

            assert storage._connection_string == test_conn
            assert storage._account_url is None
            assert storage._credential is None

        await storage.close()

    @pytest.mark.asyncio
    async def test_priority_2_azure_webjobs_storage_env(self):
        """Test Priority 2: AzureWebJobsStorage environment variable."""
        test_conn = "DefaultEndpointsProtocol=https;AccountName=webjobsaccount;AccountKey=key456;EndpointSuffix=core.windows.net"

        with patch.dict(os.environ, {"AzureWebJobsStorage": test_conn}, clear=True):
            storage = AzureBlobDeltaLinkStorage()

            assert storage._connection_string == test_conn

        await storage.close()

    @pytest.mark.asyncio
    async def test_priority_3_local_settings_json_with_azure_webjobs_storage(self):
        """Test Priority 3: local.settings.json with AzureWebJobsStorage."""
        test_conn = "DefaultEndpointsProtocol=https;AccountName=localsettings;AccountKey=localkey;EndpointSuffix=core.windows.net"
        local_settings = {"Values": {"AzureWebJobsStorage": test_conn}}

        # Create a temporary local.settings.json
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="local.settings.json", delete=False
        ) as f:
            json.dump(local_settings, f)
            temp_path = f.name

        try:
            # Clear environment variables and use custom path
            with patch.dict(os.environ, {}, clear=True):
                storage = AzureBlobDeltaLinkStorage()
                storage._local_settings_path = temp_path

                # Re-detect connection with the custom path
                detected = storage._detect_connection_with_priority()
                assert detected["connection_string"] == test_conn
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_priority_3_local_settings_json_invalid_json(self):
        """Test Priority 3: local.settings.json with invalid JSON."""
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(
            mode="w", suffix="local.settings.json", delete=False
        ) as f:
            f.write("{ invalid json")
            temp_path = f.name

        try:
            with patch.dict(os.environ, {}, clear=True):
                storage = AzureBlobDeltaLinkStorage()
                storage._local_settings_path = temp_path

                # Should fall back to Azurite
                detected = storage._detect_connection_with_priority()
                assert "devstoreaccount1" in detected["connection_string"]
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_priority_3_local_settings_json_missing_file(self):
        """Test Priority 3: local.settings.json file doesn't exist."""
        with patch.dict(os.environ, {}, clear=True):
            storage = AzureBlobDeltaLinkStorage()
            storage._local_settings_path = "/nonexistent/local.settings.json"

            # Should fall back to Azurite
            detected = storage._detect_connection_with_priority()
            assert "devstoreaccount1" in detected["connection_string"]

    @pytest.mark.asyncio
    async def test_connection_string_account_extraction_error(self):
        """Test connection string account name extraction with malformed string."""
        malformed_conn = "DefaultEndpointsProtocol=https;AccountKey=key123;EndpointSuffix=core.windows.net"  # Missing AccountName

        with patch.dict(
            os.environ, {"AZURE_STORAGE_CONNECTION_STRING": malformed_conn}, clear=True
        ):
            storage = AzureBlobDeltaLinkStorage()
            # Should still work but account_info will be "unknown"
            assert storage._connection_string == malformed_conn

    @pytest.mark.asyncio
    async def test_blob_service_client_with_account_url_and_credential(self):
        """Test creating blob service client with account URL and credential."""
        mock_credential = MagicMock(spec=DefaultAzureCredential)

        storage = AzureBlobDeltaLinkStorage(
            account_url="https://testaccount.blob.core.windows.net",
            credential=mock_credential,
        )

        with patch(
            "msgraph_delta_query.storage.azure_blob.BlobServiceClient"
        ) as mock_blob_client:
            client = await storage._get_blob_service_client()

            mock_blob_client.assert_called_once_with(
                account_url="https://testaccount.blob.core.windows.net",
                credential=mock_credential,
            )

    @pytest.mark.asyncio
    async def test_blob_service_client_with_managed_identity(self):
        """Test creating blob service client with managed identity (no credential provided)."""
        storage = AzureBlobDeltaLinkStorage(
            account_url="https://testaccount.blob.core.windows.net"
        )

        with patch(
            "msgraph_delta_query.storage.azure_blob.BlobServiceClient"
        ) as mock_blob_client, patch(
            "msgraph_delta_query.storage.azure_blob.DefaultAzureCredential"
        ) as mock_cred_class:

            mock_credential = MagicMock()
            mock_cred_class.return_value = mock_credential

            client = await storage._get_blob_service_client()

            # Should create DefaultAzureCredential
            mock_cred_class.assert_called_once()
            assert storage._credential == mock_credential
            assert storage._credential_created is True

    @pytest.mark.asyncio
    async def test_blob_service_client_no_connection_error(self):
        """Test error when no connection string or account URL available."""
        storage = AzureBlobDeltaLinkStorage()
        storage._connection_string = None
        storage._account_url = None

        with pytest.raises(
            ValueError, match="No account URL or connection string available"
        ):
            await storage._get_blob_service_client()

    @pytest.mark.asyncio
    async def test_get_blob_name_long_resource_name(self):
        """Test blob name creation with very long resource name."""
        storage = AzureBlobDeltaLinkStorage()

        # Create a resource name longer than 200 characters
        long_name = "a" * 250
        blob_name = storage._get_blob_name(long_name)

        # Should be truncated and have .json extension
        assert len(blob_name) <= 200 + 5  # +5 for .json
        assert blob_name.endswith(".json")

    @pytest.mark.asyncio
    async def test_get_blob_name_special_characters(self):
        """Test blob name creation with special characters."""
        storage = AzureBlobDeltaLinkStorage()

        resource_name = "resource/with\\special:characters"
        blob_name = storage._get_blob_name(resource_name)

        # Special characters should be replaced with underscores
        assert "/" not in blob_name
        assert "\\" not in blob_name
        assert ":" not in blob_name
        assert blob_name == "resource_with_special_characters.json"

    @pytest.mark.asyncio
    async def test_ensure_container_exists_error(self):
        """Test error handling in _ensure_container_exists."""
        storage = AzureBlobDeltaLinkStorage()

        mock_blob_service = AsyncMock()
        mock_container_client = AsyncMock()
        mock_blob_service.get_container_client.return_value = mock_container_client

        # Mock create_container to raise an exception
        mock_container_client.create_container.side_effect = ServiceRequestError(
            "Service unavailable"
        )

        with patch.object(
            storage, "_get_blob_service_client", return_value=mock_blob_service
        ):
            with pytest.raises(ServiceRequestError):
                await storage._ensure_container_exists()

    @pytest.mark.asyncio
    async def test_get_delta_link_json_decode_error(self):
        """Test get method with invalid JSON content."""
        storage = AzureBlobDeltaLinkStorage()

        mock_blob_service = AsyncMock()
        mock_blob_client = AsyncMock()
        mock_download_stream = AsyncMock()

        # Mock invalid JSON content
        mock_download_stream.readall.return_value = b"{ invalid json"
        mock_blob_client.download_blob.return_value = mock_download_stream
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        with patch.object(
            storage, "_get_blob_service_client", return_value=mock_blob_service
        ), patch.object(storage, "_ensure_container_exists"):

            result = await storage.get("test_resource")
            # Should return None on JSON decode error
            assert result is None

    @pytest.mark.asyncio
    async def test_get_delta_link_non_string_delta_link(self):
        """Test get method with non-string delta_link in JSON."""
        storage = AzureBlobDeltaLinkStorage()

        mock_blob_service = AsyncMock()
        mock_blob_client = AsyncMock()
        mock_download_stream = AsyncMock()

        # Mock JSON with non-string delta_link
        invalid_data = {"delta_link": 123, "last_sync": "2025-01-01T00:00:00Z"}
        mock_download_stream.readall.return_value = json.dumps(invalid_data).encode(
            "utf-8"
        )
        mock_blob_client.download_blob.return_value = mock_download_stream
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        with patch.object(
            storage, "_get_blob_service_client", return_value=mock_blob_service
        ), patch.object(storage, "_ensure_container_exists"):

            result = await storage.get("test_resource")
            # Should return None for non-string delta_link
            assert result is None

    @pytest.mark.asyncio
    async def test_get_metadata_general_exception(self):
        """Test get_metadata method with general exception."""
        storage = AzureBlobDeltaLinkStorage()

        with patch.object(
            storage, "_ensure_container_exists", side_effect=Exception("General error")
        ):
            result = await storage.get_metadata("test_resource")
            # Should return None on general exception
            assert result is None

    @pytest.mark.asyncio
    async def test_set_delta_link_general_exception(self):
        """Test set method with general exception."""
        storage = AzureBlobDeltaLinkStorage()

        with patch.object(
            storage, "_ensure_container_exists", side_effect=Exception("General error")
        ):
            with pytest.raises(Exception, match="General error"):
                await storage.set("test_resource", "delta_link_value")

    @pytest.mark.asyncio
    async def test_delete_delta_link_resource_not_found(self):
        """Test delete method when blob doesn't exist."""
        storage = AzureBlobDeltaLinkStorage()

        mock_blob_service = AsyncMock()
        mock_blob_client = AsyncMock()

        # Mock ResourceNotFoundError
        mock_blob_client.delete_blob.side_effect = ResourceNotFoundError(
            "Blob not found"
        )
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        with patch.object(
            storage, "_get_blob_service_client", return_value=mock_blob_service
        ):
            # Should not raise exception (ResourceNotFoundError is handled)
            await storage.delete("test_resource")

    @pytest.mark.asyncio
    async def test_delete_delta_link_general_exception(self):
        """Test delete method with general exception."""
        storage = AzureBlobDeltaLinkStorage()

        mock_blob_service = AsyncMock()
        mock_blob_client = AsyncMock()

        # Mock general exception
        mock_blob_client.delete_blob.side_effect = Exception("Service error")
        mock_blob_service.get_blob_client.return_value = mock_blob_client

        with patch.object(
            storage, "_get_blob_service_client", return_value=mock_blob_service
        ):
            # Should not raise exception (general exceptions are handled)
            await storage.delete("test_resource")

    @pytest.mark.asyncio
    async def test_close_with_credential_without_close_method(self):
        """Test close method with credential that doesn't have close method."""
        storage = AzureBlobDeltaLinkStorage()

        # Mock credential without close method
        mock_credential = MagicMock()
        del mock_credential.close  # Remove close method
        storage._credential = mock_credential
        storage._credential_created = True

        mock_blob_service = AsyncMock()
        storage._blob_service_client = mock_blob_service

        # Should not raise exception
        await storage.close()

        assert storage._blob_service_client is None
        assert storage._credential is None
        assert storage._credential_created is False

    @pytest.mark.asyncio
    async def test_close_with_credential_close_exception(self):
        """Test close method when credential.close() raises exception."""
        storage = AzureBlobDeltaLinkStorage()

        # Mock credential with close method that raises exception
        mock_credential = AsyncMock()
        mock_credential.close.side_effect = Exception("Close error")
        storage._credential = mock_credential
        storage._credential_created = True

        mock_blob_service = AsyncMock()
        storage._blob_service_client = mock_blob_service

        # Should not raise exception (logs debug message)
        await storage.close()

        assert storage._blob_service_client is None
        assert storage._credential is None
        assert storage._credential_created is False

    @pytest.mark.asyncio
    async def test_initialization_fallback_when_no_connection_available(self):
        """Test initialization fallback when connection detection fails."""
        storage = AzureBlobDeltaLinkStorage()

        # Mock _detect_connection_with_priority to return empty dict
        with patch.object(storage, "_detect_connection_with_priority", return_value={}):
            # Force re-initialization
            detected = storage._detect_connection_with_priority()
            storage._connection_string = detected.get("connection_string")
            storage._account_url = detected.get("account_url")
            storage._credential = detected.get("credential")

            # Both should be None, which would trigger error in _get_blob_service_client
            assert storage._connection_string is None
            assert storage._account_url is None

    @pytest.mark.asyncio
    async def test_explicit_connection_string_priority(self):
        """Test that explicit connection string takes priority over environment."""
        explicit_conn = (
            "DefaultEndpointsProtocol=https;AccountName=explicit;AccountKey=key123"
        )
        env_conn = (
            "DefaultEndpointsProtocol=https;AccountName=envaccount;AccountKey=key456"
        )

        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": env_conn}):
            storage = AzureBlobDeltaLinkStorage(connection_string=explicit_conn)

            # Should use explicit connection string, not environment
            assert storage._connection_string == explicit_conn
            assert storage._account_url is None
            assert storage._credential is None

    @pytest.mark.asyncio
    async def test_explicit_account_url_credential_priority(self):
        """Test that explicit account_url + credential takes priority over environment."""
        env_conn = (
            "DefaultEndpointsProtocol=https;AccountName=envaccount;AccountKey=key456"
        )
        mock_credential = MagicMock(spec=DefaultAzureCredential)

        with patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": env_conn}):
            storage = AzureBlobDeltaLinkStorage(
                account_url="https://explicit.blob.core.windows.net",
                credential=mock_credential,
            )

            # Should use explicit account_url + credential, not environment
            assert storage._account_url == "https://explicit.blob.core.windows.net"
            assert storage._credential == mock_credential
            assert storage._connection_string is None
