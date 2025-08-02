"""
Simple User Sync with Azure Blob Storage

This example shows how to sync Microsoft Graph users using Azure Blob Storage
for delta link persistence. Great for production and multi-instance deployments.

Perfect for:
- Production applications
- Multiple application instances
- Cloud deployments
- Shared state across environments
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import cast, List, Dict, Any
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage
from msgraph.generated.models.user import User


async def sync_users():
    """Sync users using Azure Blob Storage for delta links."""
    print("=== User Sync with Azure Blob Storage ===")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Setup Azure Blob Storage for delta links
    # Automatically detects: Environment vars -> local.settings.json -> Azurite
    storage = AzureBlobDeltaLinkStorage(container_name="msgraph-deltalinks")
    client = AsyncDeltaQueryClient(delta_link_storage=storage)

    try:
        print("Syncing users...")
        
        # Get users with delta query - automatically handles full vs incremental sync
        users_data, delta_link, metadata = await client.delta_query_all(
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

        # Cast to SDK objects for better IDE support and dot notation access
        users = cast(List[User], users_data)

        # Show results using the comprehensive sync results method
        metadata.print_sync_results("Users")

        # Show sample users
        if users:
            print(f"\n📋 Users ({len(users)} total):")
            for i, user in enumerate(users[:5]):
                if hasattr(user, '@removed') or (isinstance(user, dict) and user.get("@removed")):
                    user_id = user.id if hasattr(user, 'id') else (user.get('id', 'N/A') if isinstance(user, dict) else 'N/A')
                    print(f"   🗑️  [DELETED] {user_id}")
                else:
                    # Use dot notation for cleaner code
                    display_name = user.display_name or 'N/A'
                    email = user.mail or user.user_principal_name or 'N/A'
                    print(f"   👤 {display_name} ({email})")
            
            if len(users) > 5:
                print(f"   ... and {len(users) - 5} more users")
        else:
            print("\n📋 No changes since last sync")

        print(f"\n☁️  Delta link saved to Azure Blob Storage: msgraph-deltalinks/users.json")
        print(f"💡 Run again to see incremental sync in action!")
        
        return users

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await client._internal_close()
        await storage.close()


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
