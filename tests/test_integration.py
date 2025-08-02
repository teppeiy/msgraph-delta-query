"""Integration tests for msgraph-delta-query package."""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import Mock, AsyncMock, patch

from msgraph_delta_query import AsyncDeltaQueryClient, LocalFileDeltaLinkStorage


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests combining client and storage."""

    async def test_end_to_end_delta_query_with_storage(self):
        """Test complete end-to-end delta query with persistent storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create storage and client
            storage = LocalFileDeltaLinkStorage(folder=temp_dir)
            
            # Mock credential
            mock_credential = AsyncMock()
            token_mock = Mock()
            token_mock.token = "test_token_123"
            mock_credential.get_token.return_value = token_mock
            
            client = AsyncDeltaQueryClient(
                credential=mock_credential,
                delta_link_storage=storage
            )
            
            # First request - no delta link stored
            first_response = {
                "value": [{"id": "user1", "displayName": "John Doe"}],
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=first_token"
            }
            
            with patch.object(client, '_make_request') as mock_request:
                mock_request.return_value = (200, json.dumps(first_response), first_response)
                
                # Execute first delta query
                objects, delta_link, meta = await client.delta_query_all("users")
                
                assert len(objects) == 1
                assert objects[0]["id"] == "user1"
                assert delta_link == "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=first_token"
                assert meta.used_stored_deltalink is False
            
            # Verify delta link was stored
            stored_link = await storage.get("users")
            assert stored_link == "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=first_token"
            
            # Second request - should use stored delta link
            second_response = {
                "value": [{"id": "user2", "displayName": "Jane Smith"}],
                "@odata.deltaLink": "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=second_token"
            }
            
            # Create new client instance to simulate restart
            client2 = AsyncDeltaQueryClient(
                credential=mock_credential,
                delta_link_storage=storage
            )
            
            with patch.object(client2, '_make_request') as mock_request2:
                mock_request2.return_value = (200, json.dumps(second_response), second_response)
                
                # Execute second delta query
                objects2, delta_link2, meta2 = await client2.delta_query_all("users")
                
                assert len(objects2) == 1
                assert objects2[0]["id"] == "user2"
                assert delta_link2 == "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=second_token"
                assert meta2.used_stored_deltalink is True
                
                # Verify the stored delta token was used in the request
                called_url = mock_request2.call_args[0][0]
                assert "deltatoken=first_token" in called_url  # Works with both encoded and unencoded

    async def test_concurrent_clients_same_storage(self):
        """Test multiple clients using the same storage instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileDeltaLinkStorage(folder=temp_dir)
            
            # Mock credentials
            mock_credential1 = AsyncMock()
            mock_credential2 = AsyncMock()
            token_mock = Mock()
            token_mock.token = "test_token"
            mock_credential1.get_token.return_value = token_mock
            mock_credential2.get_token.return_value = token_mock
            
            client1 = AsyncDeltaQueryClient(credential=mock_credential1, delta_link_storage=storage)
            client2 = AsyncDeltaQueryClient(credential=mock_credential2, delta_link_storage=storage)
            
            # Store different delta links for different resources
            response1 = {
                "value": [{"id": "user1"}],
                "@odata.deltaLink": "https://example.com/users/delta?token=users_token"
            }
            
            response2 = {
                "value": [{"id": "group1"}],
                "@odata.deltaLink": "https://example.com/groups/delta?token=groups_token"
            }
            
            with patch.object(client1, '_make_request', return_value=(200, json.dumps(response1), response1)):
                with patch.object(client2, '_make_request', return_value=(200, json.dumps(response2), response2)):
                    
                    # Execute queries concurrently
                    results = await asyncio.gather(
                        client1.delta_query_all("users"),
                        client2.delta_query_all("groups")
                    )
                    
                    users_result, groups_result = results
                    
                    assert users_result[0][0]["id"] == "user1"
                    assert groups_result[0][0]["id"] == "group1"
            
            # Verify both delta links were stored separately
            assert await storage.get("users") == "https://example.com/users/delta?token=users_token"
            assert await storage.get("groups") == "https://example.com/groups/delta?token=groups_token"

    async def test_client_reset_delta_link_integration(self):
        """Test resetting delta link through client affects storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileDeltaLinkStorage(folder=temp_dir)
            
            # Store a delta link
            await storage.set("users", "https://example.com/delta?token=old_token")
            assert await storage.get("users") == "https://example.com/delta?token=old_token"
            
            # Create client and reset
            mock_credential = AsyncMock()
            client = AsyncDeltaQueryClient(credential=mock_credential, delta_link_storage=storage)
            
            await client.reset_delta_link("users")
            
            # Verify it's gone from storage
            assert await storage.get("users") is None

    async def test_storage_metadata_persistence(self):
        """Test that metadata is properly stored and retrievable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileDeltaLinkStorage(folder=temp_dir)
            
            mock_credential = AsyncMock()
            token_mock = Mock()
            token_mock.token = "test_token"
            mock_credential.get_token.return_value = token_mock
            
            client = AsyncDeltaQueryClient(credential=mock_credential, delta_link_storage=storage)
            
            response = {
                "value": [{"id": "user1", "displayName": "Test User"}],
                "@odata.deltaLink": "https://example.com/delta?token=test_token"
            }
            
            with patch.object(client, '_make_request', return_value=(200, json.dumps(response), response)):
                # Execute query with specific parameters
                objects, delta_link, meta = await client.delta_query_all(
                    "users",
                    select=["id", "displayName"],
                    filter="startswith(displayName,'Test')",
                    top=100
                )
            
            # Check that metadata was saved to storage file
            path = storage._get_resource_path("users")
            assert os.path.exists(path)
            
            with open(path, "r") as f:
                stored_data = json.load(f)
                
                assert stored_data["delta_link"] == "https://example.com/delta?token=test_token"
                assert stored_data["resource"] == "users"
                assert "last_updated" in stored_data
                assert "metadata" in stored_data
                
                # Check that query parameters were stored in metadata
                metadata = stored_data["metadata"]
                assert "resource_params" in metadata
                params = metadata["resource_params"]
                assert params["select"] == ["id", "displayName"]
                assert params["filter"] == "startswith(displayName,'Test')"
                assert params["top"] == 100

    async def test_error_handling_integration(self):
        """Test error handling across client and storage components."""
        # Test with invalid storage folder (read-only or non-existent parent)
        mock_credential = AsyncMock()
        
        # Create storage with invalid path
        invalid_storage = LocalFileDeltaLinkStorage(folder="/invalid/path/that/does/not/exist")
        client = AsyncDeltaQueryClient(credential=mock_credential, delta_link_storage=invalid_storage)
        
        # This should handle storage errors gracefully
        try:
            await client.reset_delta_link("users")
            # Should not raise exception even if delete fails
        except Exception:
            pytest.fail("reset_delta_link should handle storage errors gracefully")

    async def test_client_cleanup_with_storage(self):
        """Test that client cleanup works properly with storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileDeltaLinkStorage(folder=temp_dir)
            
            mock_credential = AsyncMock()
            client = AsyncDeltaQueryClient(credential=mock_credential, delta_link_storage=storage)
            
            # Initialize client
            await client._initialize()
            assert client._initialized
            assert client._session is not None
            
            # Close client
            await client._internal_close()
            assert client._closed
            assert client._session is None
            
            # Storage should still be functional
            await storage.set("test", "https://example.com")
            result = await storage.get("test")
            assert result == "https://example.com"
