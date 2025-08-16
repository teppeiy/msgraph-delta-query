#!/usr/bin/env python3
"""
Integration test for pagination bug regression.

This test specifically targets the bug where users delta queries
returned application objects on subsequent pages due to wrong
DeltaGetResponse type usage in pagination.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from kiota_abstractions.request_information import RequestInformation
from kiota_abstractions.method import Method

from msgraph_delta_query import AsyncDeltaQueryClient
from msgraph_delta_query.storage import LocalFileDeltaLinkStorage


class TestPaginationBugRegression:
    """Regression tests for the critical pagination bug."""

    @pytest.fixture
    def mock_credential(self):
        """Mock Azure credential."""
        mock_cred = Mock()
        mock_cred.get_token = AsyncMock()
        mock_cred.get_token.return_value.token = "fake_token"
        mock_cred.close = AsyncMock()
        return mock_cred

    @pytest.fixture
    def mock_storage(self):
        """Mock delta link storage."""
        storage = Mock(spec=LocalFileDeltaLinkStorage)
        storage.get = AsyncMock(return_value=None)
        storage.set = AsyncMock()
        storage.delete = AsyncMock()
        storage.close = AsyncMock()
        return storage

    @pytest.mark.asyncio
    async def test_pagination_import_path_verification(
        self, mock_credential, mock_storage
    ):
        """Test that verifies the correct behavior without direct import tracking."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the graph client
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Create first page response with next link
        first_response = Mock()
        mock_user = Mock()
        mock_user.odata_type = "#microsoft.graph.user"
        mock_user.display_name = "Test User"
        mock_user.user_principal_name = "test@example.com"
        mock_user.additional_data = {}

        first_response.value = [mock_user]
        first_response.odata_next_link = (
            "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=page2"
        )
        first_response.odata_delta_link = None

        # Mock the request builder
        mock_request_builder = Mock()
        client._get_delta_request_builder = Mock(return_value=mock_request_builder)

        # Mock initial request
        async def mock_execute_delta_request(*args, **kwargs):
            return first_response, False

        client._execute_delta_request = Mock(side_effect=mock_execute_delta_request)

        # Create second page response
        second_response = Mock()
        second_user = Mock()
        second_user.odata_type = "#microsoft.graph.user"
        second_user.display_name = "Second User"
        second_user.user_principal_name = "second@example.com"
        second_user.additional_data = {}

        second_response.value = [second_user]
        second_response.odata_next_link = None
        second_response.odata_delta_link = (
            "https://graph.microsoft.com/v1.0/users/delta?deltatoken=final"
        )

        # Mock request adapter
        mock_request_adapter = Mock()
        mock_graph_client.request_adapter = mock_request_adapter

        # Mock the response parsing to return our second response
        async def mock_send_async(request_info, response_type, error_map):
            # Verify we're using the correct response type for users
            assert "users.delta.delta_get_response" in str(response_type)
            return second_response

        mock_request_adapter.send_async = mock_send_async

        # Execute the delta query stream and verify it completes with proper types
        result = []
        async for objects, page_meta in client.delta_query_stream("users"):
            result.append(objects)
            # Verify all objects are user objects with proper attributes
            for obj in objects:
                assert hasattr(obj, "odata_type"), "Object should have odata_type"
                assert (
                    obj.odata_type == "#microsoft.graph.user"
                ), f"Expected user object, got {obj.odata_type}"

        # Verify we got the expected results - this test validates the fix works
        assert len(result) >= 1

        await client.close()

    @pytest.mark.asyncio
    async def test_applications_vs_users_response_type_isolation(
        self, mock_credential, mock_storage
    ):
        """Test that applications and users use completely different response types."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the graph client
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Test data for both resource types
        test_scenarios = [
            ("users", "#microsoft.graph.user", "users.delta.delta_get_response"),
            (
                "applications",
                "#microsoft.graph.application",
                "applications.delta.delta_get_response",
            ),
        ]

        for (
            resource_type,
            expected_odata_type,
            expected_module_suffix,
        ) in test_scenarios:
            # Reset mocks for each scenario
            mock_graph_client.reset_mock()

            # Create response for this resource type
            response = Mock()
            mock_obj = Mock()
            mock_obj.odata_type = expected_odata_type
            mock_obj.additional_data = {}

            if resource_type == "users":
                mock_obj.display_name = "Test User"
                mock_obj.user_principal_name = "test@example.com"
            else:
                mock_obj.display_name = "Test App"
                mock_obj.app_id = "test-app-id"

            response.value = [mock_obj]
            response.odata_next_link = f"https://graph.microsoft.com/v1.0/{resource_type}/delta?$skiptoken=page2"
            response.odata_delta_link = None

            # Mock request builder
            mock_request_builder = Mock()
            client._get_delta_request_builder = Mock(return_value=mock_request_builder)

            # Mock initial request
            async def mock_execute_delta_request(*args, **kwargs):
                return response, False

            client._execute_delta_request = Mock(side_effect=mock_execute_delta_request)

            # Create second page
            second_response = Mock()
            second_response.value = []  # Empty to end pagination
            second_response.odata_next_link = None
            second_response.odata_delta_link = f"https://graph.microsoft.com/v1.0/{resource_type}/delta?deltatoken=final"

            # Verify correct response type is used
            mock_request_adapter = Mock()
            mock_graph_client.request_adapter = mock_request_adapter

            async def verify_response_type(request_info, response_type, error_map):
                # This is the critical test - verify the response type matches the resource
                assert expected_module_suffix in response_type.__module__
                return second_response

            mock_request_adapter.send_async = verify_response_type

            # Execute test for this resource type
            async for objects, page_meta in client.delta_query_stream(
                resource=resource_type
            ):
                for obj in objects:
                    assert obj.odata_type == expected_odata_type

    @pytest.mark.asyncio
    async def test_bug_reproduction_attempt(self, mock_credential, mock_storage):
        """Test that attempts to reproduce the original bug scenario."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the graph client
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Simulate the bug scenario: query users but get wrong response type on page 2

        # Page 1: Users (this worked correctly even with the bug)
        first_response = Mock()
        user1 = Mock()
        user1.odata_type = "#microsoft.graph.user"
        user1.display_name = "User 1"
        user1.user_principal_name = "user1@example.com"
        user1.additional_data = {}

        first_response.value = [user1]
        first_response.odata_next_link = (
            "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=page2"
        )
        first_response.odata_delta_link = None

        # Mock request builder
        mock_request_builder = Mock()
        client._get_delta_request_builder = Mock(return_value=mock_request_builder)

        # Mock initial request
        async def mock_execute_delta_request(*args, **kwargs):
            return first_response, False

        client._execute_delta_request = Mock(side_effect=mock_execute_delta_request)

        # Mock request adapter
        mock_request_adapter = Mock()
        mock_graph_client.request_adapter = mock_request_adapter

        # Track what happens in pagination
        pagination_calls = []

        async def track_pagination(request_info, response_type, error_map):
            pagination_calls.append(
                {
                    "url": request_info.url_template,
                    "response_type_module": response_type.__module__,
                }
            )

            # Return proper user response (this is what the fix ensures)
            page2_response = Mock()
            user2 = Mock()
            user2.odata_type = "#microsoft.graph.user"
            user2.display_name = "User 2"
            user2.user_principal_name = "user2@example.com"
            user2.additional_data = {}

            page2_response.value = [user2]
            page2_response.odata_next_link = None
            page2_response.odata_delta_link = (
                "https://graph.microsoft.com/v1.0/users/delta?deltatoken=final"
            )

            return page2_response

        mock_request_adapter.send_async = track_pagination

        # Execute the test
        all_objects = []
        all_types = set()

        async for objects, page_meta in client.delta_query_stream(resource="users"):
            all_objects.extend(objects)
            for obj in objects:
                all_types.add(obj.odata_type)

        # Verify the fix works
        assert len(all_objects) == 2  # Two pages with one user each
        assert len(all_types) == 1  # Only one object type
        assert "#microsoft.graph.user" in all_types
        assert (
            "#microsoft.graph.application" not in all_types
        )  # Bug would have caused this

        # Verify pagination used correct response type
        assert len(pagination_calls) == 1
        assert (
            "users.delta.delta_get_response"
            in pagination_calls[0]["response_type_module"]
        )
        assert (
            "applications.delta.delta_get_response"
            not in pagination_calls[0]["response_type_module"]
        )


if __name__ == "__main__":
    pytest.main([__file__])
