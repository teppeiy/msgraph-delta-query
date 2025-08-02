"""Test __init__ module."""

import pytest
from msgraph_delta_query import (
    AsyncDeltaQueryClient,
    DeltaLinkStorage, 
    LocalFileDeltaLinkStorage,
    __version__,
    __author__,
    __email__,
    __all__
)


def test_imports():
    """Test that all expected classes and constants are importable."""
    # Test classes can be imported and instantiated
    assert AsyncDeltaQueryClient is not None
    assert DeltaLinkStorage is not None
    assert LocalFileDeltaLinkStorage is not None
    
    # Test that we can create instances
    client = AsyncDeltaQueryClient()
    assert client is not None
    
    storage = LocalFileDeltaLinkStorage()
    assert storage is not None
    
    # Test abstract base class
    base_storage = DeltaLinkStorage()
    assert base_storage is not None


def test_version_constants():
    """Test that version constants are defined."""
    assert __version__ == "0.1.0"
    assert isinstance(__author__, str)
    assert isinstance(__email__, str)


def test_all_exports():
    """Test that __all__ contains expected exports."""
    expected_exports = [
        "AsyncDeltaQueryClient",
        "DeltaLinkStorage", 
        "LocalFileDeltaLinkStorage"
    ]
    
    assert __all__ == expected_exports
    
    # Verify all items in __all__ are actually importable
    import msgraph_delta_query
    for item in __all__:
        assert hasattr(msgraph_delta_query, item)


def test_module_docstring():
    """Test that module has docstring."""
    import msgraph_delta_query
    assert msgraph_delta_query.__doc__ is not None
    assert "Delta Query Client for Microsoft Graph API" in msgraph_delta_query.__doc__
