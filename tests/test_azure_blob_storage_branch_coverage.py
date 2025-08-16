import pytest
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
import src.msgraph_delta_query.storage.azure_blob as azure_blob_mod

@pytest.mark.asyncio
async def test_detect_connection_priority_env_and_localsettings(monkeypatch, tmp_path):
    # Priority 1: Managed identity
    monkeypatch.setenv('AZURE_STORAGE_ACCOUNT_NAME', 'testaccount')
    s = azure_blob_mod.AzureBlobDeltaLinkStorage()
    assert s._account_url == 'https://testaccount.blob.core.windows.net'
    monkeypatch.delenv('AZURE_STORAGE_ACCOUNT_NAME')

    # Priority 2: Env connection string
    monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', 'AccountName=envaccount;')
    s2 = azure_blob_mod.AzureBlobDeltaLinkStorage()
    assert s2._connection_string is not None and s2._connection_string.startswith('AccountName=envaccount')
    monkeypatch.delenv('AZURE_STORAGE_CONNECTION_STRING')

    # Priority 3: local.settings.json
    local_settings = tmp_path / 'local.settings.json'
    local_settings.write_text(json.dumps({"Values": {"AzureWebJobsStorage": "AccountName=localfile;"}}))
    s3 = azure_blob_mod.AzureBlobDeltaLinkStorage(local_settings_path=str(local_settings))
    assert s3._connection_string is not None and s3._connection_string.startswith('AccountName=localfile')

    # Priority 4: Azurite fallback
    s4 = azure_blob_mod.AzureBlobDeltaLinkStorage(local_settings_path='nonexistent.json')
    assert s4._connection_string is not None and 'devstoreaccount1' in s4._connection_string

@pytest.mark.asyncio
async def test_get_blob_name_hashing():
    s = azure_blob_mod.AzureBlobDeltaLinkStorage()
    long_name = 'a' * 300
    blob_name = s._get_blob_name(long_name)
    assert blob_name.endswith('.json')
    assert len(blob_name) < 100  # Should be hashed

@pytest.mark.asyncio
async def test_ensure_container_exists_error():
    s = azure_blob_mod.AzureBlobDeltaLinkStorage()
    s._get_blob_service_client = AsyncMock(side_effect=Exception('fail'))
    with pytest.raises(Exception):
        await s._ensure_container_exists()

@pytest.mark.asyncio
async def test_get_and_get_metadata_resource_not_found():
    s = azure_blob_mod.AzureBlobDeltaLinkStorage()
    s._ensure_container_exists = AsyncMock()
    s._get_blob_service_client = AsyncMock()
    blob_client = MagicMock()
    blob_client.download_blob = AsyncMock(side_effect=azure_blob_mod.ResourceNotFoundError('not found'))
    blob_service_client = MagicMock()
    blob_service_client.get_blob_client.return_value = blob_client
    s._get_blob_service_client.return_value = blob_service_client
    assert await s.get('foo') is None
    assert await s.get_metadata('foo') is None

@pytest.mark.asyncio
async def test_get_and_get_metadata_other_error():
    s = azure_blob_mod.AzureBlobDeltaLinkStorage()
    s._ensure_container_exists = AsyncMock()
    s._get_blob_service_client = AsyncMock()
    blob_client = MagicMock()
    blob_client.download_blob = AsyncMock(side_effect=Exception('fail'))
    blob_service_client = MagicMock()
    blob_service_client.get_blob_client.return_value = blob_client
    s._get_blob_service_client.return_value = blob_service_client
    assert await s.get('foo') is None
    assert await s.get_metadata('foo') is None

@pytest.mark.asyncio
async def test_set_and_delete_and_close_error_branches():
    s = azure_blob_mod.AzureBlobDeltaLinkStorage()
    s._ensure_container_exists = AsyncMock()
    s._get_blob_service_client = AsyncMock()
    blob_client = MagicMock()
    blob_client.upload_blob = AsyncMock(side_effect=Exception('fail'))
    blob_client.delete_blob = AsyncMock(side_effect=Exception('fail'))
    blob_service_client = MagicMock()
    blob_service_client.get_blob_client.return_value = blob_client
    s._get_blob_service_client.return_value = blob_service_client
    # set should raise
    with pytest.raises(Exception):
        await s.set('foo', 'bar')
    # delete should not raise
    await s.delete('foo')
    # close error branch
    s._blob_service_client = AsyncMock()
    s._credential = MagicMock()
    s._credential.close = AsyncMock(side_effect=Exception('fail'))
    await s.close()
