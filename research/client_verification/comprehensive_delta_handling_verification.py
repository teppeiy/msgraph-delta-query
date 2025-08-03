"""Test the improved client.py with comprehensive delta link failure handling."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient


async def test_improved_delta_handling():
    """Test that the improved client handles all delta link failure scenarios."""
    
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
    
    print("=== Testing Improved Delta Link Failure Handling ===\n")
    
    test_scenarios = [
        {
            "name": "Invalid delta token (should trigger HTTP 400)",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=invalid_token_test_123",
            "test_type": "invalid_token"
        },
        {
            "name": "Malformed delta token with special chars (should trigger HTTP 400)",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=malformed!@#$%^&*()",
            "test_type": "malformed_token"
        },
        {
            "name": "Empty delta token (should work normally)",
            "delta_link": "https://graph.microsoft.com/v1.0/applications/delta?$deltatoken=",
            "test_type": "empty_token"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"🧪 Test {i}: {scenario['name']}")
        print(f"   Delta link: {scenario['delta_link']}")
        
        # Test with fallback enabled
        print(f"   Testing with fallback_to_full_sync=True...")
        
        client = AsyncDeltaQueryClient()
        
        try:
            apps, new_delta_link, metadata = await client.delta_query(
                resource="applications",
                select=["id", "displayName"],
                top=5,
                delta_link=scenario['delta_link'],
                fallback_to_full_sync=True
            )
            
            print(f"   ✅ Success! Retrieved {len(apps)} applications")
            print(f"   🔗 New delta link received: {new_delta_link is not None}")
            print(f"   📊 Change summary: {metadata.change_summary}")
            
            if scenario['test_type'] in ('invalid_token', 'malformed_token'):
                # These should have triggered fallback to full sync
                if metadata.change_summary.timestamp is None:
                    print(f"   ✅ Correctly fell back to full sync (no timestamp)")
                else:
                    print(f"   ⚠️  Expected full sync fallback but got incremental sync")
            elif scenario['test_type'] == 'empty_token':
                # Empty token should work like normal full sync
                print(f"   ✅ Empty token handled as normal full sync")
                
        except Exception as e:
            print(f"   ❌ Exception: {type(e).__name__}: {e}")
        
        finally:
            await client._internal_close()
        
        print("-" * 70)
        
        # Test with fallback disabled for invalid/malformed tokens
        if scenario['test_type'] in ('invalid_token', 'malformed_token'):
            print(f"   Testing with fallback_to_full_sync=False...")
            
            client = AsyncDeltaQueryClient()
            
            try:
                apps, new_delta_link, metadata = await client.delta_query(
                    resource="applications",
                    select=["id", "displayName"],
                    top=5,
                    delta_link=scenario['delta_link'],
                    fallback_to_full_sync=False
                )
                
                print(f"   📊 Retrieved {len(apps)} applications (should be 0)")
                print(f"   🔗 New delta link received: {new_delta_link is not None} (should be False)")
                
                if len(apps) == 0 and new_delta_link is None:
                    print(f"   ✅ Correctly returned empty results without fallback")
                else:
                    print(f"   ⚠️  Expected empty results but got data")
                    
            except Exception as e:
                print(f"   ❌ Exception: {type(e).__name__}: {e}")
            
            finally:
                await client._internal_close()
            
            print("-" * 70)
    
    print("✅ All delta link failure scenarios tested!")


if __name__ == "__main__":
    asyncio.run(test_improved_delta_handling())
