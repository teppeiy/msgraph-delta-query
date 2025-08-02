"""
Simple Periodic User Sync Example

A minimal example that runs user synchronization every X minutes.
Each sync creates a new client, runs the sync, and closes the client.

Features:
- Simple periodic execution
- Automatic incremental sync (uses existing deltalink if found)
- Clean client lifecycle management
- Configurable interval
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage
from msgraph_delta_query.storage.azure_blob import AzureBlobDeltaLinkStorage


async def run_user_sync():
    """Run a single user sync operation."""
    print(f"🔄 Starting sync at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Create client for this sync
    storage = AzureBlobDeltaLinkStorage()
    client = AsyncDeltaQueryClient(delta_link_storage=storage)
    
    try:
        # Run delta query - automatically uses incremental sync if deltalink exists
        users, delta_link, metadata = await client.delta_query_all(
            resource="users",
            select=["id", "displayName", "mail", "userPrincipalName", "accountEnabled", "createdDateTime"],
            top=1000
        )
        
        # Report results
        print(f"✅ Sync completed in {metadata.duration_seconds:.2f}s")
        print(f"   📊 {metadata.change_summary}")
        print(f"   📈 Processed {metadata.pages_fetched} pages, {len(users)} total users")
        
        if len(users) > 0:
            print(f"   Sample users:")
            for i, user in enumerate(users[:3]):
                status = "✅" if user.get('accountEnabled', True) else "❌"
                created = user.get('createdDateTime', 'N/A')
                # Format the created date if it exists
                if created and created != 'N/A':
                    try:
                        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        created = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass  # Keep original if parsing fails
                print(f"     {i+1}. {status} {user.get('displayName', 'N/A')} (created: {created})")
            if len(users) > 3:
                print(f"     ... and {len(users) - 3} more users")
        else:
            print("   No changes detected since last sync")
            
        return True
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False
        
    finally:
        # Always close the client
        await client._internal_close()


async def simple_periodic_sync(interval_minutes: float = 15):
    """Run periodic sync every interval_minutes."""
    print("=== Simple Periodic User Sync ===")
    print(f"⏱️  Sync interval: {interval_minutes} minutes")
    print(f"📅 Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("🛑 Press Ctrl+C to stop\n")
    
    sync_count = 0
    interval_seconds = interval_minutes * 60
    
    try:
        while True:
            sync_count += 1
            print(f"--- Sync #{sync_count} ---")
            
            # Run sync
            success = await run_user_sync()
            
            if not success:
                print("⚠️  Sync failed, but will retry at next interval")
            
            print(f"⏰ Next sync in {interval_minutes} minutes... (Ctrl+C to stop)")
            print("-" * 50)
            
            # Wait for next interval
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
                
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped after {sync_count} syncs")


async def main():
    """Main function."""
    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️  No .env file found at {env_path}")
        return
    
    # Verify required environment variables
    required_vars = ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 For authentication, set up Azure credentials using one of:")
        print("   - Environment variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)")
        print("   - Azure CLI: az login")
        print("   - VS Code Azure Account extension")
        return
    
    # Configure logging (reduce Azure SDK noise)
    logging.basicConfig(level=logging.WARNING)
    
    # Ask for interval
    print("\nChoose sync interval:")
    print("1. Demo (every 1 minute)")
    print("2. Production (every 15 minutes)")
    print("3. Custom interval")
    
    try:
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == "1":
            await simple_periodic_sync(1)
        elif choice == "2":
            await simple_periodic_sync(15)
        elif choice == "3":
            try:
                minutes = float(input("Enter interval in minutes: "))
                await simple_periodic_sync(minutes)
            except ValueError:
                print("Invalid number, using 15 minutes")
                await simple_periodic_sync(15)
        else:
            print("Invalid choice, using 1 minute demo")
            await simple_periodic_sync(1)
            
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    asyncio.run(main())
