"""
Delta Query Client for Microsoft Graph API.

A Python library for efficiently querying Microsoft Graph API using delta queries
with automatic delta link management and asynchronous support.
"""

from .client import AsyncDeltaQueryClient
from .storage import DeltaLinkStorage, LocalFileDeltaLinkStorage
from .models import ChangeSummary, ResourceParams, PageMetadata, DeltaQueryMetadata

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "AsyncDeltaQueryClient",
    "DeltaLinkStorage", 
    "LocalFileDeltaLinkStorage",
    "ChangeSummary",
    "ResourceParams",
    "PageMetadata", 
    "DeltaQueryMetadata"
]
