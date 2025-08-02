#!/usr/bin/env python3
"""
Test script to verify AzureBlobDeltaLinkStorage priority order.

Priority order:
1. Explicit connection_string parameter
2. Explicit account_url + credential parameters  
3. Managed identity with AZURE_STORAGE_ACCOUNT_NAME env var
4. Environment variables (AZURE_STORAGE_CONNECTION_STRING, AzureWebJobsStorage)
5. Azure Functions local.settings.json (local dev fallback)
"""

import os
import json
import tempfile
import asyncio
from src.msgraph_delta_query.storage import AzureBlobDeltaLinkStorage

async def test_priority_order():
    """Test the credential detection priority order."""
    
    print("=== Testing AzureBlobDeltaLinkStorage Priority Order ===\n")
    
    # Test 1: Explicit connection string (highest priority)
    print("1. Testing explicit connection_string parameter (highest priority)")
    try:
        storage = AzureBlobDeltaLinkStorage(
            connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net"
        )
        print("✅ Explicit connection_string accepted")
        conn_str = storage._connection_string or "None"
        print(f"   Connection string: {conn_str[:50] if conn_str != 'None' else 'None'}...")
        print(f"   Account URL: {storage._account_url}")
        print(f"   Credential: {storage._credential}")
        await storage.close()
    except Exception as e:
        print(f"❌ Error with explicit connection_string: {e}")
    print()
    
    # Test 2: Explicit account_url + credential
    print("2. Testing explicit account_url + credential")
    try:
        from azure.identity.aio import DefaultAzureCredential
        cred = DefaultAzureCredential()
        storage = AzureBlobDeltaLinkStorage(
            account_url="https://testaccount.blob.core.windows.net",
            credential=cred
        )
        print("✅ Explicit account_url + credential accepted")
        print(f"   Connection string: {storage._connection_string}")
        print(f"   Account URL: {storage._account_url}")
        print(f"   Credential: {type(storage._credential).__name__}")
        await storage.close()
        await cred.close()
    except Exception as e:
        print(f"❌ Error with explicit account_url + credential: {e}")
    print()
    
    # Test 3: Managed identity with AZURE_STORAGE_ACCOUNT_NAME (production)
    print("3. Testing managed identity with AZURE_STORAGE_ACCOUNT_NAME env var")
    os.environ['AZURE_STORAGE_ACCOUNT_NAME'] = 'testproductionaccount'
    try:
        storage = AzureBlobDeltaLinkStorage()
        print("✅ Managed identity with AZURE_STORAGE_ACCOUNT_NAME working")
        print(f"   Connection string: {storage._connection_string}")
        print(f"   Account URL: {storage._account_url}")
        print(f"   Credential: {storage._credential}")
        await storage.close()
    except Exception as e:
        print(f"❌ Error with managed identity: {e}")
    finally:
        del os.environ['AZURE_STORAGE_ACCOUNT_NAME']
    print()
    
    # Test 4: Environment variables
    print("4. Testing environment variables (AZURE_STORAGE_CONNECTION_STRING)")
    os.environ['AZURE_STORAGE_CONNECTION_STRING'] = 'DefaultEndpointsProtocol=https;AccountName=envtest;AccountKey=test;EndpointSuffix=core.windows.net'
    try:
        storage = AzureBlobDeltaLinkStorage()
        print("✅ Environment variable connection string working")
        conn_str = storage._connection_string or "None"
        print(f"   Connection string: {conn_str[:50] if conn_str != 'None' else 'None'}...")
        print(f"   Account URL: {storage._account_url}")
        print(f"   Credential: {storage._credential}")
        await storage.close()
    except Exception as e:
        print(f"❌ Error with environment variable: {e}")
    finally:
        del os.environ['AZURE_STORAGE_CONNECTION_STRING']
    print()
    
    # Test 5: Azure Functions local.settings.json (fallback)
    print("5. Testing Azure Functions local.settings.json fallback")
    
    # Create temporary local.settings.json
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        settings = {
            "IsEncrypted": False,
            "Values": {
                "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=localdev;AccountKey=test;EndpointSuffix=core.windows.net",
                "FUNCTIONS_WORKER_RUNTIME": "python"
            }
        }
        json.dump(settings, f, indent=2)
        temp_settings_path = f.name
    
    try:
        storage = AzureBlobDeltaLinkStorage(local_settings_path=temp_settings_path)
        print("✅ Azure Functions local.settings.json fallback working")
        conn_str = storage._connection_string or "None"
        print(f"   Connection string: {conn_str[:50] if conn_str != 'None' else 'None'}...")
        print(f"   Account URL: {storage._account_url}")
        print(f"   Credential: {storage._credential}")
        await storage.close()
    except Exception as e:
        print(f"❌ Error with local.settings.json: {e}")
    finally:
        os.unlink(temp_settings_path)
    print()
    
    # Test 6: No connection available (should fail)
    print("6. Testing no connection available (should fail gracefully)")
    try:
        storage = AzureBlobDeltaLinkStorage()
        print("❌ Should have failed but didn't")
        await storage.close()
    except ValueError as e:
        print(f"✅ Correctly failed with no connection: {str(e)[:100]}...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    print()
    
    print("=== Priority Order Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_priority_order())
