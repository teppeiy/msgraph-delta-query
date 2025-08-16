import pytest
import os
import json
from unittest.mock import patch, MagicMock
import src.msgraph_delta_query.storage.local_file as local_file_mod
from pathlib import Path

@pytest.mark.asyncio
async def test_get_and_get_metadata_file_not_found(tmp_path):
    folder = tmp_path / "deltalinks"
    s = local_file_mod.LocalFileDeltaLinkStorage(folder=str(folder))
    # File does not exist
    assert await s.get('foo') is None
    assert await s.get_metadata('foo') is None

@pytest.mark.asyncio
async def test_get_and_get_metadata_success(tmp_path):
    folder = tmp_path / "deltalinks"
    s = local_file_mod.LocalFileDeltaLinkStorage(folder=str(folder))
    path = Path(folder) / "foo.json"
    data = {"delta_link": "bar", "last_updated": "now", "metadata": {"x": 1}, "resource": "foo"}
    path.write_text(json.dumps(data))
    assert await s.get('foo') == "bar"
    meta = await s.get_metadata('foo')
    assert meta is not None
    assert meta["last_updated"] == "now"
    assert meta["metadata"] == {"x": 1}
    assert meta["resource"] == "foo"

@pytest.mark.asyncio
async def test_get_and_get_metadata_error(tmp_path):
    folder = tmp_path / "deltalinks"
    s = local_file_mod.LocalFileDeltaLinkStorage(folder=str(folder))
    path = Path(folder) / "foo.json"
    path.write_text("not json")
    with patch.object(local_file_mod.logger, 'warning') as warn:
        assert await s.get('foo') is None
        assert warn.called
    with patch.object(local_file_mod.logger, 'warning') as warn:
        assert await s.get_metadata('foo') is None
        assert warn.called

@pytest.mark.asyncio
async def test_set_and_delete_success_and_error(tmp_path):
    folder = tmp_path / "deltalinks"
    s = local_file_mod.LocalFileDeltaLinkStorage(folder=str(folder))
    # set should create file
    await s.set('foo', 'bar', {"meta": 1})
    path = Path(folder) / "foo.json"
    assert path.exists()
    # delete should remove file
    await s.delete('foo')
    assert not path.exists()
    # delete should not raise if file does not exist
    await s.delete('foo')
    # set error branch
    with patch("builtins.open", side_effect=Exception("fail")):
        with pytest.raises(Exception):
            await s.set('foo', 'bar')
    # delete error branch
    path.write_text("x")
    with patch("os.remove", side_effect=Exception("fail")):
        with patch.object(local_file_mod.logger, 'warning') as warn:
            await s.delete('foo')
            assert warn.called

@pytest.mark.asyncio
async def test_get_resource_path_hashing(tmp_path):
    folder = tmp_path / "deltalinks"
    s = local_file_mod.LocalFileDeltaLinkStorage(folder=str(folder))
    long_name = 'a' * 300
    path = s._get_resource_path(long_name)
    assert path.endswith('.json')
    assert len(Path(path).stem) < 100  # Should be hashed

@pytest.mark.asyncio
async def test_custom_folder_and_deltalinks_dir(tmp_path):
    folder = tmp_path / "customdir"
    s = local_file_mod.LocalFileDeltaLinkStorage(folder=str(folder))
    assert s.folder == str(folder)
    assert s.deltalinks_dir == "customdir"
    # Should create the directory
    assert os.path.exists(folder)
