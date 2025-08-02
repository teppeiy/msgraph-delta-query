#!/usr/bin/env python3
"""
Test script to verify the refactored storage module structure.
Tests both backward compatibility and new package imports.
"""

import asyncio

print("=== Testing Refactored Storage Module ===\n")

# Test 1: Backward compatibility - importing from main storage module
print("1. Testing backward compatibility imports...")
try:
    from src.msgraph_delta_query.storage import (
        DeltaLinkStorage,
        LocalFileDeltaLinkStorage,
        AzureBlobDeltaLinkStorage
    )
    print("✅ Backward compatibility imports working")
    print(f"   DeltaLinkStorage: {DeltaLinkStorage}")
    print(f"   LocalFileDeltaLinkStorage: {LocalFileDeltaLinkStorage}")
    print(f"   AzureBlobDeltaLinkStorage: {AzureBlobDeltaLinkStorage}")
except Exception as e:
    print(f"❌ Backward compatibility imports failed: {e}")
print()

# Test 2: New package structure imports
print("2. Testing new package structure imports...")
try:
    from src.msgraph_delta_query.storage.base import DeltaLinkStorage as BaseDLS
    from src.msgraph_delta_query.storage.local_file import LocalFileDeltaLinkStorage as LocalDLS
    from src.msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage as AzureDLS
    print("✅ New package structure imports working")
    print(f"   Base class: {BaseDLS}")
    print(f"   Local file: {LocalDLS}")
    print(f"   Azure blob: {AzureDLS}")
except Exception as e:
    print(f"❌ New package structure imports failed: {e}")
print()

# Test 3: Verify classes are the same
print("3. Testing class identity...")
try:
    # Check if backward compatibility classes are the same as new package classes
    print(f"   DeltaLinkStorage same as BaseDLS: {DeltaLinkStorage is BaseDLS}")
    print(f"   LocalFileDeltaLinkStorage same as LocalDLS: {LocalFileDeltaLinkStorage is LocalDLS}")
    print(f"   AzureBlobDeltaLinkStorage same as AzureDLS: {AzureBlobDeltaLinkStorage is AzureDLS}")
except Exception as e:
    print(f"❌ Class identity test failed: {e}")
print()

# Test 4: Functional test - create and use storage instances
async def test_functionality():
    print("4. Testing functionality...")
    
    # Test LocalFileDeltaLinkStorage
    try:
        storage = LocalFileDeltaLinkStorage("test_deltalinks")
        await storage.set("test_resource", "https://test.delta.link", {"test": "metadata"})
        delta_link = await storage.get("test_resource")
        metadata = await storage.get_metadata("test_resource")
        
        print("✅ LocalFileDeltaLinkStorage functionality working")
        print(f"   Retrieved delta link: {delta_link}")
        print(f"   Metadata exists: {metadata is not None}")
        
        await storage.delete("test_resource")
        print("   ✅ Cleanup successful")
    except Exception as e:
        print(f"❌ LocalFileDeltaLinkStorage functionality failed: {e}")
    
    # Test AzureBlobDeltaLinkStorage connection (but don't actually connect)
    try:
        # This should fail gracefully with connection error, not import error
        try:
            storage = AzureBlobDeltaLinkStorage()
        except ValueError as ve:
            if "Could not establish Azure Blob Storage connection" in str(ve):
                print("✅ AzureBlobDeltaLinkStorage properly handles missing credentials")
            else:
                print(f"❌ Unexpected ValueError: {ve}")
        except ImportError as ie:
            print(f"❌ Azure dependencies not available: {ie}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    except Exception as e:
        print(f"❌ AzureBlobDeltaLinkStorage test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_functionality())
    print("\n=== Refactoring Test Complete ===")
