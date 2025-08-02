#!/usr/bin/env python3
"""Simple test to identify the periodic sync issue."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient

async def test_users_sync():
    """Test a simple users sync to identify the issue."""
    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    
    print(f"🔐 Using Azure Tenant: {os.getenv('AZURE_TENANT_ID')}")
    print(f"🔐 Using Azure Client: {os.getenv('AZURE_CLIENT_ID')}")
    
    client = AsyncDeltaQueryClient()
    
    try:
        print("🔄 Testing users delta query...")
        users, delta_link, user_meta = await client.delta_query_all(
            resource="users",
            select=["id", "displayName", "mail", "userPrincipalName", "accountEnabled"],
            top=10  # Small number for testing
        )
        
        print(f"✅ Success! Retrieved {len(users)} users in {user_meta.duration_seconds:.2f}s")
        print(f"📊 {user_meta.change_summary}")
        
        if len(users) > 0:
            print("Sample users:")
            for i, user in enumerate(users[:3]):
                print(f"  {i+1}. {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        
    finally:
        await client._internal_close()
        print("✅ Client closed")

if __name__ == "__main__":
    asyncio.run(test_users_sync())
