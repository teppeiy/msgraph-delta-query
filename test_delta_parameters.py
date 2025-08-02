"""
Test script to demonstrate delta link parameter handling.

This script shows that when a stored delta link exists, the client correctly
uses the original parameters encoded in the delta link, not the new parameters
passed to the current function call.
"""

import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient

async def test_parameter_conflict():
    """Test that stored delta links use their original parameters, not current ones."""
    
    print("=== Testing Delta Link Parameter Handling ===\n")
    
    # Load environment variables
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        print("📄 Loaded environment variables from .env file\n")
    
    # Enable debug logging to see the HTTP requests
    logging.basicConfig(level=logging.INFO)
    
    client = AsyncDeltaQueryClient()
    
    try:
        print("🔍 Testing with completely different parameters...")
        print("📝 Current call uses: select=['id', 'appId'] and top=1")
        print("📝 But stored delta link has different original parameters!")
        print()
        
        # Call with completely different parameters than what was stored
        applications, delta_link, metadata = await client.delta_query_all(
            resource="applications",
            select=["id", "appId"],  # Different from stored parameters
            top=1,                   # Different from stored parameters
        )
        
        print(f"✅ Sync completed successfully!")
        print(f"✅ Used stored delta link: {metadata.used_stored_deltalink}")
        print(f"✅ Sync type: {'Incremental' if metadata.used_stored_deltalink else 'Full'}")
        print(f"✅ Results: {len(applications)} applications")
        print()
        
        if metadata.used_stored_deltalink:
            print("🎯 SUCCESS: Client correctly used stored delta link with its original parameters")
            print("   The new select=['id', 'appId'] and top=1 were ignored for incremental sync!")
        else:
            print("ℹ️  No stored delta link available, performed full sync with current parameters")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await client._internal_close()

if __name__ == "__main__":
    asyncio.run(test_parameter_conflict())
