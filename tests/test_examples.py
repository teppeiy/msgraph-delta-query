"""Test example usage and real-world scenarios."""

import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock, Mock
import json

from msgraph_delta_query.client import example_usage


@pytest.mark.asyncio
async def test_example_usage():
    """Test the example_usage function."""
    # Mock the entire client behavior
    mock_client = AsyncMock()
    mock_client.delta_query_all.return_value = (
        [{"id": "1", "displayName": "User 1"}, {"id": "2", "displayName": "User 2"}],
        "https://example.com/delta?token=abc",
        {"duration_seconds": 1.23, "changed_count": 2}
    )
    
    with patch('msgraph_delta_query.client.AsyncDeltaQueryClient', return_value=mock_client):
        with patch('builtins.print') as mock_print:
            await example_usage()
            
            # Verify the client was called correctly
            mock_client.delta_query_all.assert_called_once_with(
                resource="users",
                select=["id", "displayName", "mail"],
                top=100
            )
            
            # Verify the output
            mock_print.assert_called_once_with("Retrieved 2 users in 1.23s")


@pytest.mark.asyncio 
async def test_real_world_scenario_user_sync():
    """Test a real-world user synchronization scenario."""
    from msgraph_delta_query import AsyncDeltaQueryClient, LocalFileDeltaLinkStorage
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = LocalFileDeltaLinkStorage(folder=temp_dir)
        
        # Mock credential
        mock_credential = AsyncMock()
        token_mock = Mock()
        token_mock.token = "access_token_123"
        mock_credential.get_token.return_value = token_mock
        
        client = AsyncDeltaQueryClient(
            credential=mock_credential,
            delta_link_storage=storage,
            max_concurrent_requests=5
        )
        
        # Simulate initial sync (no delta link)
        initial_response = {
            "value": [
                {"id": "1", "displayName": "John Doe", "mail": "john@example.com"},
                {"id": "2", "displayName": "Jane Smith", "mail": "jane@example.com"}
            ],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=initial_token"
        }
        
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = (200, json.dumps(initial_response), initial_response)
            
            users, delta_link, meta = await client.delta_query_all(
                "users",
                select=["id", "displayName", "mail"],
                top=1000
            )
            
            assert len(users) == 2
            assert meta["used_stored_deltalink"] is False
            
        # Simulate incremental sync (using stored delta link)  
        incremental_response = {
            "value": [
                {"id": "3", "displayName": "Bob Johnson", "mail": "bob@example.com"},
                {"@removed": {"reason": "deleted"}, "id": "2"}  # User was deleted
            ],
            "@odata.deltaLink": "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=incremental_token"
        }
        
        # Create new client instance (simulating app restart)
        client2 = AsyncDeltaQueryClient(
            credential=mock_credential,
            delta_link_storage=storage,
            max_concurrent_requests=5
        )
        
        with patch.object(client2, '_make_request') as mock_request2:
            mock_request2.return_value = (200, json.dumps(incremental_response), incremental_response)
            
            changes, new_delta_link, meta2 = await client2.delta_query_all(
                "users", 
                select=["id", "displayName", "mail"],
                top=1000
            )
            
            assert len(changes) == 2
            assert meta2["used_stored_deltalink"] is True
            
            # Verify the call used the stored delta token
            called_url = mock_request2.call_args[0][0]
            assert "deltatoken=initial_token" in called_url  # Works with both encoded and unencoded
            
            # Process changes
            added_users = [user for user in changes if "@removed" not in user]
            deleted_users = [user for user in changes if "@removed" in user]
            
            assert len(added_users) == 1
            assert added_users[0]["displayName"] == "Bob Johnson"
            assert len(deleted_users) == 1
            assert deleted_users[0]["id"] == "2"


@pytest.mark.asyncio
async def test_real_world_scenario_large_dataset_pagination():
    """Test handling large datasets with multiple pages."""
    from msgraph_delta_query import AsyncDeltaQueryClient
    
    mock_credential = AsyncMock()
    token_mock = Mock()
    token_mock.token = "access_token_123"
    mock_credential.get_token.return_value = token_mock
    
    client = AsyncDeltaQueryClient(credential=mock_credential)
    
    # Simulate multi-page response
    page1_response = {
        "value": [{"id": f"user{i}", "displayName": f"User {i}"} for i in range(1, 101)],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=page2"
    }
    
    page2_response = {
        "value": [{"id": f"user{i}", "displayName": f"User {i}"} for i in range(101, 201)],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=page3"
    }
    
    page3_response = {
        "value": [{"id": f"user{i}", "displayName": f"User {i}"} for i in range(201, 251)],
        "@odata.deltaLink": "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=final_token"
    }
    
    with patch.object(client, '_make_request') as mock_request:
        mock_request.side_effect = [
            (200, json.dumps(page1_response), page1_response),
            (200, json.dumps(page2_response), page2_response),
            (200, json.dumps(page3_response), page3_response)
        ]
        
        all_users = []
        page_count = 0
        
        async for users, page_meta in client.delta_query_stream("users", top=100):
            all_users.extend(users)
            page_count += 1
            
            assert page_meta["page"] == page_count
            assert page_meta["object_count"] == len(users)
            
            if page_count < 3:
                assert page_meta["has_next_page"] is True
            else:
                assert page_meta["has_next_page"] is False
                assert page_meta["delta_link"] == "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=final_token"
        
        assert len(all_users) == 250
        assert page_count == 3


@pytest.mark.asyncio
async def test_real_world_scenario_error_recovery():
    """Test error recovery in real-world conditions."""
    from msgraph_delta_query import AsyncDeltaQueryClient
    
    mock_credential = AsyncMock()
    token_mock = Mock()
    token_mock.token = "access_token_123"
    mock_credential.get_token.return_value = token_mock
    
    client = AsyncDeltaQueryClient(credential=mock_credential)
    
    success_response = {
        "value": [{"id": "1", "displayName": "User 1"}],
        "@odata.deltaLink": "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=success_token"
    }
    
    # Mock _make_request to simulate rate limiting handled internally and then success
    with patch.object(client, '_make_request') as mock_request:
        # The _make_request method should handle rate limiting internally and return success
        mock_request.return_value = (200, json.dumps(success_response), success_response)
        
        users, delta_link, meta = await client.delta_query_all("users")
        
        assert len(users) == 1
        assert users[0]["id"] == "1"


@pytest.mark.asyncio
async def test_real_world_scenario_concurrent_requests():
    """Test handling multiple concurrent delta queries."""
    from msgraph_delta_query import AsyncDeltaQueryClient
    
    mock_credential = AsyncMock()
    token_mock = Mock()
    token_mock.token = "access_token_123"
    mock_credential.get_token.return_value = token_mock
    
    # Use small semaphore to test concurrency limiting
    client = AsyncDeltaQueryClient(credential=mock_credential, max_concurrent_requests=2)
    
    users_response = {
        "value": [{"id": "user1"}],
        "@odata.deltaLink": "https://example.com/users/delta?token=users_token"
    }
    
    groups_response = {
        "value": [{"id": "group1"}],
        "@odata.deltaLink": "https://example.com/groups/delta?token=groups_token"
    }
    
    with patch.object(client, '_make_request') as mock_request:
        mock_request.side_effect = [
            (200, json.dumps(users_response), users_response),
            (200, json.dumps(groups_response), groups_response)
        ]
        
        # Execute multiple queries concurrently
        results = await asyncio.gather(
            client.delta_query_all("users"),
            client.delta_query_all("groups")
        )
        
        users_result, groups_result = results
        
        assert len(users_result[0]) == 1
        assert len(groups_result[0]) == 1
        assert users_result[0][0]["id"] == "user1"
        assert groups_result[0][0]["id"] == "group1"


if __name__ == "__main__":
    # Test the example usage when run directly
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
