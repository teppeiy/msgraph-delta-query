"""
Simple Application Sync Example for msgraph-delta-query.

Basic example showing how to sync Microsoft Graph applications 
using Azure Blob Storage for delta link persistence.
"""

import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage


async def simple_app_sync():
    """Simple application synchronization example."""
    print("=== Simple Application Sync ===\n")
    
    # Just use empty constructor - automatic detection!
    storage = AzureBlobDeltaLinkStorage()
    client = AsyncDeltaQueryClient(delta_link_storage=storage)
    
    try:
        print("🔄 Syncing applications...")
        
        # Simple delta query for applications
        apps, delta_link, metadata = await client.delta_query_all(
            resource="applications",
            select=["id", "displayName", "appId"],
            top=50
        )
        
        print(f"✅ Retrieved {len(apps)} applications in {metadata.duration_seconds:.2f}s")
        print(f"📊 {metadata.change_summary}")
        
        # Show sample applications
        if len(apps) > 0:
            print(f"\n📱 Applications:")
            for i, app in enumerate(apps[:5]):
                removed_info = app.get('@removed')
                if removed_info:
                    print(f"   🗑️  {i+1}. [DELETED] ID: {app.get('id', 'N/A')}")
                else:
                    print(f"   ✨ {i+1}. {app.get('displayName', 'N/A')} (AppID: {app.get('appId', 'N/A')})")
            
            if len(apps) > 5:
                print(f"   ... and {len(apps) - 5} more applications")
        else:
            print("📭 No changes detected (delta query working!)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await storage.close()


async def main():
    """Run simple application sync."""
    # Configure logging to show info messages but filter out verbose Azure SDK logs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Reduce verbosity of Azure SDK loggers
    logging.getLogger('azure.storage.blob').setLevel(logging.WARNING)
    logging.getLogger('azure.identity').setLevel(logging.WARNING)
    logging.getLogger('azure.core').setLevel(logging.WARNING)
    
    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from {env_path}\n")
    
    # Check required variables
    required_vars = ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing: {', '.join(missing_vars)}")
        return
    
    print(f"🔐 Tenant: {os.getenv('AZURE_TENANT_ID')}")
    print(f"🔐 Client: {os.getenv('AZURE_CLIENT_ID')}\n")
    
    # Run the simple sync
    await simple_app_sync()
    
    print("\n🎉 Done! Run again to see incremental changes.")


if __name__ == "__main__":
    asyncio.run(main())
