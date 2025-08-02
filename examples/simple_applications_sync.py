"""
Simple Application Sync with Local Storage

This example shows how to sync Microsoft Graph applications using local file storage.
Delta links are automatically stored in a local 'deltalinks' folder.

Perfect for:
- Monitoring application changes
- Security auditing
- Application inventory management
- Development and testing
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient


async def sync_applications():
    """Sync applications using local file storage for delta links."""
    print("=== Application Sync with Local Storage ===")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Simple client setup - uses local file storage by default
    client = AsyncDeltaQueryClient()

    try:
        print("Syncing applications...")
        
        # Get applications with delta query - automatically handles full vs incremental sync
        applications, delta_link, metadata = await client.delta_query_all(
            resource="applications",
            select=[
                "id", 
                "displayName", 
                "appId",
                "createdDateTime",
                "publisherDomain",
                "signInAudience"
            ],
            top=1000
        )

        # Show results
        print(f"✓ Sync completed in {metadata.duration_seconds:.2f}s")
        print(f"✓ {metadata.change_summary}")
        
        sync_type = "Incremental" if metadata.used_stored_deltalink else "Full"
        print(f"✓ Sync type: {sync_type}")

        # Show sample applications
        if applications:
            print(f"\n📋 Applications ({len(applications)} total):")
            for i, app in enumerate(applications[:5]):
                if app.get("@removed"):
                    print(f"   🗑️  [DELETED] {app.get('id', 'N/A')}")
                else:
                    display_name = app.get('displayName', 'N/A')
                    app_id = app.get('appId', 'N/A')
                    publisher = app.get('publisherDomain', 'N/A')
                    audience = app.get('signInAudience', 'N/A')
                    created = app.get('createdDateTime', 'N/A')
                    
                    print(f"   📱 {display_name}")
                    print(f"      App ID: {app_id}")
                    print(f"      Publisher: {publisher}")
                    print(f"      Audience: {audience}")
                    print(f"      Created: {created}")
                    print()
            
            if len(applications) > 5:
                print(f"   ... and {len(applications) - 5} more applications")
        else:
            print("\n📋 No changes since last sync")

        print(f"\n💾 Delta link saved to: deltalinks/applications.json")
        print(f"💡 Run again to see incremental sync in action!")
        
        return applications

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await client._internal_close()


async def main():
    """Load environment and run sync."""
    # Load .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    # Set up minimal logging
    logging.basicConfig(level=logging.WARNING)

    # Run the sync
    applications = await sync_applications()
    
    # Use your data here
    print(f"\n🎯 Ready to use {len(applications)} applications in your application!")


if __name__ == "__main__":
    asyncio.run(main())
