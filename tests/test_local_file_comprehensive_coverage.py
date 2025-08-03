"""
Comprehensive coverage tests for local_file.py edge cases and error conditions.
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch, mock_open
from msgraph_delta_query.storage.local_file import LocalFileDeltaLinkStorage


class TestLocalFileComprehensiveCoverage:
    """Test LocalFile storage edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_get_resource_path_with_long_resource_name(self):
        """Test _get_resource_path with very long resource name."""
        storage = LocalFileDeltaLinkStorage()
        
        # Create a resource name longer than filesystem limits
        long_name = "a" * 250
        file_path = storage._get_resource_path(long_name)
        
        # Should be handled appropriately (either truncated or hashed)
        assert file_path.endswith(".json")

    @pytest.mark.asyncio
    async def test_get_resource_path_special_characters(self):
        """Test _get_resource_path with special characters."""
        storage = LocalFileDeltaLinkStorage()
        
        resource_name = "resource/with\\special:characters"
        file_path = storage._get_resource_path(resource_name)
        
        # Should create a valid file path
        assert file_path.endswith(".json")

    @pytest.mark.asyncio
    async def test_get_with_json_decode_error(self):
        """Test get method with invalid JSON file."""
        storage = LocalFileDeltaLinkStorage()
        
        # Create a temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json")
            temp_path = f.name
        
        try:
            with patch.object(storage, '_get_resource_path', return_value=temp_path):
                result = await storage.get("test_resource")
                # Should return None on JSON decode error
                assert result is None
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_get_with_non_string_delta_link(self):
        """Test get method with non-string delta_link in JSON."""
        storage = LocalFileDeltaLinkStorage()
        
        # Create a temporary file with non-string delta_link
        invalid_data = {"delta_link": 123, "last_sync": "2025-01-01T00:00:00Z"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f)
            temp_path = f.name
        
        try:
            with patch.object(storage, '_get_resource_path', return_value=temp_path):
                result = await storage.get("test_resource")
                # Should return None for non-string delta_link
                assert result is None
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_get_metadata_with_general_exception(self):
        """Test get_metadata method with general exception."""
        storage = LocalFileDeltaLinkStorage()
        
        # Mock _get_resource_path to raise exception
        with patch.object(storage, '_get_resource_path', side_effect=Exception("General error")):
            result = await storage.get_metadata("test_resource")
            # Should return None on general exception
            assert result is None

    @pytest.mark.asyncio
    async def test_set_with_write_permission_error(self):
        """Test set method with file write permission error."""
        storage = LocalFileDeltaLinkStorage()
        
        # Mock open to raise PermissionError
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                await storage.set("test_resource", "delta_link_value")

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self):
        """Test delete method when file doesn't exist."""
        storage = LocalFileDeltaLinkStorage()
        
        # Mock _get_resource_path to return non-existent file
        with patch.object(storage, '_get_resource_path', return_value="/nonexistent/file.json"):
            # Should not raise exception (FileNotFoundError is handled)
            await storage.delete("test_resource")

    @pytest.mark.asyncio
    async def test_delete_permission_error(self):
        """Test delete method with permission error."""
        storage = LocalFileDeltaLinkStorage()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"delta_link": "test"}')
            temp_path = f.name
        
        try:
            # Mock os.remove to raise PermissionError
            with patch.object(storage, '_get_resource_path', return_value=temp_path), \
                 patch('os.remove', side_effect=PermissionError("Permission denied")):
                
                # Should not raise exception (logs warning)
                await storage.delete("test_resource")
        finally:
            # Clean up the temp file if it still exists
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    @pytest.mark.asyncio
    async def test_close_method_no_error(self):
        """Test close method (should be no-op for local file storage)."""
        storage = LocalFileDeltaLinkStorage()
        
        # Should not raise any exception
        await storage.close()

    @pytest.mark.asyncio
    async def test_init_with_custom_folder(self):
        """Test initialization with custom folder."""
        custom_folder = "custom_deltalinks"
        storage = LocalFileDeltaLinkStorage(folder=custom_folder)
        
        assert storage.folder == custom_folder

    @pytest.mark.asyncio
    async def test_init_with_default_folder(self):
        """Test initialization with default folder."""
        storage = LocalFileDeltaLinkStorage()
        
        assert storage.folder == "deltalinks"

    @pytest.mark.asyncio
    async def test_get_resource_path_edge_case_empty_resource(self):
        """Test _get_resource_path with empty resource name."""
        storage = LocalFileDeltaLinkStorage()
        
        file_path = storage._get_resource_path("")
        
        # Should still create a valid filename
        assert file_path.endswith(".json")

    @pytest.mark.asyncio
    async def test_set_with_makedirs_permission_error(self):
        """Test set method when directory creation fails."""
        storage = LocalFileDeltaLinkStorage()
        
        # Mock os.makedirs to raise PermissionError
        with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                await storage.set("test_resource", "delta_link_value")

    @pytest.mark.asyncio
    async def test_set_with_makedirs_file_exists_error(self):
        """Test set method when directory already exists."""
        storage = LocalFileDeltaLinkStorage()
        
        # Mock os.makedirs to raise FileExistsError (should be ignored)
        with patch('os.makedirs', side_effect=FileExistsError("Directory exists")), \
             patch('builtins.open', mock_open()) as mock_file:
            
            await storage.set("test_resource", "delta_link_value")
            
            # Should still attempt to write the file
            mock_file.assert_called_once()

    @pytest.mark.asyncio 
    async def test_hash_consistency_for_long_names(self):
        """Test that hash is consistent for long resource names."""
        storage = LocalFileDeltaLinkStorage()
        
        long_name = "a" * 300
        
        # Should produce the same path for the same input
        path1 = storage._get_resource_path(long_name)
        path2 = storage._get_resource_path(long_name)
        
        assert path1 == path2
        
        # Different long names should produce different paths
        different_long_name = "b" * 300
        path3 = storage._get_resource_path(different_long_name)
        
        assert path1 != path3

    @pytest.mark.asyncio
    async def test_get_with_file_not_found(self):
        """Test get method when file doesn't exist."""
        storage = LocalFileDeltaLinkStorage()
        
        # Mock _get_resource_path to return non-existent file
        with patch.object(storage, '_get_resource_path', return_value="/nonexistent/file.json"):
            result = await storage.get("test_resource")
            # Should return None for non-existent file
            assert result is None

    @pytest.mark.asyncio
    async def test_get_metadata_with_file_not_found(self):
        """Test get_metadata method when file doesn't exist."""
        storage = LocalFileDeltaLinkStorage()
        
        # Mock _get_resource_path to return non-existent file
        with patch.object(storage, '_get_resource_path', return_value="/nonexistent/file.json"):
            result = await storage.get_metadata("test_resource")
            # Should return None for non-existent file
            assert result is None
