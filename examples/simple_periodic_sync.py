"""
Simple Periodic Sync Example

This example demonstrates how to run periodic synchronization of a single
object type (users) with configurable intervals. Each sync automatically
handles incremental updates using stored delta links.

Features:
- Configurable sync interval
- Automatic incremental sync
- Clean client lifecycle management
- Graceful shutdown handling
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage


class PeriodicUserSync:
    """Handles periodic user synchronization with graceful shutdown."""
    
    def __init__(self, interval_minutes: int = 15, use_azure_storage: bool = False):
        """
        Initialize periodic sync.
        
        Args:
            interval_minutes: How often to run sync (default: 15 minutes)
            use_azure_storage: If True, uses Azure Blob Storage for delta links
        """
        self.interval_minutes = interval_minutes
        self.use_azure_storage = use_azure_storage
        self.running = True
        self.sync_count = 0
        
    async def run_single_sync(self) -> bool:
        """
        Run a single user sync operation.
        
        Returns:
            bool: True if sync was successful, False otherwise
        """
        self.sync_count += 1
        print(f"\nStarting sync #{self.sync_count} at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Create fresh client for each sync (recommended pattern)
        storage = None
        if self.use_azure_storage:
            storage = AzureBlobDeltaLinkStorage(container_name="msgraph-deltalinks")
            client = AsyncDeltaQueryClient(delta_link_storage=storage)
        else:
            client = AsyncDeltaQueryClient()
        
        try:
            # Run delta query - automatically uses incremental sync if delta link exists
            users, delta_link, metadata = await client.delta_query_all(
                resource="users",
                select=[
                    "id",
                    "displayName", 
                    "mail",
                    "userPrincipalName",
                    "accountEnabled",
                    "lastSignInDateTime"
                ],
                top=1000
            )
            
            # Report results
            print(f"Sync #{self.sync_count} completed in {metadata.duration_seconds:.2f}s")
            print(f"Changes: {metadata.change_summary}")
            
            # Show sync type
            if metadata.used_stored_deltalink:
                print("Type: Incremental sync")
            else:
                print("Type: Full sync (first run or reset)")
            
            # Show sample of changes if any
            if users:
                print(f"Users processed: {len(users)}")
                
                # Show sample of new/updated users
                new_users = [u for u in users[:3] if not u.get("@removed")]
                if new_users:
                    print("   New/Updated:")
                    for i, user in enumerate(new_users):
                        print(f"   {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
                
                # Show deleted users if any
                deleted_users = [u for u in users[:3] if u.get("@removed")]
                if deleted_users:
                    print("   Deleted:")
                    for user in deleted_users:
                        print(f"   [DELETED] {user.get('id', 'N/A')}")
            else:
                print("No changes detected")
            
            return True
            
        except Exception as e:
            print(f"Sync #{self.sync_count} failed: {e}")
            return False
        finally:
            # Always clean up the client
            await client._internal_close()
            if storage is not None:
                await storage.close()
    
    async def run_periodic_sync(self):
        """Run periodic synchronization until stopped."""
        storage_type = "Azure Blob Storage" if self.use_azure_storage else "Local File Storage"
        print(f"Starting periodic user sync (every {self.interval_minutes} minutes)")
        print(f"Storage: {storage_type}")
        print(f"Press Ctrl+C to stop gracefully")
        if self.use_azure_storage:
            print(f"Delta links stored in Azure Blob Storage container: msgraph-deltalinks")
        else:
            print(f"Delta links stored in: deltalinks/users.json")
        
        while self.running:
            try:
                # Run sync
                success = await self.run_single_sync()
                
                if success:
                    print(f"Next sync in {self.interval_minutes} minutes...")
                else:
                    print(f"Retrying in {self.interval_minutes} minutes...")
                
                # Wait for next sync (with early exit if stopped)
                for i in range(self.interval_minutes * 60):  # Convert minutes to seconds
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                print("\nGraceful shutdown requested...")
                self.running = False
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                print(f"Retrying in {self.interval_minutes} minutes...")
                
                # Wait before retry
                for i in range(self.interval_minutes * 60):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
        
        print(f"Periodic sync stopped after {self.sync_count} sync operations")
    
    def stop(self):
        """Signal the periodic sync to stop."""
        self.running = False


async def main():
    """Main function to run periodic sync."""
    # Load environment variables
    load_dotenv()
    print("ℹ️  No .env file found, using system environment variables" if not Path(".env").exists() else "✅ Loaded .env file")
    print("💡 Create a .env file in the root directory with AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")
    print("   or use Azure CLI (az login) or managed identity in Azure")

    # Set up logging (optional)
    logging.basicConfig(
        level=logging.WARNING,  # Only show warnings and errors
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Storage options
    print("=== Storage Options ===")
    print("Available storage backends:")
    print("1. Local File Storage (default)")
    print("2. Azure Blob Storage")
    print()
    
    # Check storage configuration
    use_azure = False
    if os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.path.exists("local.settings.json"):
        print("Azure storage configuration detected!")
        print("Set environment variable USE_AZURE_STORAGE=true to use Azure Blob Storage")
        use_azure = os.getenv("USE_AZURE_STORAGE", "").lower() == "true"
    else:
        print("No Azure storage configuration found - using local file storage")
    print()

    # Create sync manager
    # You can customize the interval here (default: 15 minutes)
    interval_minutes = 5  # Sync every 5 minutes for demo
    sync_manager = PeriodicUserSync(
        interval_minutes=interval_minutes,
        use_azure_storage=use_azure
    )
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, initiating graceful shutdown...")
        sync_manager.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run periodic sync
        await sync_manager.run_periodic_sync()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received")
        sync_manager.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
