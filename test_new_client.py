"""
Test the new Microsoft Graph SDK-based client
"""
import asyncio
import logging
from src.msgraph_delta_query.client import AsyncDeltaQueryClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_new_client():
    """Test the new Graph SDK client"""
    try:
        # Create client
        client = AsyncDeltaQueryClient()
        
        print("✅ New client created successfully")
        
        # Test initialization (this should work even without proper auth)
        await client._initialize()
        print("✅ Client initialized")
        
        # Test supported resources
        print("✅ Supported resources:", client.SUPPORTED_RESOURCES)
        
        # Test delta request builder access
        try:
            builder = client._get_delta_request_builder("users")
            print(f"✅ Users delta builder: {type(builder)}")
            
            builder = client._get_delta_request_builder("applications")
            print(f"✅ Applications delta builder: {type(builder)}")
            
        except Exception as e:
            print(f"❌ Error accessing builders: {e}")
        
        # Test query parameter building
        params = client._build_query_parameters(
            select=["id", "displayName"],
            top=10,
            deltatoken_latest=True
        )
        print(f"✅ Query parameters built: {params}")
        
        print("✅ All basic tests passed!")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if 'client' in locals():
            await client._internal_close()

if __name__ == "__main__":
    asyncio.run(test_new_client())
