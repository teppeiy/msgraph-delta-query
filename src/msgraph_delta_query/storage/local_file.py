import logging
logger = logging.getLogger(__name__)
"""
Local file-based delta link storage implementation.
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timezone

from .base import DeltaLinkStorage


class LocalFileDeltaLinkStorage(DeltaLinkStorage):
    """Stores delta links in a local JSON file per resource with metadata."""

    def __init__(self, folder: Optional[str] = None):
        """
        Initialize local file storage.

        Args:
            folder: Directory to store delta link files. If None, defaults to
                   "deltalinks" in the current working directory. To always use
                   the same location regardless of where scripts run from, 
                   pass an absolute path like "/path/to/project/deltalinks".
        """
        if folder is None:
            # Simple default: deltalinks folder in current working directory
            # This is predictable and doesn't require complex project detection
            self.folder = "deltalinks"
        else:
            # If folder is provided, use it as-is (can be relative or absolute)  
            self.folder = folder
            
        # Store the folder name for logging
        self.deltalinks_dir = Path(self.folder).name
        
        os.makedirs(self.folder, exist_ok=True)

    def _get_resource_path(self, resource: str) -> str:
        """Convert resource name to safe file path."""
        safe_name = resource.replace("/", "_").replace("\\", "_").replace(":", "_")
        if len(safe_name) > 200:
            safe_name = hashlib.md5(resource.encode()).hexdigest()
        return os.path.join(self.folder, f"{safe_name}.json")

    async def get(self, resource: str) -> Optional[str]:
        """Get delta link for a resource."""
        path = self._get_resource_path(resource)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    delta_link = data.get("delta_link")
                    return delta_link if isinstance(delta_link, str) else None
            except Exception as e:
                logger.warning(f"Failed to read delta link for {resource}: {e}")
                return None
        return None

    async def get_metadata(self, resource: str) -> Optional[Dict]:
        """Get metadata for a resource including last sync time."""
        path = self._get_resource_path(resource)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        "last_updated": data.get("last_updated"),
                        "metadata": data.get("metadata", {}),
                        "resource": data.get("resource"),
                    }
            except Exception as e:
                logger.warning(f"Failed to read metadata for {resource}: {e}")
                return None
        return None

    async def set(
        self, resource: str, delta_link: str, metadata: Optional[Dict] = None
    ) -> None:
        """Set delta link and metadata for a resource."""
        path = self._get_resource_path(resource)
        data = {
            "delta_link": delta_link,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "resource": resource,
            "metadata": metadata or {},
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save delta link for {resource}: {e}")
            raise

    async def delete(self, resource: str) -> None:
        """Delete delta link and metadata for a resource."""
        path = self._get_resource_path(resource)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.warning(f"Failed to delete delta link for {resource}: {e}")
