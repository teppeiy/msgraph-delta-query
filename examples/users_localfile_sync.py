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
from msgraph_delta_query.storage import LocalFileDeltaLinkStorage


async def sync_users():
    """Sync users using local file storage for delta links."""
    print("=== User Sync with Local Storage ===")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Setup with deltalinks folder at project root (parent of examples directory)
    storage = LocalFileDeltaLinkStorage(folder="../deltalinks")
    client = AsyncDeltaQueryClient(delta_link_storage=storage)

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

        # Show results using the comprehensive sync results method
        metadata.print_sync_results("Users")

        # Show sample users
        if users:
            print(f"\n📋 Users ({len(users)} total):")
            for i, user in enumerate(users[:5]):
                # Check for deleted users
                if isinstance(user, dict) and user.get("@removed"):
                    user_id = user.get('id', 'N/A')
                    print(f"   🗑️  [DELETED] {user_id}")
                else:
                    # Access user properties (assuming it's a dict based on debug output)
                    if isinstance(user, dict):
                        # The Graph SDK returns snake_case keys instead of camelCase
                        display_name = user.get('display_name') or user.get('displayName', 'N/A')
                        email = user.get('mail') or user.get('userPrincipalName', 'N/A')
                        enabled = user.get('accountEnabled', 'N/A')
                        user_id = user.get('id', 'N/A')
                        user_id_display = user_id[:8] + "..." if user_id and user_id != 'N/A' else 'N/A'
                        
                        print(f"   👤 {display_name}")
                        print(f"      Email: {email}")
                        print(f"      Enabled: {enabled}")
                        print(f"      ID: {user_id_display}")
                        print()
                    else:
                        # Fallback for non-dict objects
                        try:
                            display_name = getattr(user, 'display_name', None) or getattr(user, 'displayName', None) or 'N/A'
                            email = getattr(user, 'mail', None) or getattr(user, 'user_principal_name', None) or getattr(user, 'userPrincipalName', None) or 'N/A'
                            enabled = getattr(user, 'account_enabled', None) or getattr(user, 'accountEnabled', None) or 'N/A'
                            user_id = getattr(user, 'id', None)
                            user_id_display = user_id[:8] + "..." if user_id else 'N/A'
                            
                            print(f"   👤 {display_name}")
                            print(f"      Email: {email}")
                            print(f"      Enabled: {enabled}")
                            print(f"      ID: {user_id_display}")
                            print()
                        except Exception as e:
                            print(f"   ❌ Error accessing user properties: {e}")
            
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
