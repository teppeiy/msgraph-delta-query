"""Test client implementations."""

import pytest
import asyncio
import aiohttp
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
    credential = AsyncMock()
    token_mock = Mock()
    token_mock.token = "test_token_123"
    credential.get_token.return_value = token_mock
    return credential


@pytest.mark.asyncio
class TestAsyncDeltaQueryClient:
    """Test AsyncDeltaQueryClient functionality."""

    async def test_init_default_parameters(self):
        """Test client initialization with default parameters."""
        client = AsyncDeltaQueryClient()

        assert client.credential is None
        assert client.delta_link_storage is not None
        assert client.timeout == AsyncDeltaQueryClient.DEFAULT_TIMEOUT
        assert client.semaphore._value == 10
        assert not client._initialized
        assert not client._closed
        assert not client._credential_created
        assert client in _client_registry

    async def test_init_custom_parameters(self, mock_credential, mock_storage):
        """Test client initialization with custom parameters."""
        timeout = aiohttp.ClientTimeout(total=60)
        client = AsyncDeltaQueryClient(
            credential=mock_credential,
            delta_link_storage=mock_storage,
            timeout=timeout,
            max_concurrent_requests=5,
        )

        assert client.credential == mock_credential
        assert client.delta_link_storage == mock_storage
        assert client.timeout == timeout
        assert client.semaphore._value == 5

    async def test_initialize_creates_session_and_credential(self):
        """Test that _initialize creates session and credential."""
        client = AsyncDeltaQueryClient()

        with patch(
            "msgraph_delta_query.client.aiohttp.ClientSession"
        ) as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            with patch(
                "msgraph_delta_query.client.DefaultAzureCredential"
            ) as mock_cred_class:
                mock_credential = AsyncMock()
                mock_cred_class.return_value = mock_credential

                await client._initialize()

                assert client._initialized
                assert client._session == mock_session
                assert client.credential == mock_credential
                assert client._credential_created
                mock_session_class.assert_called_once_with(timeout=client.timeout)
                mock_cred_class.assert_called_once()

    async def test_initialize_idempotent(self):
        """Test that _initialize can be called multiple times safely."""
        client = AsyncDeltaQueryClient()

        with patch(
            "msgraph_delta_query.client.aiohttp.ClientSession"
        ) as mock_session_class:
            with patch(
                "msgraph_delta_query.client.DefaultAzureCredential"
            ) as mock_cred_class:
                await client._initialize()
                await client._initialize()  # Second call should not create new instances

                assert mock_session_class.call_count == 1
                assert mock_cred_class.call_count == 1

    async def test_initialize_skipped_when_closed(self):
        """Test that _initialize is skipped when client is closed."""
        client = AsyncDeltaQueryClient()
        client._closed = True

        with patch(
            "msgraph_delta_query.client.aiohttp.ClientSession"
        ) as mock_session_class:
            await client._initialize()
            mock_session_class.assert_not_called()

    async def test_internal_close(self, mock_credential):
        """Test internal close functionality."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        # Mock session
        mock_session = AsyncMock()
        mock_session.closed = False
        client._session = mock_session
        client._credential_created = True
        client._initialized = True

        await client._internal_close()

        assert client._closed
        assert client._session is None
        assert client.credential is None
        assert not client._credential_created
        assert not client._initialized
        mock_session.close.assert_called_once()
        mock_credential.close.assert_called_once()

    async def test_internal_close_idempotent(self):
        """Test that _internal_close can be called multiple times safely."""
        client = AsyncDeltaQueryClient()
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.closed = False  # First call will see it as not closed
        client._session = mock_session

        await client._internal_close()
        # Simulate session being closed after first call
        mock_session.closed = True
        await client._internal_close()  # Should not raise or call close again

        assert mock_session.close.call_count == 1

    async def test_internal_close_handles_credential_error(self, mock_credential):
        """Test that _internal_close handles credential close errors gracefully."""
        client = AsyncDeltaQueryClient(credential=mock_credential)
        client._credential_created = True
        mock_credential.close.side_effect = Exception("Close error")

        with patch("logging.warning") as mock_warning:
            await client._internal_close()
            mock_warning.assert_called()

    async def test_get_token_success(self, mock_credential):
        """Test successful token retrieval."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        with patch.object(client, "_initialize") as mock_init:
            token = await client.get_token()

            mock_init.assert_called_once()
            mock_credential.get_token.assert_called_once_with(
                "https://graph.microsoft.com/.default"
            )
            assert token == "test_token_123"

    async def test_get_token_failure(self, mock_credential):
        """Test token retrieval failure."""
        client = AsyncDeltaQueryClient(credential=mock_credential)
        mock_credential.get_token.side_effect = Exception("Token error")

        with patch("logging.error") as mock_error:
            with pytest.raises(Exception, match="Token error"):
                await client.get_token()
            mock_error.assert_called()

    async def test_make_request_success(self, mock_credential):
        """Test successful HTTP request."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        # Mock session and response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"value": []}')
        mock_response.json = AsyncMock(return_value={"value": []})

        # Create a proper async context manager mock
        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        context_manager.__aexit__ = AsyncMock(return_value=None)

        # Make sure the get method returns our context manager
        mock_session.get = Mock(return_value=context_manager)

        client._session = mock_session
        client._initialized = True

        url = "https://example.com/test"
        headers = {"Authorization": "Bearer token"}

        status, text, result = await client._make_request(url, headers)

        assert status == 200
        assert text == '{"value": []}'
        assert result == {"value": []}

    async def test_make_request_rate_limit_429(self, mock_credential):
        """Test handling of 429 rate limit responses."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        mock_session = AsyncMock()

        # First response: 429 with retry-after
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        # Mock headers object properly
        mock_headers = Mock()
        mock_headers.get.return_value = "2"
        mock_response_429.headers = mock_headers
        mock_response_429.text = AsyncMock(return_value="Rate limited")

        # Second response: 200 success
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.text = AsyncMock(return_value='{"value": []}')
        mock_response_200.json = AsyncMock(return_value={"value": []})

        # Use a counter to track calls
        call_count = 0

        def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            context_manager = AsyncMock()
            if call_count == 1:
                context_manager.__aenter__ = AsyncMock(return_value=mock_response_429)
            else:
                context_manager.__aenter__ = AsyncMock(return_value=mock_response_200)
            context_manager.__aexit__ = AsyncMock(return_value=None)
            return context_manager

        mock_session.get = Mock(side_effect=mock_get_side_effect)

        client._session = mock_session
        client._initialized = True

        with patch("asyncio.sleep") as mock_sleep:
            status, text, result = await client._make_request("https://example.com", {})

            assert status == 200
            mock_sleep.assert_called_with(2)

    async def test_make_request_server_errors_with_retry(self, mock_credential):
        """Test handling of server errors (500, 502, 503, 504) with retry."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        mock_session = AsyncMock()

        # First response: 503 server error
        mock_response_503 = AsyncMock()
        mock_response_503.status = 503
        mock_response_503.text = AsyncMock(return_value="Service unavailable")

        # Second response: 200 success
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.text = AsyncMock(return_value='{"value": []}')
        mock_response_200.json = AsyncMock(return_value={"value": []})

        call_count = 0

        def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            context_manager = AsyncMock()
            if call_count == 1:
                context_manager.__aenter__ = AsyncMock(return_value=mock_response_503)
            else:
                context_manager.__aenter__ = AsyncMock(return_value=mock_response_200)
            context_manager.__aexit__ = AsyncMock(return_value=None)
            return context_manager

        mock_session.get = Mock(side_effect=mock_get_side_effect)

        client._session = mock_session
        client._initialized = True

        with patch("asyncio.sleep") as mock_sleep:
            status, text, result = await client._make_request("https://example.com", {})

            assert status == 200
            mock_sleep.assert_called()

    async def test_make_request_401_unauthorized(self, mock_credential):
        """Test handling of 401 unauthorized responses."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value="Unauthorized")

        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = Mock(return_value=context_manager)

        client._session = mock_session
        client._initialized = True

        with patch("logging.error") as mock_error:
            status, text, result = await client._make_request("https://example.com", {})

            assert status == 401
            assert text == "Unauthorized"
            assert result == {}
            mock_error.assert_called()

    async def test_make_request_timeout_retry(self, mock_credential):
        """Test handling of timeout errors with retry."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        mock_session = AsyncMock()

        # First call: timeout, second call: success
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.text = AsyncMock(return_value='{"value": []}')
        mock_response_success.json = AsyncMock(return_value={"value": []})

        call_count = 0

        def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                raise asyncio.TimeoutError()
            else:
                context_manager = AsyncMock()
                context_manager.__aenter__ = AsyncMock(
                    return_value=mock_response_success
                )
                context_manager.__aexit__ = AsyncMock(return_value=None)
                return context_manager

        mock_session.get = Mock(side_effect=mock_get_side_effect)

        client._session = mock_session
        client._initialized = True

        with patch("asyncio.sleep") as mock_sleep:
            status, text, result = await client._make_request("https://example.com", {})

            assert status == 200
            mock_sleep.assert_called()

    async def test_make_request_max_retries_exceeded(self, mock_credential):
        """Test max retries exceeded scenario."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        mock_session = AsyncMock()

        def mock_get_side_effect(*args, **kwargs):
            raise asyncio.TimeoutError()

        mock_session.get = Mock(side_effect=mock_get_side_effect)

        client._session = mock_session
        client._initialized = True

        with patch("asyncio.sleep"):
            with pytest.raises(asyncio.TimeoutError):
                await client._make_request("https://example.com", {})

    async def test_delta_query_stream_basic(self, mock_credential, mock_storage):
        """Test basic delta query streaming."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock responses
        page1_response = {
            "value": [{"id": "1", "name": "User1"}],
            "@odata.nextLink": "https://example.com/page2",
        }
        page2_response = {
            "value": [{"id": "2", "name": "User2"}],
            "@odata.deltaLink": "https://example.com/delta?token=xyz",
        }

        with patch.object(client, "get_token", return_value="test_token"):
            with patch.object(client, "_make_request") as mock_request:
                mock_request.side_effect = [
                    (200, json.dumps(page1_response), page1_response),
                    (200, json.dumps(page2_response), page2_response),
                ]

                pages = []
                async for objects, page_meta in client.delta_query_stream("users"):
                    pages.append((objects, page_meta))

                assert len(pages) == 2
                assert pages[0][0] == [{"id": "1", "name": "User1"}]
                assert pages[1][0] == [{"id": "2", "name": "User2"}]
                assert pages[0][1].page == 1
                assert pages[1][1].page == 2
                assert pages[0][1].has_next_page is True
                assert pages[1][1].has_next_page is False

    async def test_delta_query_stream_with_parameters(
        self, mock_credential, mock_storage
    ):
        """Test delta query streaming with various parameters."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        response = {
            "value": [{"id": "1", "displayName": "User1"}],
            "@odata.deltaLink": "https://example.com/delta?token=abc",
        }

        with patch.object(client, "get_token", return_value="test_token"):
            with patch.object(client, "_make_request") as mock_request:
                mock_request.return_value = (200, json.dumps(response), response)

                pages = []
                async for objects, page_meta in client.delta_query_stream(
                    "users",
                    select=["id", "displayName"],
                    filter="startswith(displayName,'A')",
                    top=100,
                    deltatoken_latest=True,
                ):
                    pages.append((objects, page_meta))

                # Verify URL construction with parameters
                called_url = mock_request.call_args[0][0]
                # URLs are encoded, so we need to check for both encoded and unencoded versions
                assert (
                    "select=id%2CdisplayName" in called_url
                    or "$select=id,displayName" in called_url
                )
                assert (
                    "filter=startswith" in called_url
                )  # Just check for the function name
                assert "top=100" in called_url or "$top=100" in called_url
                assert (
                    "deltatoken=latest" in called_url
                    or "$deltatoken=latest" in called_url
                )

    async def test_delta_query_stream_with_existing_delta_link(
        self, mock_credential, mock_storage
    ):
        """Test delta query streaming with existing delta link."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Set up existing delta link in storage
        existing_delta_link = "https://example.com/delta?$deltatoken=stored_token"
        await mock_storage.set("users", existing_delta_link)

        response = {
            "value": [{"id": "1", "name": "User1"}],
            "@odata.deltaLink": "https://example.com/delta?token=new_token",
        }

        with patch.object(client, "get_token", return_value="test_token"):
            with patch.object(client, "_make_request") as mock_request:
                mock_request.return_value = (200, json.dumps(response), response)

                pages = []
                async for objects, page_meta in client.delta_query_stream("users"):
                    pages.append((objects, page_meta))

                # Verify delta token was used in URL
                called_url = mock_request.call_args[0][0]
                assert (
                    "deltatoken=stored_token" in called_url
                    or "$deltatoken=stored_token" in called_url
                )

    async def test_delta_query_stream_http_error(self, mock_credential, mock_storage):
        """Test delta query streaming handles HTTP errors gracefully."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        with patch.object(client, "get_token", return_value="test_token"):
            with patch.object(client, "_make_request") as mock_request:
                mock_request.return_value = (500, "Server Error", {})

                pages = []
                async for objects, page_meta in client.delta_query_stream("users"):
                    pages.append((objects, page_meta))

                assert len(pages) == 0

    async def test_delta_query_all_success(self, mock_credential, mock_storage):
        """Test delta_query_all successful execution."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the stream method
        async def mock_stream(*args, **kwargs):
            from dataclasses import dataclass
            from msgraph_delta_query.client import PageMetadata

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
            with patch.object(client, "_internal_close") as mock_close:
                objects, delta_link, meta = await client.delta_query_all("users")

                assert len(objects) == 2
                assert objects[0]["id"] == "1"
                assert objects[1]["id"] == "2"
                assert delta_link == "final_link"
                assert meta.change_summary.new_or_updated == 2
                assert meta.pages_fetched == 2
                assert hasattr(meta, "duration_seconds")
                assert hasattr(meta, "start_time")
                assert hasattr(meta, "end_time")
                mock_close.assert_called_once()

    async def test_delta_query_all_with_max_objects(
        self, mock_credential, mock_storage
    ):
        """Test delta_query_all respects max_objects limit."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Mock the stream method
        async def mock_stream(*args, **kwargs):
            from msgraph_delta_query.client import PageMetadata

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
            with patch.object(client, "_internal_close"):
                objects, delta_link, meta = await client.delta_query_all(
                    "users", max_objects=3
                )

                assert len(objects) == 3  # Limited to 3 despite having 4 available
                # Note: change_summary tracks all processed objects, not just returned ones
                assert (
                    meta.change_summary.new_or_updated == 4
                )  # All 4 objects were processed

    async def test_reset_delta_link(self, mock_credential, mock_storage):
        """Test reset_delta_link functionality."""
        client = AsyncDeltaQueryClient(
            credential=mock_credential, delta_link_storage=mock_storage
        )

        # Set up existing delta link
        await mock_storage.set("users", "existing_link")
        assert await mock_storage.get("users") == "existing_link"

        # Reset it
        with patch("logging.info") as mock_info:
            await client.reset_delta_link("users")
            mock_info.assert_called_with("Reset delta link for users")

        # Verify it's gone
        assert await mock_storage.get("users") is None

    def test_destructor_with_running_loop(self, mock_credential):
        """Test destructor when event loop is running."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        mock_loop = Mock()
        mock_task = Mock()
        mock_loop.create_task.return_value = mock_task

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            with patch.object(client, "_internal_close") as mock_close:
                client.__del__()
                mock_loop.create_task.assert_called_once()

    def test_destructor_without_running_loop(self, mock_credential):
        """Test destructor when no event loop is running."""
        client = AsyncDeltaQueryClient(credential=mock_credential)

        with patch(
            "asyncio.get_running_loop", side_effect=RuntimeError("No running loop")
        ):
            with patch("logging.warning") as mock_warning:
                client.__del__()
                mock_warning.assert_called()

    def test_destructor_already_closed(self, mock_credential):
        """Test destructor when client is already closed."""
        client = AsyncDeltaQueryClient(credential=mock_credential)
        client._closed = True

        with patch("asyncio.get_running_loop") as mock_get_loop:
            client.__del__()
            mock_get_loop.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_all_clients():
    """Test global cleanup function."""
    # Create some test clients
    client1 = AsyncDeltaQueryClient()
    client2 = AsyncDeltaQueryClient()

    with patch.object(client1, "_internal_close") as mock_close1:
        with patch.object(client2, "_internal_close") as mock_close2:
            await _cleanup_all_clients()

            mock_close1.assert_called_once()
            mock_close2.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_all_clients_with_errors():
    """Test global cleanup function handles errors gracefully."""
    client = AsyncDeltaQueryClient()

    with patch.object(client, "_internal_close", side_effect=Exception("Close error")):
        with patch("logging.warning") as mock_warning:
            await _cleanup_all_clients()
            mock_warning.assert_called()


@pytest.mark.asyncio
async def test_signal_handler_setup():
    """Test signal handler setup in constructor."""
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = Mock()
        mock_loop.add_signal_handler = Mock()
        mock_get_loop.return_value = mock_loop

        with patch("signal.SIGTERM", 15):
            with patch("signal.SIGINT", 2):
                client = AsyncDeltaQueryClient()

                # Verify signal handlers were attempted to be set up
                # (may not be called on Windows, so we just ensure no errors)
                assert client is not None


@pytest.mark.asyncio
async def test_signal_handler_setup_not_implemented():
    """Test signal handler setup when not implemented on platform."""
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = Mock()
        mock_loop.add_signal_handler = Mock(side_effect=NotImplementedError())
        mock_get_loop.return_value = mock_loop

        # Should not raise exception
        client = AsyncDeltaQueryClient()
        assert client is not None


@pytest.mark.asyncio
async def test_constructor_no_running_loop():
    """Test constructor when no event loop is running."""
    with patch("asyncio.get_running_loop", side_effect=RuntimeError("No running loop")):
        # Should not raise exception
        client = AsyncDeltaQueryClient()
        assert client is not None


@pytest.mark.asyncio
async def test_delta_query_stream_saves_final_delta_link(mock_credential, mock_storage):
    """Test that delta_query_stream saves the final delta link to storage."""
    client = AsyncDeltaQueryClient(
        credential=mock_credential, delta_link_storage=mock_storage
    )

    response = {
        "value": [{"id": "1", "name": "User1"}],
        "@odata.deltaLink": "https://example.com/delta?token=final_token",
    }

    with patch.object(client, "get_token", return_value="test_token"):
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = (200, json.dumps(response), response)

            pages = []
            async for objects, page_meta in client.delta_query_stream(
                "users", select=["id", "name"]
            ):
                pages.append((objects, page_meta))

            # Verify delta link was saved
            saved_link = await mock_storage.get("users")
            assert saved_link == "https://example.com/delta?token=final_token"


@pytest.mark.asyncio
async def test_delta_query_all_metadata_used_stored_deltalink(
    mock_credential, mock_storage
):
    """Test that metadata correctly indicates when stored delta link was used."""
    client = AsyncDeltaQueryClient(
        credential=mock_credential, delta_link_storage=mock_storage
    )

    # Set up existing delta link
    await mock_storage.set("users", "existing_link")

    async def mock_stream(*args, **kwargs):
        from msgraph_delta_query.client import PageMetadata

        page_meta = PageMetadata(
            page=1,
            object_count=1,
            has_next_page=False,
            delta_link="new_link",
            raw_response_size=100,
            page_new_or_updated=1,
            page_deleted=0,
            page_changed=0,
            total_new_or_updated=1,
            total_deleted=0,
            total_changed=0,
        )
        yield [{"id": "1"}], page_meta

    with patch.object(client, "delta_query_stream", side_effect=mock_stream):
        with patch.object(client, "_internal_close"):
            objects, delta_link, meta = await client.delta_query_all("users")

            assert meta.used_stored_deltalink is True


@pytest.mark.asyncio
async def test_delta_query_all_metadata_no_stored_deltalink(
    mock_credential, mock_storage
):
    """Test that metadata correctly indicates when no stored delta link was used."""
    client = AsyncDeltaQueryClient(
        credential=mock_credential, delta_link_storage=mock_storage
    )

    async def mock_stream(*args, **kwargs):
        from msgraph_delta_query.client import PageMetadata

        page_meta = PageMetadata(
            page=1,
            object_count=1,
            has_next_page=False,
            delta_link="new_link",
            raw_response_size=100,
            page_new_or_updated=1,
            page_deleted=0,
            page_changed=0,
            total_new_or_updated=1,
            total_deleted=0,
            total_changed=0,
        )
        yield [{"id": "1"}], page_meta

    with patch.object(client, "delta_query_stream", side_effect=mock_stream):
        with patch.object(client, "_internal_close"):
            objects, delta_link, meta = await client.delta_query_all("users")

            assert meta.used_stored_deltalink is False
