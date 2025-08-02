"""
Simple Full and Incremental Sync Example

This example demonstrates the core functionality of msgraph-delta-query:
1. First run: Full sync (gets all users)
2. Subsequent runs: Incremental sync (gets only changes since last run)

The delta link is automatically persisted, so incremental sync works
across application restarts.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage


async def simple_user_sync(use_azure_storage=False):
    """
    Simple user synchronization that automatically handles full vs incremental sync.
    
    - First run: Full sync (no existing delta link)
    - Subsequent runs: Incremental sync (uses stored delta link)
    
    Args:
        use_azure_storage: If True, uses Azure Blob Storage for delta links.
                          If False, uses local file storage (default).
    """
    storage_type = "Azure Blob Storage" if use_azure_storage else "Local File Storage"
    print("=== Simple User Sync Example ===")
    print(f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Storage: {storage_type}\n")

    # Choose storage based on parameter
    storage = None
    if use_azure_storage:
        # Azure Blob Storage - automatically detects connection settings
        # Priority: Environment vars > local.settings.json > Azurite fallback
        storage = AzureBlobDeltaLinkStorage(container_name="msgraph-deltalinks")
        client = AsyncDeltaQueryClient(delta_link_storage=storage)
        print("Using Azure Blob Storage for delta link persistence")
        print("  - Checks AZURE_STORAGE_CONNECTION_STRING environment variable")
        print("  - Falls back to local.settings.json if present")
        print("  - Falls back to Azurite (localhost:10000) for development")
    else:
        # Local file storage (default)
        client = AsyncDeltaQueryClient()
        print("Using Local File Storage for delta link persistence")
        print("  - Delta links stored in: deltalinks/ directory")

    try:
        print("Running user sync...")
        
        # This automatically determines if it's a full or incremental sync
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

        # Display results
        print(f"Sync completed in {metadata.duration_seconds:.2f}s")
        print(f"Changes: {metadata.change_summary}")
        print(f"Delta link stored: {delta_link is not None}")
        
        # Show sync type
        if metadata.used_stored_deltalink:
            print("Type: Incremental sync (using existing delta link)")
        else:
            print("Type: Full sync (first run or reset)")

        # Display sample users
        if users:
            print(f"\nSample users ({len(users)} total):")
            for i, user in enumerate(users[:5]):
                # Check if user was deleted
                if user.get("@removed"):
                    print(f"   [DELETED] {user.get('id', 'N/A')}")
                else:
                    print(f"   {i+1}. {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
            
            if len(users) > 5:
                print(f"   ... and {len(users) - 5} more users")
        else:
            print("\nNo users found (or no changes since last sync)")

        # Show next steps
        print(f"\nNext steps:")
        print(f"   - Run this script again to see incremental sync in action")
        if use_azure_storage:
            print(f"   - Delta link is stored in Azure Blob Storage container: msgraph-deltalinks")
            print(f"   - Delete the blob 'users.json' to force a full sync")
        else:
            print(f"   - Delta link is stored in: deltalinks/users.json")
            print(f"   - Delete deltalinks/users.json to force a full sync")

    except Exception as e:
        print(f"Error during sync: {e}")
        raise
    finally:
        # Clean up
        await client._internal_close()
        if storage is not None:
            await storage.close()


async def main():
    """Main function to run the example."""
    # Load environment variables from .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        print("Loaded environment variables from .env file")
    else:
        print("No .env file found - using environment variables")

    # Set up logging (optional)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Demonstrate storage options
    print("=== Storage Options Demo ===")
    print("This example can use two different storage backends:")
    print("1. Local File Storage (default) - stores delta links in local files")
    print("2. Azure Blob Storage - stores delta links in Azure cloud storage")
    print()
    
    # Check if user wants to use Azure Blob Storage
    use_azure = False
    if os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.path.exists("local.settings.json"):
        print("Azure storage configuration detected!")
        print("Set environment variable USE_AZURE_STORAGE=true to use Azure Blob Storage")
        use_azure = os.getenv("USE_AZURE_STORAGE", "").lower() == "true"
    else:
        print("No Azure storage configuration found - using local file storage")
    print()

    # Run the sync with chosen storage
    await simple_user_sync(use_azure_storage=use_azure)


if __name__ == "__main__":
    asyncio.run(main())
