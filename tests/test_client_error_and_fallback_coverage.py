import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from msgraph_delta_query.client import AsyncDeltaQueryClient

@pytest.mark.asyncio
async def test_execute_delta_request_fallback_and_storage_delete():
    """Test that a delta token error triggers fallback and deletes stored delta link."""
    client = AsyncDeltaQueryClient()
    client.delta_link_storage = MagicMock()
    request_builder = MagicMock()
    # Simulate SDK query param classes
    class DummyParams:
        pass
    request_builder.DeltaRequestBuilderGetQueryParameters = DummyParams
    request_builder.DeltaRequestBuilderGetRequestConfiguration = lambda query_parameters: MagicMock()
    # Simulate get raising a delta token error, then fallback succeeds
    call_count = [0]
    async def get_side_effect(*args, **kwargs):
        if call_count[0] == 0:
            call_count[0] += 1
            raise Exception("invalid delta token")
        return MagicMock()
    request_builder.get = AsyncMock(side_effect=get_side_effect)
    # Patch logger
    with patch.object(client, "logger") as mock_logger:
        # Patch storage.delete
        client.delta_link_storage.delete = AsyncMock()
        # Run
        resp, fallback = await client._execute_delta_request(
            request_builder,
            {"deltatoken": "badtoken"},
            fallback_to_full_sync=True,
            used_stored_deltalink=True,
            resource="users"
        )
        assert fallback is True
        client.delta_link_storage.delete.assert_called_with("users")
        assert mock_logger.warning.called
        assert mock_logger.info.called

@pytest.mark.asyncio
async def test_delta_query_stream_pagination_error_logs_and_exits():
    """Test that an error during pagination logs error and breaks the generator."""
    client = AsyncDeltaQueryClient()
    client._graph_client = MagicMock()
    client._graph_client.request_adapter = MagicMock()
    # Patch request builder and response
    with patch.object(client, "_get_delta_request_builder", return_value=MagicMock()):
        # Patch _execute_delta_request to return a response with odata_next_link
        class FakeResponse:
            value = [MagicMock()]
            odata_next_link = "https://next.page"
            additional_data = {}
        with patch.object(client, "_execute_delta_request", return_value=(FakeResponse(), False)):
            # Patch send_async to raise error on next page
            client._graph_client.request_adapter.send_async = AsyncMock(side_effect=Exception("pagination error"))
            with patch.object(client, "logger") as mock_logger:
                gen = client.delta_query_stream("users")
                results = []
                try:
                    async for objs, meta in gen:
                        results.append((objs, meta))
                except Exception:
                    pass
                assert mock_logger.error.called
                # Only the first page should be yielded
                assert len(results) == 1


def test_destructor_warns_on_unclosed_client():
    """Test that __del__ logs a warning if not closed and no running event loop."""
    client = AsyncDeltaQueryClient()
    client._closed = False
    with patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")):
        with patch.object(client, "logger") as mock_logger:
            client.__del__()
            assert mock_logger.warning.called
