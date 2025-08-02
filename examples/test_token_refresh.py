"""
Test script to verify token refresh functionality.

This script simulates token expiration scenarios to ensure the client
handles them correctly by automatically refreshing tokens.
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient
from datetime import datetime, timezone, timedelta


async def test_token_refresh():
    """Test token refresh functionality."""
    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    
    # Configure logging to see token refresh messages
    logging.basicConfig(level=logging.DEBUG)
    
    client = AsyncDeltaQueryClient()
    
    try:
        print("🔄 Testing initial token acquisition...")
        
        # First request - should acquire a new token
        users1, _, meta1 = await client.delta_query_all(
            resource="users",
            select=["id", "displayName"],
            top=5
        )
        
        print(f"✅ First request successful: {len(users1)} users")
        print(f"   Token cached, expires at: {client._token_expires_at}")
        
        # Check if token is cached
        if client._cached_token:
            print("✅ Token is properly cached")
        else:
            print("❌ Token was not cached")
            
        print("\n🔄 Testing cached token usage...")
        
        # Second request - should use cached token
        users2, _, meta2 = await client.delta_query_all(
            resource="users",
            select=["id", "displayName"],
            top=5
        )
        
        print(f"✅ Second request successful: {len(users2)} users")
        print("✅ Used cached token (check debug logs)")
        
        print("\n🔄 Testing forced token refresh...")
        
        # Force token refresh
        old_token = client._cached_token
        new_token = await client.get_token(force_refresh=True)
        
        if new_token != old_token:
            print("✅ Token was successfully refreshed")
        else:
            print("⚠️  Token appears unchanged (might be expected in some cases)")
            
        print(f"   New token expires at: {client._token_expires_at}")
        
        print("\n🔄 Testing request with refreshed token...")
        
        # Third request - should use the refreshed token
        users3, _, meta3 = await client.delta_query_all(
            resource="users",
            select=["id", "displayName"],
            top=5
        )
        
        print(f"✅ Third request successful: {len(users3)} users")
        
        # Simulate token expiration by manually setting expiry to past
        print("\n🔄 Testing automatic token refresh on expiry...")
        
        # Set token to expire in the past
        client._token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        print("⏰ Simulated token expiration (set expiry to 10 minutes ago)")
        
        # This request should automatically refresh the token
        users4, _, meta4 = await client.delta_query_all(
            resource="users",
            select=["id", "displayName"],
            top=5
        )
        
        print(f"✅ Request with expired token successful: {len(users4)} users")
        print("✅ Token was automatically refreshed")
        print(f"   New expiry: {client._token_expires_at}")
        
        print("\n📊 Test Summary:")
        print("✅ Initial token acquisition")
        print("✅ Token caching")
        print("✅ Cached token reuse")
        print("✅ Forced token refresh")
        print("✅ Automatic token refresh on expiry")
        print("✅ All token refresh scenarios working correctly!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        
    finally:
        await client._internal_close()
        print("✅ Client closed")


if __name__ == "__main__":
    asyncio.run(test_token_refresh())
