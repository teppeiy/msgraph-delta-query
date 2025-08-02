"""
Delta link storage implementations for Microsoft Graph API.

This package provides different storage backends for persisting delta links
between Microsoft Graph API sync operations.
"""

from .base import DeltaLinkStorage
from .local_file import LocalFileDeltaLinkStorage

# Azure Blob Storage is optional - only import if dependencies are available
try:
    from .azure_blob import AzureBlobDeltaLinkStorage  # noqa: F401

    __all__ = [
        "DeltaLinkStorage",
        "LocalFileDeltaLinkStorage",
        "AzureBlobDeltaLinkStorage",
    ]
except ImportError:
    __all__ = ["DeltaLinkStorage", "LocalFileDeltaLinkStorage"]
