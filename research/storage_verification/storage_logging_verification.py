"""
Test the storage source logging for different storage types.
"""

import asyncio
import logging
from msgraph_delta_query import AsyncDeltaQueryClient, LocalFileDeltaLinkStorage, AzureBlobDeltaLinkStorage


async def test_storage_logging():
    """Test logging for different storage types."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=== Storage Source Logging Test ===\n")
    
    # Test 1: Local File Storage
    print("1. Testing LocalFileDeltaLinkStorage:")
    local_storage = LocalFileDeltaLinkStorage("test_deltalinks")
    client1 = AsyncDeltaQueryClient(delta_link_storage=local_storage)
    await client1._internal_close()
    
    print("\n2. Testing LocalFileDeltaLinkStorage (default directory):")
    local_storage_default = LocalFileDeltaLinkStorage()
    client2 = AsyncDeltaQueryClient(delta_link_storage=local_storage_default)
    await client2._internal_close()
    
    print("\n3. Testing AzureBlobDeltaLinkStorage (auto-detection):")
    azure_storage = AzureBlobDeltaLinkStorage()
    client3 = AsyncDeltaQueryClient(delta_link_storage=azure_storage)
    await client3._internal_close()
    
    print("\n4. Testing AzureBlobDeltaLinkStorage (custom container):")
    azure_storage_custom = AzureBlobDeltaLinkStorage(container_name="custom-deltalinks")
    client4 = AsyncDeltaQueryClient(delta_link_storage=azure_storage_custom)
    await client4._internal_close()
    
    print("\n5. Testing default client (no explicit storage):")
    client5 = AsyncDeltaQueryClient()  # Should use LocalFileDeltaLinkStorage by default
    await client5._internal_close()
    
    print("\n✅ All storage logging tests completed!")


if __name__ == "__main__":
    asyncio.run(test_storage_logging())
