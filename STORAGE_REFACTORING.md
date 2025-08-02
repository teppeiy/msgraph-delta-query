# Storage Module Refactoring

The `storage.py` module has been refactored into a more organized package structure for better maintainability and modularity.

## New Structure

```
src/msgraph_delta_query/
├── storage.py                    # Backward compatibility imports
└── storage/                      # New package structure
    ├── __init__.py              # Package initialization and exports
    ├── base.py                  # Abstract base class
    ├── local_file.py            # Local file storage implementation
    └── azure_blob.py            # Azure Blob Storage implementation
```

## Files Description

### `storage/base.py`
Contains the abstract `DeltaLinkStorage` base class that defines the interface for all storage implementations:
- `get(resource)` - Retrieve delta link for a resource
- `get_metadata(resource)` - Retrieve metadata for a resource
- `set(resource, delta_link, metadata)` - Store delta link and metadata
- `delete(resource)` - Delete delta link and metadata
- `close()` - Clean up resources

### `storage/local_file.py`
Contains the `LocalFileDeltaLinkStorage` class for storing delta links in local JSON files:
- Simple file-based storage for development and testing
- Creates a directory structure for organizing delta links
- Stores each resource's data in a separate JSON file

### `storage/azure_blob.py`
Contains the `AzureBlobDeltaLinkStorage` class for storing delta links in Azure Blob Storage:
- Production-ready cloud storage solution
- Supports multiple authentication methods with priority order
- Managed identity support for Azure Functions and other Azure services
- Local development fallback with Azurite support

### `storage/__init__.py`
Exports all classes for easy importing from the package:
- Handles optional Azure dependencies gracefully
- Provides clean public API

### `storage.py` (Root Level)
Maintains backward compatibility by importing all classes from the new package structure.
Existing code will continue to work without changes.

## Usage

### Backward Compatibility (Recommended for existing code)
```python
from msgraph_delta_query.storage import (
    DeltaLinkStorage,
    LocalFileDeltaLinkStorage,
    AzureBlobDeltaLinkStorage
)
```

### New Package Structure (For new code)
```python
# Import specific implementations
from msgraph_delta_query.storage.local_file import LocalFileDeltaLinkStorage
from msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage

# Or import from package
from msgraph_delta_query.storage import LocalFileDeltaLinkStorage, AzureBlobDeltaLinkStorage
```

## Benefits

1. **Better Organization**: Related code is grouped together in logical modules
2. **Easier Maintenance**: Each storage implementation is in its own file
3. **Optional Dependencies**: Azure dependencies are isolated and handled gracefully
4. **Extensibility**: Easy to add new storage implementations
5. **Backward Compatibility**: Existing code continues to work unchanged
6. **Cleaner Imports**: Can import specific implementations as needed

## Migration Guide

**No migration required!** The refactoring maintains full backward compatibility. 

For new code, you can optionally use the new package imports, but the existing import style will continue to work.

## Future Storage Implementations

The new structure makes it easy to add additional storage backends:

- `storage/database.py` - Database storage (PostgreSQL, MySQL, etc.)
- `storage/redis.py` - Redis cache storage
- `storage/aws_s3.py` - AWS S3 storage
- `storage/gcp_storage.py` - Google Cloud Storage

Each new implementation would just need to:
1. Inherit from `DeltaLinkStorage`
2. Implement the required methods
3. Be added to `storage/__init__.py` exports
