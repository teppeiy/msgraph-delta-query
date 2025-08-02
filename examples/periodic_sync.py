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
    
    def __init__(self, sync_interval_minutes: float = 15):
        """
        Initialize the periodic sync.
        
        Args:
            sync_interval_minutes: How often to sync (default: 15 minutes)
        """
        self.sync_interval_minutes = sync_interval_minutes
        self.sync_interval_seconds = sync_interval_minutes * 60
        self.client: Optional[AsyncDeltaQueryClient] = None  # Initialize client lazily
        self.sync_count = 0
        self.is_running = False
        self.start_time = None
    
    async def _ensure_client(self):
        """Ensure the client is initialized and ready."""
        if self.client is None:
            self.client = AsyncDeltaQueryClient()
    
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
            if stored_deltalink:
                print("   📥 Incremental sync - checking for changes since last sync...")
            else:
                print("   📦 Full sync - this may take several minutes for large tenants...")
            
            # Use streaming to show progress for large datasets
            total_users = 0
            page_count = 0
            users_list = []
            last_page_meta = None
            
            print("   🔄 Fetching users in batches...")
            async for users_batch, page_meta in self.client.delta_query_stream(
                resource="users",
                select=[
                    "id", "displayName", "mail", "userPrincipalName", 
                    "accountEnabled", "createdDateTime"
                ],
                top=1000  # Larger batch size for better performance
            ):
                page_count += 1
                total_users += len(users_batch)
                users_list.extend(users_batch)
                last_page_meta = page_meta
                
                # Show progress every few pages
                if page_count % 5 == 0 or len(users_batch) < 1000:  # Show progress every 5 pages or on last page
                    print(f"   📊 Page {page_count}: {len(users_batch)} users (Total: {total_users})")
                    print(f"       Changes so far: {page_meta.total_new_or_updated} new/updated, "
                          f"{page_meta.total_deleted} deleted, {page_meta.total_changed} changed")
                
                # If we have a delta link, we're done
                if page_meta.delta_link:
                    print(f"   ✅ Delta link received - sync complete!")
                    break
            
            sync_duration = (datetime.now(timezone.utc) - sync_start).total_seconds()
            
            # Create summary metadata (approximate since we used streaming)
            from msgraph_delta_query.models import ChangeSummary
            
            # Get final metadata by checking the last page_meta
            if last_page_meta:
                change_summary = ChangeSummary(
                    new_or_updated=last_page_meta.total_new_or_updated,
                    deleted=last_page_meta.total_deleted,
                    changed=last_page_meta.total_changed,
                    timestamp=None if not stored_deltalink else sync_start
                )
            else:
                # Fallback if no pages were processed
                change_summary = ChangeSummary(
                    new_or_updated=total_users,
                    deleted=0,
                    changed=0,
                    timestamp=None if not stored_deltalink else sync_start
                )
            
            # Report final results
            print(f"✅ Sync #{self.sync_count} completed in {sync_duration:.2f}s")
            print(f"   📊 {change_summary}")
            print(f"   📈 Processed {page_count} pages, {total_users} total users")
            
            # Show sample of changes if any
            if len(users_list) > 0:
                print(f"   Sample users from this sync:")
                for i, user in enumerate(users_list[:5]):
                    enabled_status = "✅" if user.get('accountEnabled', True) else "❌"
                    print(f"     {i+1}. {enabled_status} {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
                if len(users_list) > 5:
                    print(f"     ... and {len(users_list) - 5} more users")
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
                await asyncio.sleep(self.sync_interval_seconds)
                
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


async def demo_quick_sync():
    """Demo version with shorter intervals for testing."""
    print("=== Quick Demo (30-second intervals) ===")
    print("This demo runs every 30 seconds for testing purposes")
    print("Press Ctrl+C to stop\n")
    
    sync = PeriodicUserSync(sync_interval_minutes=0.5)  # 30 seconds
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
    
    # Ask user for sync mode
    print("\nChoose sync mode:")
    print("1. Production sync (every 15 minutes)")
    print("2. Demo sync (every 30 seconds)")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            # Production sync every 15 minutes
            sync = PeriodicUserSync(sync_interval_minutes=15)
            await sync.start_periodic_sync()
        elif choice == "2":
            # Demo sync every 30 seconds
            await demo_quick_sync()
        else:
            print("Invalid choice. Defaulting to demo mode...")
            await demo_quick_sync()
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
