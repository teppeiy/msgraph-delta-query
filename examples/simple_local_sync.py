"""
Simple User Sync with Local Storage

This is the simplest way to sync Microsoft Graph users using local file storage.
Delta links are automatically stored in a local 'deltalinks' folder.

Perfect for:
- Development and testing
- Single-machine applications
- Getting started with the library
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient


async def sync_users():
    """Sync users using local file storage for delta links."""
    print("=== User Sync with Local Storage ===")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Simple client setup - uses local file storage by default
    client = AsyncDeltaQueryClient()

    try:
        print("Syncing users...")
        
        # Get users with delta query - automatically handles full vs incremental sync
        users, delta_link, metadata = await client.delta_query_all(
            resource="users",
            select=[
                "id", 
                "displayName", 
                "mail", 
                "userPrincipalName", 
                "accountEnabled"
            ],
            top=1000
        )

        # Show results
        print(f"✓ Sync completed in {metadata.duration_seconds:.2f}s")
        print(f"✓ {metadata.change_summary}")
        
        sync_type = "Incremental" if metadata.used_stored_deltalink else "Full"
        print(f"✓ Sync type: {sync_type}")

        # Show sample users
        if users:
            print(f"\n📋 Users ({len(users)} total):")
            for i, user in enumerate(users[:5]):
                if user.get("@removed"):
                    print(f"   🗑️  [DELETED] {user.get('id', 'N/A')}")
                else:
                    display_name = user.get('displayName', 'N/A')
                    email = user.get('mail', user.get('userPrincipalName', 'N/A'))
                    print(f"   👤 {display_name} ({email})")
            
            if len(users) > 5:
                print(f"   ... and {len(users) - 5} more users")
        else:
            print("\n📋 No changes since last sync")

        print(f"\n💾 Delta link saved to: deltalinks/users.json")
        print(f"💡 Run again to see incremental sync in action!")
        
        return users

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
    users = await sync_users()
    
    # Use your data here
    print(f"\n🎯 Ready to use {len(users)} users in your application!")


if __name__ == "__main__":
    asyncio.run(main())
