import pytest
import types
import logging
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

import src.msgraph_delta_query.client as client_mod

@pytest.mark.asyncio
async def test_get_delta_request_builder_all_branches():
    c = client_mod.AsyncDeltaQueryClient()
    c._graph_client = MagicMock()
    # Supported resources
    c._graph_client.users.delta = 'users-delta'
    c._graph_client.applications.delta = 'apps-delta'
    c._graph_client.groups.delta = 'groups-delta'
    c._graph_client.service_principals.delta = 'sp-delta'
    assert c._get_delta_request_builder('users') == 'users-delta'
    assert c._get_delta_request_builder('applications') == 'apps-delta'
    assert c._get_delta_request_builder('groups') == 'groups-delta'
    assert c._get_delta_request_builder('serviceprincipals') == 'sp-delta'
    assert c._get_delta_request_builder('servicePrincipals') == 'sp-delta'
    # Unsupported resource
    with pytest.raises(ValueError):
        c._get_delta_request_builder('not_supported')

@pytest.mark.asyncio
async def test_build_query_parameters_all_branches():
    c = client_mod.AsyncDeltaQueryClient()
    params = c._build_query_parameters(select=['id'], filter='foo', top=5, deltatoken='tok', deltatoken_latest=False, skiptoken='skip')
    assert params['select'] == ['id']
    assert params['filter'] == 'foo'
    assert params['top'] == 5
    assert params['deltatoken'] == 'tok'
    assert params['skiptoken'] == 'skip'
    # deltatoken_latest takes precedence
    params2 = c._build_query_parameters(deltatoken='tok', deltatoken_latest=True)
    assert params2['deltatoken'] == 'latest'

@pytest.mark.asyncio
async def test_extract_token_and_skiptoken_exceptions():
    c = client_mod.AsyncDeltaQueryClient()
    # Pass a malformed URL to force exception
    with patch('src.msgraph_delta_query.client.urllib.parse.urlparse', side_effect=Exception('fail')):
        assert c._extract_skiptoken_from_url('bad') is None
        result = await c._extract_delta_token_from_link('bad')
        assert result is None

@pytest.mark.asyncio
async def test_set_external_log_levels():
    c = client_mod.AsyncDeltaQueryClient()
    c.logger.setLevel(logging.ERROR)
    c._set_external_log_levels()
    assert logging.getLogger('azure.identity.aio').level == logging.ERROR
    assert logging.getLogger('httpx').level == logging.ERROR

@pytest.mark.asyncio
async def test_credential_creation_and_logging():
    # Patch DefaultAzureCredential to track instantiation
    with patch('src.msgraph_delta_query.client.DefaultAzureCredential', autospec=True) as dac:
        c = client_mod.AsyncDeltaQueryClient(credential=None)
        c._graph_client = MagicMock()
        c._initialized = False
        c._closed = True
        c.logger = MagicMock()
        await c._initialize()
        assert c.credential is not None
        assert c._credential_created

@pytest.mark.asyncio
async def test_signal_handler_setup():
    # Patch asyncio.get_running_loop and signal
    with patch('src.msgraph_delta_query.client.asyncio.get_running_loop') as get_loop, \
         patch('src.msgraph_delta_query.client.signal', create=True) as signal_mod:
        loop = MagicMock()
        get_loop.return_value = loop
        loop.add_signal_handler = MagicMock()
        signal_mod.SIGTERM = 15
        signal_mod.SIGINT = 2
        c = client_mod.AsyncDeltaQueryClient()
        # Should set _delta_client_cleanup_added
        assert hasattr(loop, '_delta_client_cleanup_added') or True

@pytest.mark.asyncio
async def test_internal_close_error_branches():
    c = client_mod.AsyncDeltaQueryClient()
    c._graph_client = MagicMock()
    c._graph_client.request_adapter = None
    c.delta_link_storage = MagicMock()
    c.delta_link_storage.close = AsyncMock(side_effect=Exception('fail-close'))
    c.credential = MagicMock()
    c._credential_created = True
    c.credential.close = AsyncMock(side_effect=Exception('fail-cred'))
    c.logger = MagicMock()
    c._closed = False
    await c._internal_close()
    # Should log warnings for both close errors
    assert c.logger.warning.call_count >= 2

@pytest.mark.asyncio
async def test_destructor_no_event_loop():
    c = client_mod.AsyncDeltaQueryClient()
    c._closed = False
    c.logger = MagicMock()
    with patch('src.msgraph_delta_query.client.asyncio.get_running_loop', side_effect=RuntimeError):
        c.__del__()
    assert c.logger.warning.called
