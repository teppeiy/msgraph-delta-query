"""
Periodic User Sync Example

This example demonstrates how to set up a continuous synchronization process
that fetches user changes from Microsoft Graph every 15 minutes using delta queries.

Features demonstrated:
1. Continuous background synchronization
2. Delta query optimization (only fetches changes after first sync)
3. Error handling and recovery
4. Graceful shutdown with Ctrl+C
5. Change tracking and reporting
6. Configurable sync intervals
"""

import asyncio
import logging
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient
from typing import Optional


class PeriodicUserSync:
    """A class to handle periodic user synchronization."""
    
    def __init__(self, sync_interval_minutes: float = 15, force_full_sync: bool = False):
        """
        Initialize the periodic sync.
        
        Args:
            sync_interval_minutes: How often to sync (default: 15 minutes)
            force_full_sync: If True, ignore existing deltalink and start with full sync
        """
        self.sync_interval_minutes = sync_interval_minutes
        self.sync_interval_seconds = sync_interval_minutes * 60
        self.force_full_sync = force_full_sync
        self.client: Optional[AsyncDeltaQueryClient] = None  # Initialize client lazily
        self.sync_count = 0
        self.is_running = False
        self.start_time = None
    
    async def _ensure_client(self):
        """Ensure the client is initialized and ready."""
        if self.client is None:
            self.client = AsyncDeltaQueryClient()
    
    async def check_existing_deltalink(self) -> bool:
        """Check if an existing deltalink file exists for users."""
        await self._ensure_client()
        if self.client is None:
            return False
        stored_deltalink = await self.client.delta_link_storage.get("users")
        return stored_deltalink is not None
    
    async def sync_users(self) -> bool:
        """
        Perform a single user sync.
        
        Returns:
            bool: True if sync was successful, False otherwise
        """
        self.sync_count += 1
        sync_start = datetime.now(timezone.utc)
        
        try:
            print(f"🔄 Starting sync #{self.sync_count} at {sync_start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Ensure client is ready
            await self._ensure_client()
            if self.client is None:
                raise RuntimeError("Failed to initialize client")
            
            # Check if this will be a full sync or incremental sync
            stored_deltalink = await self.client.delta_link_storage.get("users")
            
            # Handle force full sync option
            if self.force_full_sync and self.sync_count == 1:
                if stored_deltalink:
                    print("   🔄 Force full sync requested - ignoring existing deltalink...")
                    # Delete the existing deltalink to force full sync
                    await self.client.delta_link_storage.delete("users")
                    stored_deltalink = None
                else:
                    print("   📦 Full sync - no existing deltalink found...")
            elif stored_deltalink:
                print("   📥 Incremental sync - checking for changes since last sync...")
            else:
                print("   📦 Full sync - this may take several minutes for large tenants...")
            
            # Use the library's built-in delta_query_all which handles timestamps correctly
            users, delta_link, user_meta = await self.client.delta_query_all(
                resource="users",
                select=[
                    "id", "displayName", "mail", "userPrincipalName", 
                    "accountEnabled", "createdDateTime"
                ],
                top=1000
            )
            
            # Report final results using the library's metadata
            print(f"✅ Sync #{self.sync_count} completed in {user_meta.duration_seconds:.2f}s")
            print(f"   📊 {user_meta.change_summary}")  # This has the correct timestamp
            print(f"   📈 Processed {user_meta.pages_fetched} pages, {len(users)} total users")
            
            # Show sample of changes if any
            if len(users) > 0:
                print(f"   Sample users from this sync:")
                for i, user in enumerate(users[:5]):
                    enabled_status = "✅" if user.get('accountEnabled', True) else "❌"
                    print(f"     {i+1}. {enabled_status} {user.get('displayName', 'N/A')} - {user.get('createdDateTime', 'N/A')}")
                if len(users) > 5:
                    print(f"     ... and {len(users) - 5} more users")
            else:
                print("   No changes detected since last sync")
            
            return True
            
        except Exception as e:
            print(f"❌ Sync #{self.sync_count} failed: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return False
    
    async def start_periodic_sync(self):
        """Start the periodic synchronization process."""
        self.is_running = True
        self.start_time = datetime.now(timezone.utc)
        
        print("=== Periodic User Sync Started ===")
        print(f"⏱️  Sync interval: {self.sync_interval_minutes} minutes")
        print(f"📅 Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("🛑 Press Ctrl+C to stop\n")
        
        try:
            while self.is_running:
                # Perform sync
                success = await self.sync_users()
                
                # Calculate next sync time
                if not success:
                    print("⚠️  Sync failed, but will retry at next interval")
                
                print(f"⏰ Waiting {self.sync_interval_minutes} minutes until next sync... (Ctrl+C to stop)")
                print("-" * 60)
                
                # Wait for next sync interval
                try:
                    await asyncio.sleep(self.sync_interval_seconds)
                except asyncio.CancelledError:
                    # Sleep was cancelled, likely due to KeyboardInterrupt
                    break
                
        except KeyboardInterrupt:
            print(f"\n🛑 Periodic sync stopped by user")
        except Exception as e:
            print(f"❌ Periodic sync error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the periodic sync and cleanup."""
        self.is_running = False
        
        if self.start_time:
            runtime = datetime.now(timezone.utc) - self.start_time
            print(f"\n📊 Sync Statistics:")
            print(f"   Total runtime: {runtime}")
            print(f"   Total syncs completed: {self.sync_count}")
            print(f"   Average sync interval: {runtime.total_seconds() / max(self.sync_count, 1) / 60:.1f} minutes")
        
        if self.client is not None:
            await self.client._internal_close()
            print("✅ Client properly closed")
        else:
            print("✅ No client to close")


async def demo_quick_sync(force_full_sync: bool = False):
    """Demo version with shorter intervals for testing."""
    print("=== Quick Demo (60-second intervals) ===")
    print("This demo runs every 60 seconds for testing purposes")
    if force_full_sync:
        print("🔄 Force full sync mode enabled - will ignore existing deltalink")
    print("Press Ctrl+C to stop\n")
    
    sync = PeriodicUserSync(sync_interval_minutes=1, force_full_sync=force_full_sync)  # 60 seconds
    await sync.start_periodic_sync()


async def main():
    """Main function to set up and run periodic sync."""
    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️  No .env file found at {env_path}")
        print("Please create a .env file with your Azure credentials")
        return
    
    # Verify required environment variables
    required_vars = ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return
        
    print(f"🔐 Using Azure Tenant: {os.getenv('AZURE_TENANT_ID')}")
    print(f"🔐 Using Azure Client: {os.getenv('AZURE_CLIENT_ID')}")
    
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise from Azure SDK
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check if existing deltalink exists
    temp_client = AsyncDeltaQueryClient()
    existing_deltalink = await temp_client.delta_link_storage.get("users")
    await temp_client._internal_close()
    
    if existing_deltalink:
        print(f"\n📋 Existing deltalink found for users - incremental sync available")
        # Get metadata to show when last sync was
        temp_client = AsyncDeltaQueryClient()
        metadata = await temp_client.delta_link_storage.get_metadata("users")
        if metadata and metadata.get("last_updated"):
            try:
                from datetime import datetime
                last_updated = datetime.fromisoformat(metadata["last_updated"].replace('Z', '+00:00'))
                print(f"   Last sync: {last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            except:
                pass
        await temp_client._internal_close()
    else:
        print(f"\n📋 No existing deltalink found - will start with full sync")
    
    # Ask user for sync mode
    print("\nChoose sync mode:")
    print("1. Production sync (every 15 minutes)")
    print("2. Demo sync (every 60 seconds)")
    if existing_deltalink:
        print("3. Production sync with force full sync (ignore existing deltalink)")
        print("4. Demo sync with force full sync (ignore existing deltalink)")
        choice_prompt = "Enter choice (1-4): "
    else:
        choice_prompt = "Enter choice (1-2): "
    
    try:
        choice = input(choice_prompt).strip()
        
        if choice == "1":
            # Production sync every 15 minutes
            sync = PeriodicUserSync(sync_interval_minutes=15)
            await sync.start_periodic_sync()
        elif choice == "2":
            # Demo sync every 60 seconds
            await demo_quick_sync()
        elif choice == "3" and existing_deltalink:
            # Production sync with force full sync
            sync = PeriodicUserSync(sync_interval_minutes=15, force_full_sync=True)
            await sync.start_periodic_sync()
        elif choice == "4" and existing_deltalink:
            # Demo sync with force full sync
            await demo_quick_sync(force_full_sync=True)
        else:
            print("Invalid choice. Defaulting to demo mode...")
            await demo_quick_sync()
            
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        pass
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
