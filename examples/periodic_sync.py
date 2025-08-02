"""
Periodic User Sync

This example shows how to run continuous user synchronization.
Choose your storage backend by running the appropriate version.

Perfect for:
- Background services
- Scheduled sync jobs
- Keeping data up-to-date automatically
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient


class UserSyncService:
    """Simple user sync service with graceful shutdown."""
    
    def __init__(self, interval_minutes: int = 15):
        """
        Initialize sync service.
        
        Args:
            interval_minutes: How often to sync (default: 15 minutes)
        """
        self.interval_minutes = interval_minutes
        self.running = True
        self.sync_count = 0
        
    async def sync_once(self) -> list:
        """Run a single user sync operation."""
        self.sync_count += 1
        print(f"\n=== Sync #{self.sync_count} ===")
        print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Create fresh client for each sync
        client = AsyncDeltaQueryClient()
        
        try:
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
            
            # Report results
            print(f"✓ Completed in {metadata.duration_seconds:.2f}s")
            print(f"✓ {metadata.change_summary}")
            
            sync_type = "Incremental" if metadata.used_stored_deltalink else "Full"
            print(f"✓ Type: {sync_type} sync")
            
            # Show changes if any
            if users:
                new_users = [u for u in users if not u.get("@removed")]
                deleted_users = [u for u in users if u.get("@removed")]
                
                if new_users:
                    print(f"📥 New/Updated: {len(new_users)} users")
                    for user in new_users[:3]:
                        name = user.get('displayName', 'N/A')
                        email = user.get('mail', user.get('userPrincipalName', 'N/A'))
                        print(f"   👤 {name} ({email})")
                    if len(new_users) > 3:
                        print(f"   ... and {len(new_users) - 3} more")
                
                if deleted_users:
                    print(f"🗑️  Deleted: {len(deleted_users)} users")
            else:
                print("📋 No changes detected")
            
            return users
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            return []
        finally:
            await client._internal_close()
    
    async def run_continuous(self):
        """Run periodic synchronization until stopped."""
        print(f"🚀 Starting periodic user sync (every {self.interval_minutes} minutes)")
        print(f"💾 Delta links stored in: deltalinks/users.json")
        print(f"🛑 Press Ctrl+C to stop\n")
        
        while self.running:
            try:
                # Run sync
                users = await self.sync_once()
                
                if self.running:  # Don't wait if we're shutting down
                    print(f"⏰ Next sync in {self.interval_minutes} minutes...")
                    
                    # Wait for next sync (with early exit if stopped)
                    for i in range(self.interval_minutes * 60):
                        if not self.running:
                            break
                        await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                print("\n🛑 Shutdown requested...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                if self.running:
                    print(f"⏰ Retrying in {self.interval_minutes} minutes...")
                    # Wait before retry
                    for i in range(self.interval_minutes * 60):
                        if not self.running:
                            break
                        await asyncio.sleep(1)
        
        print(f"✅ Sync service stopped after {self.sync_count} operations")
    
    def stop(self):
        """Stop the sync service."""
        self.running = False


async def main():
    """Run the periodic sync service."""
    # Load environment
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    # Minimal logging
    logging.basicConfig(level=logging.WARNING)

    # Create and start sync service
    # Sync every 5 minutes for demo (change to 15+ for production)
    service = UserSyncService(interval_minutes=5)
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}")
        service.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.run_continuous()
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt")
        service.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
