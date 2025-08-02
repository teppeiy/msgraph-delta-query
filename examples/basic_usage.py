"""
Basic example of using msgraph-delta-query to fetch users and applications from Microsoft Graph.

This example demonstrates:
1. Loading environment variables from .env file
2. Simple client instantiation
3. Performing delta queries on multiple resource types
4. Leveraging built-in models for change tracking and display
5. Automatic session management
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient


async def users_example():
    """Example of fetching users with delta query."""
    print("=== Users Delta Query Example ===")
    
    client = AsyncDeltaQueryClient()
    
    try:
        # Fetch users
        print("\n--- Fetching Users ---")
        users, user_delta_link, user_meta = await client.delta_query_all(
            resource="users",
            select=["id", "displayName", "mail", "userPrincipalName"],
            top=100
        )
        
        print(f"Retrieved {len(users)} users in {user_meta.duration_seconds:.2f}s")
        print(f"User delta link stored: {user_delta_link is not None}")
        
        # Show first few users
        for i, user in enumerate(users[:3]):
            print(f"  {i+1}. {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
        
        if len(users) > 3:
            print(f"  ... and {len(users) - 3} more users")
            
    except Exception as e:
        print(f"Error: {e}")


async def applications_example():
    """Example of fetching applications with delta query."""
    print("=== Applications Delta Query Example ===")
    
    client = AsyncDeltaQueryClient()
    
    try:
        # Fetch applications
        print("--- Fetching Applications ---")
        apps, app_delta_link, app_meta = await client.delta_query_all(
            resource="applications",
            select=["id", "displayName", "appId", "createdDateTime"],
            top=50
        )
        
        print(f"Retrieved {len(apps)} applications in {app_meta.duration_seconds:.2f}s")
        print(f"Application delta link stored: {app_delta_link is not None}")
        
        # Use the built-in change summary model for display
        print(f"📊 {app_meta.change_summary}")
        
        # Show sample applications (leverage the models for change detection)
        print("\nSample applications:")
        for i, app in enumerate(apps[:5]):  # Show more examples
            removed_info = app.get('@removed')
            if removed_info:
                reason = removed_info.get('reason', 'unknown')
                status = "DELETED" if reason == 'deleted' else "SOFT DELETED" if reason == 'changed' else f"REMOVED-{reason}"
                print(f"  {i+1}. [{status}] ID: {app.get('id', 'N/A')}")
            else:
                print(f"  {i+1}. [NEW/UPDATED] {app.get('displayName', 'N/A')} (AppID: {app.get('appId', 'N/A')})")
        
        if len(apps) > 5:
            print(f"  ... and {len(apps) - 5} more applications")
            
    except Exception as e:
        print(f"Error: {e}")


async def streaming_example():
    """Example of processing data in batches using streaming."""
    print("=== Streaming Example ===")
    
    client = AsyncDeltaQueryClient()
    
    try:
        print("--- Streaming Applications ---")
        batch_count = 0
        total_apps = 0
        
        async for apps, page_metadata in client.delta_query_stream(
            resource="applications",
            select=["id", "displayName", "appId"],
            top=25
        ):
            batch_count += 1
            total_apps += len(apps)
            
            print(f"Batch {batch_count}: {len(apps)} applications (Page {page_metadata.page})")
            print(f"  Page changes: {page_metadata.page_new_or_updated} new/updated, "
                  f"{page_metadata.page_deleted} deleted, {page_metadata.page_changed} changed")
            
            # Process batch - show first application as example
            if apps:
                app = apps[0]
                removed_info = app.get('@removed')
                if removed_info:
                    print(f"  Sample: [REMOVED] ID: {app.get('id', 'N/A')}")
                else:
                    print(f"  Sample: [NEW/UPDATED] {app.get('displayName', 'N/A')}")
            
            # Check if we have a delta link (end of pages)
            if page_metadata.delta_link:
                print(f"✅ Final delta link received for future incremental syncs")
                break
            
            # Limit demo to reasonable number of batches
            if batch_count >= 5:
                print("Breaking after 5 batches for demo purposes...")
                break
        
        print(f"📊 Processed {total_apps} applications in {batch_count} batches")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client._internal_close()


async def periodic_sync_example():
    """Example of syncing users every 15 minutes."""
    print("=== Periodic User Sync Example ===")
    print("This example will sync users every 15 minutes...")
    print("Press Ctrl+C to stop the sync\n")
    
    client = AsyncDeltaQueryClient()
    sync_count = 0
    
    try:
        while True:
            sync_count += 1
            print(f"🔄 Starting sync #{sync_count} at {asyncio.get_event_loop().time():.0f}s")
            
            try:
                # Sync users
                users, delta_link, user_meta = await client.delta_query_all(
                    resource="users",
                    select=["id", "displayName", "mail", "userPrincipalName", "accountEnabled"],
                    top=100
                )
                
                print(f"✅ Sync #{sync_count} completed:")
                print(f"   Retrieved {len(users)} users in {user_meta.duration_seconds:.2f}s")
                print(f"   📊 {user_meta.change_summary}")
                
                # Show any changes found
                if len(users) > 0:
                    print(f"   Sample users from this sync:")
                    for i, user in enumerate(users[:3]):
                        print(f"     {i+1}. {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
                    if len(users) > 3:
                        print(f"     ... and {len(users) - 3} more users")
                else:
                    print("   No changes detected since last sync")
                
            except Exception as e:
                print(f"❌ Sync #{sync_count} failed: {e}")
            
            print(f"⏰ Waiting 15 minutes before next sync... (Ctrl+C to stop)")
            
            # Wait 15 minutes (900 seconds)
            # For demo purposes, you might want to change this to a shorter interval
            await asyncio.sleep(900)  # 15 minutes = 900 seconds
            
    except KeyboardInterrupt:
        print(f"\n🛑 Periodic sync stopped by user after {sync_count} sync(s)")
    except Exception as e:
        print(f"❌ Periodic sync error: {e}")
    finally:
        await client._internal_close()
        print("✅ Client properly closed")


async def main():
    """Run the basic examples."""
    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️  No .env file found at {env_path}")
        print("Please create a .env file with your Azure credentials")
        return
    
    # Verify required environment variables are set
    required_vars = ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file")
        return
        
    print(f"🔐 Using Azure Tenant: {os.getenv('AZURE_TENANT_ID')}")
    print(f"🔐 Using Azure Client: {os.getenv('AZURE_CLIENT_ID')}")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main example
    await applications_example()
    
    # Uncomment to try other examples:
    # await users_example()
    # await streaming_example()
    # await periodic_sync_example()  # Warning: This runs continuously every 15 minutes


if __name__ == "__main__":
    asyncio.run(main())
