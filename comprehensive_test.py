#!/usr/bin/env python3
"""
Comprehensive test suite for the refactored storage system.
Tests all storage implementations and functionality.
"""

import asyncio
import tempfile
import os
import json
from datetime import datetime, timezone

print("=== Comprehensive Storage System Test ===\n")

async def test_imports():
    """Test that all imports work correctly."""
    print("1. Testing imports...")
    
    try:
        # Test package imports
        from msgraph_delta_query.storage import (
            DeltaLinkStorage,
            LocalFileDeltaLinkStorage,
            AzureBlobDeltaLinkStorage
        )
        print("✅ Package imports successful")
        
        # Test direct module imports
        from msgraph_delta_query.storage.base import DeltaLinkStorage as BaseDLS
        from msgraph_delta_query.storage.local_file import LocalFileDeltaLinkStorage as LocalDLS
        from msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage as AzureDLS
        print("✅ Direct module imports successful")
        
        # Verify they're the same classes
        assert DeltaLinkStorage is BaseDLS
        assert LocalFileDeltaLinkStorage is LocalDLS
        assert AzureBlobDeltaLinkStorage is AzureDLS
        print("✅ Class identity verified")
        
        # Store classes globally for other tests
        global LocalFileDeltaLinkStorage_class, AzureBlobDeltaLinkStorage_class
        LocalFileDeltaLinkStorage_class = LocalFileDeltaLinkStorage
        AzureBlobDeltaLinkStorage_class = AzureBlobDeltaLinkStorage
        
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

async def test_local_file_storage():
    """Test LocalFileDeltaLinkStorage functionality."""
    print("\n2. Testing LocalFileDeltaLinkStorage...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileDeltaLinkStorage_class(temp_dir)
            
            # Test set and get
            test_resource = "users"
            test_delta_link = "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=abc123"
            test_metadata = {"sync_count": 1, "last_sync": "2025-01-01T00:00:00Z"}
            
            await storage.set(test_resource, test_delta_link, test_metadata)
            print("  ✅ Set operation successful")
            
            # Test get delta link
            retrieved_link = await storage.get(test_resource)
            assert retrieved_link == test_delta_link
            print(f"  ✅ Get delta link: {retrieved_link}")
            
            # Test get metadata
            metadata = await storage.get_metadata(test_resource)
            assert metadata is not None
            assert metadata["metadata"]["sync_count"] == 1
            assert "last_updated" in metadata
            print(f"  ✅ Get metadata: {metadata['metadata']}")
            
            # Test non-existent resource
            non_existent = await storage.get("non_existent")
            assert non_existent is None
            print("  ✅ Non-existent resource returns None")
            
            # Test delete
            await storage.delete(test_resource)
            deleted_check = await storage.get(test_resource)
            assert deleted_check is None
            print("  ✅ Delete operation successful")
            
            # Test long resource names (hash fallback)
            long_resource = "a" * 250
            await storage.set(long_resource, test_delta_link)
            long_result = await storage.get(long_resource)
            assert long_result == test_delta_link
            await storage.delete(long_resource)
            print("  ✅ Long resource name handling")
            
        return True
    except Exception as e:
        print(f"❌ LocalFileDeltaLinkStorage test failed: {e}")
        return False

async def test_azure_blob_storage_creation():
    """Test AzureBlobDeltaLinkStorage creation and authentication priority."""
    print("\n3. Testing AzureBlobDeltaLinkStorage authentication priority...")
    
    try:
        # Test 1: Explicit connection string
        storage1 = AzureBlobDeltaLinkStorage_class(
            connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net"
        )
        assert storage1._connection_string is not None
        assert storage1._account_url is None
        await storage1.close()
        print("  ✅ Explicit connection string priority")
        
        # Test 2: Explicit account_url + credential
        from msgraph_delta_query.storage.azure_blob import DefaultAzureCredential
        if DefaultAzureCredential:
            cred = DefaultAzureCredential()
            storage2 = AzureBlobDeltaLinkStorage_class(
                account_url="https://testaccount.blob.core.windows.net",
                credential=cred
            )
            assert storage2._account_url is not None
            assert storage2._connection_string is None
            await storage2.close()
            await cred.close()
            print("  ✅ Explicit account_url + credential priority")
        
        # Test 3: Environment variable priority
        os.environ['AZURE_STORAGE_ACCOUNT_NAME'] = 'testproductionaccount'
        try:
            storage3 = AzureBlobDeltaLinkStorage_class()
            assert storage3._account_url == 'https://testproductionaccount.blob.core.windows.net'
            assert storage3._connection_string is None
            await storage3.close()
            print("  ✅ Managed identity with AZURE_STORAGE_ACCOUNT_NAME priority")
        finally:
            del os.environ['AZURE_STORAGE_ACCOUNT_NAME']
        
        # Test 4: Connection string environment variable
        os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'DefaultEndpointsProtocol=https;AccountName=envtest;AccountKey=test;EndpointSuffix=core.windows.net'
        try:
            storage4 = AzureBlobDeltaLinkStorage_class()
            assert storage4._connection_string is not None
            assert storage4._account_url is None
            await storage4.close()
            print("  ✅ Environment variable connection string priority")
        finally:
            del os.environ['AZURE_STORAGE_CONNECTION_STRING']
        
        # Test 5: local.settings.json fallback
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            settings = {
                "IsEncrypted": False,
                "Values": {
                    "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=localdev;AccountKey=test;EndpointSuffix=core.windows.net"
                }
            }
            json.dump(settings, f, indent=2)
            temp_settings_path = f.name
        
        try:
            storage5 = AzureBlobDeltaLinkStorage_class(local_settings_path=temp_settings_path)
            assert storage5._connection_string is not None
            await storage5.close()
            print("  ✅ local.settings.json fallback priority")
        finally:
            os.unlink(temp_settings_path)
        
        # Test 6: No connection available (should fail)
        try:
            storage_fail = AzureBlobDeltaLinkStorage_class()
            print("❌ Should have failed but didn't")
            await storage_fail.close()
            return False
        except ValueError as e:
            if "Could not establish Azure Blob Storage connection" in str(e):
                print("  ✅ Correctly fails with no connection available")
            else:
                print(f"❌ Unexpected ValueError: {e}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ AzureBlobDeltaLinkStorage creation test failed: {e}")
        return False

async def test_azure_blob_storage_with_azurite():
    """Test AzureBlobDeltaLinkStorage with Azurite if available."""
    print("\n4. Testing AzureBlobDeltaLinkStorage with Azurite...")
    
    try:
        # Check if Azurite connection string is available
        azurite_conn_str = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
        
        storage = AzureBlobDeltaLinkStorage_class(connection_string=azurite_conn_str)
        
        # Try a simple operation to see if Azurite is running
        try:
            test_resource = "test_users"
            test_delta_link = "https://graph.microsoft.com/v1.0/users/delta?$deltatoken=test123"
            test_metadata = {"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Test full cycle
            await storage.set(test_resource, test_delta_link, test_metadata)
            print("  ✅ Set operation with Azurite")
            
            retrieved_link = await storage.get(test_resource)
            assert retrieved_link == test_delta_link
            print(f"  ✅ Get operation with Azurite: {retrieved_link}")
            
            metadata = await storage.get_metadata(test_resource)
            assert metadata is not None
            assert metadata["metadata"]["test"] is True
            print("  ✅ Get metadata with Azurite")
            
            await storage.delete(test_resource)
            deleted_check = await storage.get(test_resource)
            assert deleted_check is None
            print("  ✅ Delete operation with Azurite")
            
            await storage.close()
            print("  ✅ Azurite integration fully functional")
            return True
            
        except Exception as e:
            await storage.close()
            if "No connection could be made" in str(e) or "Connection refused" in str(e) or "ECONNREFUSED" in str(e):
                print("  ⚠️  Azurite not running - skipping live test")
                return True
            else:
                print(f"❌ Azurite test failed: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Azurite setup failed: {e}")
        return False

async def test_client_integration():
    """Test integration with the main client."""
    print("\n5. Testing client integration...")
    
    try:
        from msgraph_delta_query import AsyncDeltaQueryClient
        
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileDeltaLinkStorage_class(temp_dir)
            
            # Create client with proper parameter names
            client = AsyncDeltaQueryClient(
                delta_link_storage=storage
            )
            
            # Verify storage is set correctly
            assert client.delta_link_storage is storage
            print("  ✅ Client accepts delta_link_storage parameter")
            
            # Test storage operations through client
            await client.delta_link_storage.set("integration_test", "test_link", {"from": "client"})
            result = await client.delta_link_storage.get("integration_test")
            assert result == "test_link"
            print("  ✅ Storage operations work through client")
            
            await client._internal_close()
            
        return True
    except Exception as e:
        print(f"❌ Client integration test failed: {e}")
        return False

async def test_examples_compatibility():
    """Test that examples still work with refactored storage."""
    print("\n6. Testing examples compatibility...")
    
    try:
        # Test basic usage example import
        import examples.basic_usage
        print("  ✅ basic_usage.py imports successfully")
        
        # Test other examples
        import examples.simple_azurite_demo
        print("  ✅ simple_azurite_demo.py imports successfully")
        
        import examples.msgraph_blob_sync_demo
        print("  ✅ msgraph_blob_sync_demo.py imports successfully")
        
        return True
    except Exception as e:
        print(f"❌ Examples compatibility test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests and provide summary."""
    tests = [
        ("Import Tests", test_imports),
        ("LocalFileDeltaLinkStorage", test_local_file_storage),
        ("AzureBlobDeltaLinkStorage Creation", test_azure_blob_storage_creation),
        ("AzureBlobDeltaLinkStorage with Azurite", test_azure_blob_storage_with_azurite),
        ("Client Integration", test_client_integration),
        ("Examples Compatibility", test_examples_compatibility),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactored storage system is fully functional.")
    else:
        print("⚠️  Some tests failed. Please review the output above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(run_all_tests())
