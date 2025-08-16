#!/usr/bin/env python3
"""
Test pagination with proper response types.

These tests specifically target the pagination bug we found where the wrong
DeltaGetResponse type was being used for different resource types.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from msgraph_delta_query import AsyncDeltaQueryClient
from msgraph_delta_query.storage import LocalFileDeltaLinkStorage


class TestPaginationResponseTypes:
    """Test pagination with correct response types for different resources."""

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
        async def async_none(*args, **kwargs):
            return None
        async def async_noop(*args, **kwargs):
            pass
        storage.get = AsyncMock(side_effect=async_none)
        storage.set = AsyncMock(side_effect=async_noop)
        storage.delete = AsyncMock(side_effect=async_noop)
        storage.close = AsyncMock(side_effect=async_noop)
        return storage

    def create_mock_user_response(self, user_count: int = 5, has_next: bool = False):
        """Create a mock user response with proper User objects."""
        mock_response = Mock()

        # Create mock User objects with proper odata_type
        mock_users = []
        for i in range(user_count):
            user = Mock()
            user.odata_type = "#microsoft.graph.user"
            user.display_name = f"User {i + 1}"
            user.user_principal_name = f"user{i + 1}@example.com"
            user.id = f"user-{i + 1}-id"
            user.additional_data = {}
            # Don't add app_id to user objects
            mock_users.append(user)

        mock_response.value = mock_users
        mock_response.odata_next_link = (
            "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=next_page_token"
            if has_next
            else None
        )
        mock_response.odata_delta_link = (
            None
            if has_next
            else "https://graph.microsoft.com/v1.0/users/delta?deltatoken=final_token"
        )

        return mock_response

    def create_mock_application_response(
        self, app_count: int = 5, has_next: bool = False
    ):
        """Create a mock application response with proper Application objects."""
        mock_response = Mock()

        # Create mock Application objects with proper odata_type
        mock_apps = []
        for i in range(app_count):
            app = Mock()
            app.odata_type = "#microsoft.graph.application"
            app.display_name = f"App {i + 1}"
            app.app_id = f"app-{i + 1}-id"
            app.id = f"application-{i + 1}-id"
            app.additional_data = {}
            # Don't add user_principal_name to app objects
            mock_apps.append(app)

        mock_response.value = mock_apps
        mock_response.odata_next_link = (
            "https://graph.microsoft.com/v1.0/applications/delta?$skiptoken=next_page_token"
            if has_next
            else None
        )
        mock_response.odata_delta_link = (
            None
            if has_next
            else "https://graph.microsoft.com/v1.0/applications/delta?deltatoken=final_token"
        )

        return mock_response

    @pytest.mark.asyncio
    async def test_users_pagination_uses_correct_response_type(
        self, mock_credential, mock_storage
    ):
        """Test that users pagination uses the correct Users DeltaGetResponse type."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the graph client
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Create mock responses for pagination
        first_response = self.create_mock_user_response(user_count=3, has_next=True)
        second_response = self.create_mock_user_response(user_count=2, has_next=False)

        # Mock the request builder for initial request
        mock_request_builder = Mock()
        client._get_delta_request_builder = Mock(return_value=mock_request_builder)

        # Mock the initial request execution
        async def mock_execute_delta_request(*args, **kwargs):
            return first_response, False

        client._execute_delta_request = Mock(side_effect=mock_execute_delta_request)

        # Mock the request adapter for pagination
        mock_request_adapter = Mock()
        mock_graph_client.request_adapter = mock_request_adapter
        mock_request_adapter.send_async = AsyncMock(return_value=second_response)

        # Track which response type is used in pagination
        captured_response_type = None

        async def capture_send_async(request_info, response_type, error_map):
            nonlocal captured_response_type
            captured_response_type = response_type
            return second_response

        mock_request_adapter.send_async = capture_send_async

        # Execute the delta query stream
        pages_processed = 0
        total_users = 0

        async for objects, page_meta in client.delta_query_stream(resource="users"):
            pages_processed += 1
            total_users += len(objects)

            # Verify all objects are users
            for obj in objects:
                assert obj.odata_type == "#microsoft.graph.user"
                assert hasattr(obj, "user_principal_name")

        # Verify we processed both pages
        assert pages_processed == 2
        assert total_users == 5

        # Verify the correct response type was used for pagination
        assert captured_response_type is not None
        assert captured_response_type.__module__.endswith(
            "users.delta.delta_get_response"
        )

    @pytest.mark.asyncio
    async def test_applications_pagination_uses_correct_response_type(
        self, mock_credential, mock_storage
    ):
        """Test that applications pagination uses the correct Applications DeltaGetResponse type."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the graph client
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Create mock responses for pagination
        first_response = self.create_mock_application_response(
            app_count=3, has_next=True
        )
        second_response = self.create_mock_application_response(
            app_count=2, has_next=False
        )

        # Mock the request builder for initial request
        mock_request_builder = Mock()
        client._get_delta_request_builder = Mock(return_value=mock_request_builder)

        # Mock the initial request execution
        async def mock_execute_delta_request(*args, **kwargs):
            return first_response, False

        client._execute_delta_request = Mock(side_effect=mock_execute_delta_request)

        # Mock the request adapter for pagination
        mock_request_adapter = Mock()
        mock_graph_client.request_adapter = mock_request_adapter

        # Track which response type is used in pagination
        captured_response_type = None

        async def capture_send_async(request_info, response_type, error_map):
            nonlocal captured_response_type
            captured_response_type = response_type
            return second_response

        mock_request_adapter.send_async = capture_send_async

        # Execute the delta query stream
        pages_processed = 0
        total_apps = 0

        async for objects, page_meta in client.delta_query_stream(
            resource="applications"
        ):
            pages_processed += 1
            total_apps += len(objects)

            # Verify all objects are applications
            for obj in objects:
                assert obj.odata_type == "#microsoft.graph.application"
                assert hasattr(obj, "app_id")

        # Verify we processed both pages
        assert pages_processed == 2
        assert total_apps == 5

        # Verify the correct response type was used for pagination
        assert captured_response_type is not None
        assert captured_response_type.__module__.endswith(
            "applications.delta.delta_get_response"
        )

    @pytest.mark.asyncio
    async def test_stored_delta_link_uses_correct_response_type(
        self, mock_credential, mock_storage
    ):
        """Test that stored delta link usage also uses the correct response type."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock storage to return a stored delta link
        stored_delta_link = (
            "https://graph.microsoft.com/v1.0/users/delta?deltatoken=stored_token"
        )
        async def mock_get(*args, **kwargs):
            return (stored_delta_link, {"metadata": "test"})
        mock_storage.get = AsyncMock(side_effect=mock_get)

        # Mock the graph client
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Create mock response
        response = self.create_mock_user_response(user_count=3, has_next=False)

        # Mock the request adapter
        mock_request_adapter = Mock()
        mock_graph_client.request_adapter = mock_request_adapter

        # Track which response type is used
        captured_response_type = None

        async def capture_send_async(request_info, response_type, error_map):
            nonlocal captured_response_type
            captured_response_type = response_type
            return response

        mock_request_adapter.send_async = capture_send_async

        # Execute the delta query stream
        pages_processed = 0

        async for objects, page_meta in client.delta_query_stream(resource="users"):
            pages_processed += 1

            # Verify all objects are users
            for obj in objects:
                assert obj.odata_type == "#microsoft.graph.user"

        # Verify we processed the page
        assert pages_processed == 1

        # Verify the correct response type was used for stored delta link
        assert captured_response_type is not None
        assert captured_response_type.__module__.endswith(
            "users.delta.delta_get_response"
        )

    @pytest.mark.asyncio
    async def test_mixed_object_types_bug_prevention(
        self, mock_credential, mock_storage
    ):
        """Test that verifies the bug where wrong response types caused mixed object types."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the graph client
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # This test simulates what would happen with the bug:
        # Users query on first page, but applications response type used on second page
        first_response = self.create_mock_user_response(user_count=3, has_next=True)

        # With the bug, this would be Applications even though we're querying users
        # But now it should be the correct Users response
        second_response = self.create_mock_user_response(user_count=2, has_next=False)

        # Mock the request builder for initial request
        mock_request_builder = Mock()
        client._get_delta_request_builder = Mock(return_value=mock_request_builder)

        # Mock the initial request execution
        async def mock_execute_delta_request(*args, **kwargs):
            return first_response, False

        client._execute_delta_request = Mock(side_effect=mock_execute_delta_request)

        # Mock the request adapter for pagination
        mock_request_adapter = Mock()
        mock_graph_client.request_adapter = mock_request_adapter
        mock_request_adapter.send_async = AsyncMock(return_value=second_response)

        # Execute the delta query stream
        all_object_types = set()

        async for objects, page_meta in client.delta_query_stream(resource="users"):
            for obj in objects:
                all_object_types.add(obj.odata_type)

        # Verify all objects are the same type (users only)
        assert len(all_object_types) == 1
        assert "#microsoft.graph.user" in all_object_types
        assert "#microsoft.graph.application" not in all_object_types

    @pytest.mark.asyncio
    async def test_unsupported_resource_type_error(self, mock_credential, mock_storage):
        """Test that unsupported resource types raise appropriate errors in pagination."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the graph client
        mock_graph_client = Mock()
        client._graph_client = mock_graph_client
        client._initialized = True

        # Create a mock response with next page
        first_response = Mock()
        first_response.value = []
        first_response.odata_next_link = (
            "https://graph.microsoft.com/v1.0/unsupported/delta?$skiptoken=token"
        )
        first_response.odata_delta_link = None

        # Mock the request builder for initial request
        mock_request_builder = Mock()
        client._get_delta_request_builder = Mock(return_value=mock_request_builder)

        # Mock the initial request execution
        async def mock_execute_delta_request(*args, **kwargs):
            return first_response, False

        client._execute_delta_request = Mock(side_effect=mock_execute_delta_request)

        # Mock the request adapter
        mock_request_adapter = Mock()
        mock_graph_client.request_adapter = mock_request_adapter

        # This should raise an error when trying to get the response type for pagination
        with pytest.raises(ValueError, match="Unsupported resource type"):
            async for objects, page_meta in client.delta_query_stream(
                resource="unsupported"
            ):
                pass  # Should not reach here


if __name__ == "__main__":
    pytest.main([__file__])
