import os
import json
import logging
import hashlib
from typing import Optional, Dict
from datetime import datetime, timezone

class DeltaLinkStorage:
    """Abstract base class for delta link storage."""
    async def get(self, resource: str) -> Optional[str]:
        raise NotImplementedError
    async def set(self, resource: str, delta_link: str, metadata: Optional[Dict] = None):
        raise NotImplementedError
    async def delete(self, resource: str):
        raise NotImplementedError

class LocalFileDeltaLinkStorage(DeltaLinkStorage):
    """Stores delta links in a local JSON file per resource with metadata."""
    def __init__(self, folder: str = "deltalinks"):
        self.folder = folder
        os.makedirs(self.folder, exist_ok=True)

    def _get_resource_path(self, resource: str) -> str:
        safe_name = resource.replace('/', '_').replace('\\', '_').replace(':', '_')
        if len(safe_name) > 200:
            safe_name = hashlib.md5(resource.encode()).hexdigest()
        return os.path.join(self.folder, f"{safe_name}.json")

    async def get(self, resource: str) -> Optional[str]:
        path = self._get_resource_path(resource)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("delta_link")
            except Exception as e:
                logging.warning(f"Failed to read delta link for {resource}: {e}")
                return None
        return None

    async def set(self, resource: str, delta_link: str, metadata: Optional[Dict] = None):
        path = self._get_resource_path(resource)
        data = {
            "delta_link": delta_link,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "resource": resource,
            "metadata": metadata or {}
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save delta link for {resource}: {e}")
            raise

    async def delete(self, resource: str):
        path = self._get_resource_path(resource)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logging.warning(f"Failed to delete delta link for {resource}: {e}")
