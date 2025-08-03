"""
Test to specifically check Microsoft Graph behavior with invalid delta links.
Question: When an invalid deltalink is passed, do you get a new deltalink back?
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient


async def test_graph_invalid_deltalink_behavior():
    """Test what Microsoft Graph returns when given an invalid delta link."""
    
    # Load environment variables
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from {env_path}\n")
    
    # Check required variables
    required_vars = ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing: {', '.join(missing_vars)}")
        return
    
    print("=== Testing Microsoft Graph Behavior with Invalid Delta Links ===\n")
    
    client = AsyncDeltaQueryClient()
    
    test_scenarios = [
        {
            "name": "Completely invalid deltatoken",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=completely_invalid_token_123",
            "fallback": False  # Let's see what Graph returns without fallback first
        },
        {
            "name": "Malformed deltatoken", 
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=malformed!@#$%",
            "fallback": False
        },
        {
            "name": "Empty deltatoken",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=",
            "fallback": False
        }
    ]
    
    try:
        # Test each scenario individually with fresh client instances
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"🧪 Scenario {i}: {scenario['name']}")
            print(f"   Delta link: {scenario['delta_link']}")
            print(f"   Fallback: {scenario['fallback']}")
            
            # Create fresh client for each test
            test_client = AsyncDeltaQueryClient()
            
            try:
                apps, new_delta_link, metadata = await test_client.delta_query(
                    resource="applications",
                    select=["id", "displayName"],
                    top=5,  # Small number for testing
                    delta_link=scenario['delta_link'],
                    fallback_to_full_sync=scenario['fallback']
                )
                
                print(f"   ✅ HTTP Success!")
                print(f"   📊 Retrieved: {len(apps)} applications")
                print(f"   🔗 New delta link returned: {new_delta_link is not None}")
                if new_delta_link:
                    print(f"   🔗 New delta link preview: {new_delta_link[:80]}...")
                print(f"   📈 Change summary: {metadata.change_summary}")
                print(f"   ⏰ Sync type: {'Incremental' if metadata.change_summary.timestamp else 'Full'}")
                
            except Exception as e:
                print(f"   ❌ Exception: {type(e).__name__}: {e}")
            
            finally:
                await test_client._internal_close()
            
            print("-" * 60)
    
        # Now test the same scenarios WITH fallback enabled
        print("\n🔄 Testing the SAME scenarios WITH fallback enabled:\n")
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"🧪 Scenario {i} (with fallback): {scenario['name']}")
            print(f"   Delta link: {scenario['delta_link']}")
            print(f"   Fallback: True")
            
            # Create fresh client for each test
            test_client = AsyncDeltaQueryClient()
            
            try:
                apps, new_delta_link, metadata = await test_client.delta_query(
                    resource="applications",
                    select=["id", "displayName"],
                    top=5,
                    delta_link=scenario['delta_link'],
                    fallback_to_full_sync=True  # Enable fallback
                )
                
                print(f"   ✅ Success with fallback!")
                print(f"   📊 Retrieved: {len(apps)} applications")
                print(f"   🔗 New delta link returned: {new_delta_link is not None}")
                if new_delta_link:
                    print(f"   🔗 New delta link preview: {new_delta_link[:80]}...")
                print(f"   📈 Change summary: {metadata.change_summary}")
                print(f"   ⏰ Sync type: {'Incremental' if metadata.change_summary.timestamp else 'Full'}")
                
            except Exception as e:
                print(f"   ❌ Exception: {type(e).__name__}: {e}")
            
            finally:
                await test_client._internal_close()
            
            print("-" * 60)
    
    finally:
        await client._internal_close()
    
    print("\n📋 Summary of Microsoft Graph Behavior:")
    print("1. Invalid delta token → HTTP 400 'Badly formed token'")
    print("2. HTTP 400 response → No data returned, no new delta link")
    print("3. With fallback enabled → Retries as full sync, gets new delta link")
    print("4. With fallback disabled → Returns empty results, no delta link")


if __name__ == "__main__":
    asyncio.run(test_graph_invalid_deltalink_behavior())
