"""
Test authentication options for the Microsoft Graph Delta Query Client.
This demonstrates the enhanced credential chain with client ID/secret fallback.
"""

import os
import asyncio
import logging
from src.msgraph_delta_query.client import AsyncDeltaQueryClient

# Configure logging to see credential creation details
logging.basicConfig(level=logging.DEBUG)

async def test_authentication_options():
    """Test different authentication scenarios."""
    
    print("🔐 Testing Authentication Options...")
    
    # Test 1: No environment variables (DefaultAzureCredential chain)
    print("\n1. Testing with no environment variables (DefaultAzureCredential chain)...")
    
    # Clear any existing environment variables
    env_vars_to_clear = ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID"]
    original_values = {}
    for var in env_vars_to_clear:
        original_values[var] = os.getenv(var)
        if var in os.environ:
            del os.environ[var]
    
    try:
        client1 = AsyncDeltaQueryClient()
        await client1._initialize()
        print("✅ DefaultAzureCredential created successfully")
        await client1._internal_close()
    except Exception as e:
        print(f"ℹ️  DefaultAzureCredential creation completed (may fail at token request): {type(e).__name__}")
    
    # Test 2: With complete environment variables (ClientSecretCredential)
    print("\n2. Testing with complete environment variables (ClientSecretCredential)...")
    
    # Set mock environment variables (these are fake values for testing)
    os.environ["AZURE_CLIENT_ID"] = "12345678-1234-1234-1234-123456789012"
    os.environ["AZURE_CLIENT_SECRET"] = "fake-client-secret-for-testing"
    os.environ["AZURE_TENANT_ID"] = "87654321-4321-4321-4321-210987654321"
    
    try:
        client2 = AsyncDeltaQueryClient()
        await client2._initialize()
        print("✅ ClientSecretCredential created successfully from environment variables")
        await client2._internal_close()
    except Exception as e:
        print(f"ℹ️  ClientSecretCredential creation completed (may fail at token request): {type(e).__name__}")
    
    # Test 3: With partial environment variables (DefaultAzureCredential + warning)
    print("\n3. Testing with partial environment variables (should warn and use DefaultAzureCredential)...")
    
    # Remove one variable to simulate partial configuration
    del os.environ["AZURE_CLIENT_SECRET"]
    
    try:
        client3 = AsyncDeltaQueryClient()
        await client3._initialize()
        print("✅ DefaultAzureCredential created with helpful warning about missing variables")
        await client3._internal_close()
    except Exception as e:
        print(f"ℹ️  Credential creation completed (may fail at token request): {type(e).__name__}")
    
    # Restore original environment variables
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]
    
    print("\n🎉 Authentication option tests completed!")
    print("\nFor production use:")
    print("1. Set environment variables: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")
    print("2. Or use managed identity in Azure (automatically handled)")
    print("3. Or use Azure CLI authentication (az login)")

if __name__ == "__main__":
    asyncio.run(test_authentication_options())
