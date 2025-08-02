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
from typing import List, cast, Any, Dict
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient
from msgraph_delta_query.storage import LocalFileDeltaLinkStorage
from msgraph.generated.models.user import User


async def sync_users():
    """Sync users using local file storage for delta links."""
    print("=== User Sync with Local Storage (SDK Objects) ===")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Setup with deltalinks folder at project root (parent of examples directory)
    storage = LocalFileDeltaLinkStorage(folder="../deltalinks")
    client = AsyncDeltaQueryClient(delta_link_storage=storage)

    try:
        print("Syncing users...")
        
        # Get users with delta query - returns User SDK objects
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
        
        # Cast for type hint purposes - objects are User SDK objects
        users = cast(List[User], users)

        # Show results using the comprehensive sync results method
        metadata.print_sync_results("Users")

        # Show sample users
        if users:
            print(f"\n📋 Users ({len(users)} total):")
            for i, user in enumerate(users[:5]):
                # Check for removed objects - SDK objects use additional_data
                removed_info = None
                if hasattr(user, 'additional_data') and user.additional_data and user.additional_data.get("@removed"):
                    removed_info = user.additional_data.get("@removed")
                
                if removed_info:
                    print(f"   🗑️  [DELETED] {user.id or 'Unknown ID'}")
                else:
                    # Access properties using dot notation
                    user_id_display = user.id[:8] + "..." if user.id else 'N/A'
                    email = user.mail or user.user_principal_name or 'N/A'
                    
                    print(f"   👤 {user.display_name or 'N/A'}")
                    print(f"      Email: {email}")
                    print(f"      Enabled: {user.account_enabled or 'N/A'}")
                    print(f"      ID: {user_id_display}")
                    print(f"      Type: {type(user).__name__}")
                    print()
            
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
    # Load .env
    load_dotenv()

    # Set up minimal logging
    logging.basicConfig(level=logging.WARNING)

    # Run the sync
    users = await sync_users()
    
    # Use your data here
    print(f"\n🎯 Ready to use {len(users)} users in your application!")


if __name__ == "__main__":
    asyncio.run(main())
