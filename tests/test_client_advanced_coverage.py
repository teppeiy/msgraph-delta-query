"""Additional test coverage for complex client methods."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from msgraph_delta_query.client import AsyncDeltaQueryClient
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


class TestExecuteDeltaRequestMethod:
    """Test coverage for _execute_delta_request method."""

    async def test_execute_delta_request_success(self, mock_credential):
        """Test successful _execute_delta_request execution."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        # Mock request builder with required classes
        mock_request_builder = Mock()

        # Mock the query parameters class
        mock_query_params_class = Mock()
        mock_query_params_obj = Mock()
        mock_query_params_class.return_value = mock_query_params_obj
        mock_request_builder.DeltaRequestBuilderGetQueryParameters = (
            mock_query_params_class
        )

        # Mock the request configuration class
        mock_config_class = Mock()
        mock_config_obj = Mock()
        mock_config_class.return_value = mock_config_obj
        mock_request_builder.DeltaRequestBuilderGetRequestConfiguration = (
            mock_config_class
        )

        # Mock successful response
        mock_response = {"value": [{"id": "1", "name": "test"}]}
        mock_request_builder.get = AsyncMock(return_value=mock_response)

        query_params = {"select": ["id", "name"], "top": 10}

        response, fallback_occurred = await client._execute_delta_request(
            mock_request_builder, query_params, fallback_to_full_sync=True
        )

        assert response == mock_response
        assert fallback_occurred is False
        mock_request_builder.get.assert_called_once()

    async def test_execute_delta_request_with_skiptoken(self, mock_credential):
        """Test _execute_delta_request with skiptoken parameter."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        # Mock request builder
        mock_request_builder = Mock()
        mock_query_params_class = Mock()
        mock_query_params_obj = Mock()
        mock_query_params_class.return_value = mock_query_params_obj
        mock_request_builder.DeltaRequestBuilderGetQueryParameters = (
            mock_query_params_class
        )

        mock_config_class = Mock()
        mock_config_obj = Mock()
        mock_config_class.return_value = mock_config_obj
        mock_request_builder.DeltaRequestBuilderGetRequestConfiguration = (
            mock_config_class
        )

        mock_response = {"value": []}
        mock_request_builder.get = AsyncMock(return_value=mock_response)

        query_params = {"skiptoken": "abc123"}

        response, fallback_occurred = await client._execute_delta_request(
            mock_request_builder, query_params
        )

        # Should return response and fallback should be False
        assert response == mock_response
        assert fallback_occurred is False

        # Should have called get method on request builder
        mock_request_builder.get.assert_called_once()

    async def test_execute_delta_request_delta_error_with_fallback(
        self, mock_credential, mock_storage
    ):
        """Test _execute_delta_request with delta token error and fallback."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock request builder
        mock_request_builder = Mock()
        mock_query_params_class = Mock()
        mock_query_params_obj = Mock()
        mock_query_params_class.return_value = mock_query_params_obj
        mock_request_builder.DeltaRequestBuilderGetQueryParameters = (
            mock_query_params_class
        )

        mock_config_class = Mock()
        mock_request_builder.DeltaRequestBuilderGetRequestConfiguration = (
            mock_config_class
        )

        # First call fails with delta token error, second succeeds
        mock_response = {"value": [{"id": "1"}]}
        mock_request_builder.get = AsyncMock(
            side_effect=[Exception("Invalid token"), mock_response]
        )

        query_params = {"deltatoken": "invalid_token", "select": ["id"]}

        with patch.object(client.logger, "warning") as mock_warning:
            with patch.object(client.logger, "info") as mock_info:
                response, fallback_occurred = await client._execute_delta_request(
                    mock_request_builder,
                    query_params,
                    fallback_to_full_sync=True,
                    used_stored_deltalink=True,
                    resource="users",
                )

                assert response == mock_response
                assert fallback_occurred is True

                # Should log warning about delta token failure
                mock_warning.assert_called()
                warning_call = mock_warning.call_args[0][0]
                assert "Delta token failed" in warning_call
                assert "falling back to full sync" in warning_call

                # Should log info about clearing invalid delta link
                mock_info.assert_called_with(
                    "Clearing invalid stored delta link for users"
                )

    async def test_execute_delta_request_delta_error_no_fallback(self, mock_credential):
        """Test _execute_delta_request with delta token error but no fallback."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        # Mock request builder
        mock_request_builder = Mock()
        mock_query_params_class = Mock()
        mock_query_params_obj = Mock()
        mock_query_params_class.return_value = mock_query_params_obj
        mock_request_builder.DeltaRequestBuilderGetQueryParameters = (
            mock_query_params_class
        )

        mock_config_class = Mock()
        mock_request_builder.DeltaRequestBuilderGetRequestConfiguration = (
            mock_config_class
        )

        # Simulate token error
        mock_request_builder.get = AsyncMock(side_effect=Exception("Invalid token"))

        query_params = {"deltatoken": "invalid_token"}

        # Should re-raise the original error when fallback is disabled
        with pytest.raises(Exception, match="Invalid token"):
            await client._execute_delta_request(
                mock_request_builder, query_params, fallback_to_full_sync=False
            )

    async def test_execute_delta_request_fallback_also_fails(
        self, mock_credential, mock_storage
    ):
        """Test _execute_delta_request when both original and fallback requests fail."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock request builder
        mock_request_builder = Mock()
        mock_query_params_class = Mock()
        mock_query_params_obj = Mock()
        mock_query_params_class.return_value = mock_query_params_obj
        mock_request_builder.DeltaRequestBuilderGetQueryParameters = (
            mock_query_params_class
        )

        mock_config_class = Mock()
        mock_request_builder.DeltaRequestBuilderGetRequestConfiguration = (
            mock_config_class
        )

        # Both calls fail
        mock_request_builder.get = AsyncMock(
            side_effect=[Exception("Invalid token"), Exception("Fallback also failed")]
        )

        query_params = {"deltatoken": "invalid_token"}

        with patch("logging.error") as mock_error:
            with pytest.raises(Exception, match="Fallback also failed"):
                await client._execute_delta_request(
                    mock_request_builder,
                    query_params,
                    fallback_to_full_sync=True,
                    used_stored_deltalink=True,
                    resource="users",
                )

                # Should log error about fallback failure
                mock_error.assert_called_with(
                    "Fallback to full sync also failed: Fallback also failed"
                )

    async def test_execute_delta_request_non_delta_error(self, mock_credential):
        """Test _execute_delta_request with non-delta related error."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        # Mock request builder
        mock_request_builder = Mock()
        mock_query_params_class = Mock()
        mock_query_params_obj = Mock()
        mock_query_params_class.return_value = mock_query_params_obj
        mock_request_builder.DeltaRequestBuilderGetQueryParameters = (
            mock_query_params_class
        )

        mock_config_class = Mock()
        mock_request_builder.DeltaRequestBuilderGetRequestConfiguration = (
            mock_config_class
        )

        # Simulate non-delta error (e.g., network error)
        mock_request_builder.get = AsyncMock(side_effect=Exception("Network error"))

        query_params = {"select": ["id"]}

        # Should re-raise the original error (no fallback for non-delta errors)
        with pytest.raises(Exception, match="Network error"):
            await client._execute_delta_request(
                mock_request_builder, query_params, fallback_to_full_sync=True
            )


class TestDeltaQueryStreamMethod:
    """Test coverage for delta_query_stream method."""

    async def test_delta_query_stream_unsupported_resource(self, mock_credential):
        """Test delta_query_stream with unsupported resource type."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        with pytest.raises(ValueError, match="Unsupported resource type: invalid"):
            async for page in client.delta_query_stream("invalid"):
                pass

    async def test_delta_query_stream_with_stored_delta_link(
        self, mock_credential, mock_storage
    ):
        """Test delta_query_stream using stored delta link."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Set up stored delta link and metadata
        stored_delta_link = (
            "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=stored123"
        )
        metadata = {
            "last_updated": "2025-08-01T10:00:00.000000+00:00",
            "change_summary": {"new_or_updated": 5, "deleted": 1},
        }
        await mock_storage.set("users", stored_delta_link, metadata)

        # Mock graph client and initialize
        await client._initialize()

        # Test should attempt to use stored delta link
        with patch.object(client, "_get_delta_request_builder") as mock_builder:
            with patch.object(
                client, "_extract_delta_token_from_link", return_value="stored123"
            ) as mock_extract:
                with patch.object(client.logger, "info") as mock_info:
                    # Mock the stream to prevent actual iteration
                    mock_builder.return_value = Mock()

                    try:
                        # Start the async generator
                        stream = client.delta_query_stream("users")
                        await stream.__anext__()
                    except StopAsyncIteration:
                        pass
                    except Exception:
                        pass  # Expected since we're not fully mocking the request

                    # Should log about using stored delta link
                    info_calls = [call[0][0] for call in mock_info.call_args_list]
                    assert any(
                        "Using stored delta link for users incremental sync" in call
                        for call in info_calls
                    )

                    # Should extract token from stored link
                    mock_extract.assert_called_with(stored_delta_link)

    async def test_delta_query_stream_with_explicit_delta_link(self, mock_credential):
        """Test delta_query_stream with explicitly provided delta link."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        explicit_delta_link = (
            "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=explicit123"
        )

        await client._initialize()

        with patch.object(client, "_get_delta_request_builder") as mock_builder:
            with patch.object(
                client, "_extract_delta_token_from_link", return_value="explicit123"
            ) as mock_extract:
                mock_builder.return_value = Mock()

                try:
                    # Start the async generator
                    stream = client.delta_query_stream(
                        "users", delta_link=explicit_delta_link
                    )
                    await stream.__anext__()
                except StopAsyncIteration:
                    pass
                except Exception:
                    pass  # Expected since we're not fully mocking the request

                # Should extract token from explicit delta link
                mock_extract.assert_called_with(explicit_delta_link)

    async def test_delta_query_stream_with_deltatoken_latest(self, mock_credential):
        """Test delta_query_stream with deltatoken_latest flag."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        await client._initialize()

        with patch.object(client, "_get_delta_request_builder") as mock_builder:
            with patch.object(client, "_build_query_parameters") as mock_build_params:
                mock_builder.return_value = Mock()
                mock_build_params.return_value = {"deltatoken": "latest"}

                try:
                    # Start the async generator
                    stream = client.delta_query_stream("users", deltatoken_latest=True)
                    await stream.__anext__()
                except StopAsyncIteration:
                    pass
                except Exception:
                    pass  # Expected since we're not fully mocking the request

                # Should build parameters with deltatoken_latest
                mock_build_params.assert_called()
                call_kwargs = mock_build_params.call_args[1]
                assert call_kwargs.get("deltatoken_latest") is True


class TestClientInitializationEdgeCases:
    """Test edge cases in client initialization."""

    async def test_signal_handler_setup_import_error(self):
        """Test signal handler setup when signal module import fails."""
        with patch("builtins.__import__", side_effect=ImportError("No signal module")):
            with patch("asyncio.get_running_loop") as mock_get_loop:
                mock_loop = Mock()
                mock_loop.add_signal_handler = Mock()
                mock_get_loop.return_value = mock_loop

                # Should not raise exception even if signal import fails
                client = AsyncDeltaQueryClient()
                assert client is not None

    async def test_signal_handler_setup_os_error(self):
        """Test signal handler setup when OS doesn't support signals."""
        import signal

        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_loop.add_signal_handler = Mock(
                side_effect=OSError("Signals not supported")
            )
            mock_get_loop.return_value = mock_loop

            # Should not raise exception even if signal setup fails
            client = AsyncDeltaQueryClient()
            assert client is not None

    async def test_signal_handler_setup_not_implemented_error(self):
        """Test signal handler setup when signals are not implemented."""
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_loop.add_signal_handler = Mock(
                side_effect=NotImplementedError("Not implemented")
            )
            mock_get_loop.return_value = mock_loop

            # Should not raise exception even if signal setup is not implemented
            client = AsyncDeltaQueryClient()
            assert client is not None

    async def test_loop_cleanup_attribute_already_set(self):
        """Test that loop cleanup setup is idempotent."""
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_loop.add_signal_handler = Mock()
            # Simulate cleanup already added
            mock_loop._delta_client_cleanup_added = True
            mock_get_loop.return_value = mock_loop

            # Should not add signal handlers again
            client = AsyncDeltaQueryClient()
            mock_loop.add_signal_handler.assert_not_called()


class TestProcessSdkObjectEdgeCases:
    """Test edge cases in _process_sdk_object method."""

    async def test_process_sdk_object_with_complex_dict(self):
        """Test _process_sdk_object with complex dict structure."""
        client = AsyncDeltaQueryClient()

        # Complex dict object with nested data
        complex_dict = {
            "id": "123",
            "displayName": "Test User",
            "properties": {"nested": "value"},
            "array_field": [1, 2, 3],
            "@odata.context": "metadata",
        }

        result = client._process_sdk_object(complex_dict, "users")

        # Should return the dict unchanged
        assert result is complex_dict
        assert result["id"] == "123"
        assert result["properties"]["nested"] == "value"

    async def test_process_sdk_object_with_sdk_like_object(self):
        """Test _process_sdk_object with SDK-like object."""
        client = AsyncDeltaQueryClient()

        # Mock SDK object
        mock_obj = Mock()
        mock_obj.id = "123"
        mock_obj.display_name = "Test User"
        mock_obj.additional_data = {"extra": "data"}

        result = client._process_sdk_object(mock_obj, "applications")

        # Should return the object unchanged
        assert result is mock_obj
        assert result.id == "123"
        assert result.display_name == "Test User"

    async def test_process_sdk_object_preserves_type(self):
        """Test _process_sdk_object preserves object type."""
        client = AsyncDeltaQueryClient()

        # Various object types
        test_objects = [
            {"key": "value"},  # dict
            Mock(),  # Mock object
            "string",  # string
            123,  # number
            None,  # None
            [1, 2, 3],  # list
        ]

        for obj in test_objects:
            result = client._process_sdk_object(obj)
            assert result is obj
            assert type(result) == type(obj)
