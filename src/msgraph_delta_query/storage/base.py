"""
Base abstract class for delta link storage implementations.
"""

from typing import Optional, Dict


class DeltaLinkStorage:
    """Abstract base class for delta link storage."""

    async def get(self, resource: str) -> Optional[str]:
        """
        Get the delta link for a specific resource.

        Args:
            resource: The resource identifier (e.g., 'users', 'groups')

        Returns:
            The delta link URL if found, None otherwise
        """
        raise NotImplementedError

    async def get_metadata(self, resource: str) -> Optional[Dict]:
        """
        Get metadata for a resource including last sync time.

        Args:
            resource: The resource identifier

        Returns:
            Dictionary containing metadata if found, None otherwise
        """
        raise NotImplementedError

    async def set(
        self, resource: str, delta_link: str, metadata: Optional[Dict] = None
    ):
        """
        Set delta link and metadata for a resource.

        Args:
            resource: The resource identifier
            delta_link: The delta link URL to store
            metadata: Optional metadata to store with the delta link
        """
        raise NotImplementedError

    async def delete(self, resource: str):
        """
        Delete delta link and metadata for a resource.

        Args:
            resource: The resource identifier
        """
        raise NotImplementedError

    async def close(self):
        """
        Clean up any resources used by the storage implementation.
        Default implementation does nothing.
        """
        pass
