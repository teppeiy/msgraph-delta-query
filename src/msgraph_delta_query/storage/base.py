"""
Base abstract class for delta link storage implementations.
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

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
        logger.debug("DeltaLinkStorage.get() not implemented")
        raise NotImplementedError

    async def get_metadata(self, resource: str) -> Optional[Dict]:
        """
        Get metadata for a resource including last sync time.

        Args:
            resource: The resource identifier

        Returns:
            Dictionary containing metadata if found, None otherwise
        """
        logger.debug("DeltaLinkStorage.get_metadata() not implemented")
        raise NotImplementedError

    async def set(
        self, resource: str, delta_link: str, metadata: Optional[Dict] = None
    ) -> None:
        """
        Set delta link and metadata for a resource.

        Args:
            resource: The resource identifier
            delta_link: The delta link URL to store
            metadata: Optional metadata to store with the delta link
        """
        logger.debug("DeltaLinkStorage.set() not implemented")
        raise NotImplementedError

    async def delete(self, resource: str) -> None:
        """
        Delete delta link and metadata for a resource.

        Args:
            resource: The resource identifier
        """
        logger.debug("DeltaLinkStorage.delete() not implemented")
        raise NotImplementedError

    async def close(self) -> None:
        """
        Clean up any resources used by the storage implementation.
        Default implementation does nothing.
        """
        logger.debug("DeltaLinkStorage.close() default implementation called")
        pass
