"""
Azure Blob Storage example for msgraph-delta-query.

This example demonstrates:
1. Using Azure Blob Storage for delta link persistence in production
2. Automatic fallback to Azurite for local development
3. Authentication priority order for different environments
4. Persistent delta queries across runs
5. Handling both production and development scenarios
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage


# No helper function needed! Just use AzureBlobDeltaLinkStorage() directly


async def simple_example():
    """Simplest possible example - just use empty constructor!"""
    print("=== Simple Azure Blob Storage Example ===\n")
    
    print("💡 Using AzureBlobDeltaLinkStorage() with empty constructor...")
    print("   The storage class will automatically detect your environment!")
    
    # This is all you need! The class handles the rest automatically
    storage = AzureBlobDeltaLinkStorage()
    client = AsyncDeltaQueryClient(delta_link_storage=storage)
    
    try:
        print("\n🔄 Fetching users with automatic Azure Blob Storage...")
        
        users, delta_link, metadata = await client.delta_query_all(
            resource="users",
            select=["id", "displayName", "mail"],
            top=20
        )
        
        print(f"✅ Retrieved {len(users)} users in {metadata.duration_seconds:.2f}s")
        print(f"📊 {metadata.change_summary}")
        print(f"🔗 Delta link automatically stored in Azure Blob Storage")
        
        if len(users) > 0:
            print(f"\n👥 Sample users:")
            for i, user in enumerate(users[:3]):
                print(f"   {i+1}. {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
            if len(users) > 3:
                print(f"   ... and {len(users) - 3} more")
        else:
            print("📭 No changes (delta query working perfectly!)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure you have either:")
        print("   - AZURE_STORAGE_ACCOUNT_NAME set (production)")
        print("   - AZURE_STORAGE_CONNECTION_STRING set (development)")
        print("   - Azurite running locally (local dev)")
    finally:
        await storage.close()


async def persistent_users_sync():
    """Example showing persistent delta queries with Azure Blob Storage."""
    print("=== Persistent Users Sync with Azure Blob Storage ===\n")
    
    # Just use empty constructor - automatic detection!
    storage = AzureBlobDeltaLinkStorage()
    client = AsyncDeltaQueryClient(delta_link_storage=storage)
    
    try:
        print("🔄 Starting users sync (delta links will persist across runs)...")
        
        # Perform delta query - will use stored delta link if available
        users, delta_link, metadata = await client.delta_query_all(
            resource="users",
            select=["id", "displayName", "mail", "userPrincipalName", "accountEnabled"],
            top=100
        )
        
        print(f"✅ Users sync completed:")
        print(f"   Retrieved {len(users)} users in {metadata.duration_seconds:.2f}s")
        print(f"   📊 {metadata.change_summary}")
        print(f"   🔗 Delta link stored: {delta_link is not None}")
        
        # Show sync results
        if len(users) > 0:
            print(f"\n📋 Users from this sync:")
            for i, user in enumerate(users[:5]):
                removed_info = user.get('@removed')
                if removed_info:
                    print(f"   🗑️  {i+1}. [DELETED] {user.get('id', 'N/A')}")
                else:
                    enabled = user.get('accountEnabled', 'N/A')
                    status = "✅" if enabled else "❌" if enabled is False else "❓"
                    print(f"   {status} {i+1}. {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
            
            if len(users) > 5:
                print(f"   ... and {len(users) - 5} more users")
        else:
            print("📭 No changes detected since last sync (delta query working!)")
        
        # Show metadata about stored delta links
        try:
            stored_metadata = await storage.get_metadata("users")
            if stored_metadata:
                print(f"\n🗄️  Storage metadata:")
                print(f"   Last updated: {stored_metadata.get('last_updated', 'N/A')}")
                print(f"   Resource: {stored_metadata.get('resource', 'N/A')}")
        except Exception as e:
            print(f"ℹ️  Could not retrieve storage metadata: {e}")
            
    except Exception as e:
        print(f"❌ Error during users sync: {e}")
    finally:
        await storage.close()


async def persistent_applications_sync():
    """Example showing persistent application queries with streaming."""
    print("=== Persistent Applications Sync with Streaming ===\n")
    
    # Just use empty constructor - automatic detection!
    storage = AzureBlobDeltaLinkStorage()
    client = AsyncDeltaQueryClient(delta_link_storage=storage)
    
    try:
        print("🔄 Starting applications streaming sync...")
        
        batch_count = 0
        total_apps = 0
        
        async for apps, page_metadata in client.delta_query_stream(
            resource="applications", 
            select=["id", "displayName", "appId", "createdDateTime"],
            top=25
        ):
            batch_count += 1
            total_apps += len(apps)
            
            print(f"📦 Batch {batch_count}: {len(apps)} applications (Page {page_metadata.page})")
            print(f"   Changes: {page_metadata.page_new_or_updated} new/updated, "
                  f"{page_metadata.page_deleted} deleted, {page_metadata.page_changed} changed")
            
            # Process batch
            if apps:
                app = apps[0]
                removed_info = app.get('@removed')
                if removed_info:
                    print(f"   🗑️  Sample: [REMOVED] ID: {app.get('id', 'N/A')}")
                else:
                    print(f"   ✨ Sample: [NEW/UPDATED] {app.get('displayName', 'N/A')} (AppID: {app.get('appId', 'N/A')})")
            
            # Check if we have final delta link
            if page_metadata.delta_link:
                print(f"   🔗 Final delta link saved to Azure Blob Storage")
                break
            
            # Limit demo batches
            if batch_count >= 3:
                print("   🛑 Stopping after 3 batches for demo...")
                break
        
        print(f"\n📊 Streaming completed: {total_apps} applications in {batch_count} batches")
        
    except Exception as e:
        print(f"❌ Error during applications streaming: {e}")
    finally:
        await storage.close()


async def multi_resource_sync():
    """Example syncing multiple resources with shared blob storage."""
    print("=== Multi-Resource Sync with Shared Storage ===\n")
    
    # Just use empty constructor - automatic detection!
    storage = AzureBlobDeltaLinkStorage()
    client = AsyncDeltaQueryClient(delta_link_storage=storage)
    
    resources = [
        ("users", ["id", "displayName", "mail"]),
        ("applications", ["id", "displayName", "appId"]),
        ("groups", ["id", "displayName", "groupTypes"])
    ]
    
    try:
        for resource_name, select_fields in resources:
            print(f"🔄 Syncing {resource_name}...")
            
            try:
                objects, delta_link, metadata = await client.delta_query_all(
                    resource=resource_name,
                    select=select_fields,
                    top=50
                )
                
                print(f"   ✅ {len(objects)} {resource_name} synced in {metadata.duration_seconds:.2f}s")
                print(f"   📊 {metadata.change_summary}")
                
                if len(objects) == 0:
                    print(f"   📭 No changes for {resource_name} (delta query optimized!)")
                
            except Exception as e:
                print(f"   ❌ Failed to sync {resource_name}: {e}")
        
        print(f"\n🎉 Multi-resource sync completed!")
        
    except Exception as e:
        print(f"❌ Error during multi-resource sync: {e}")
    finally:
        await storage.close()


async def demonstrate_storage_persistence():
    """Demonstrate that delta links persist across different client instances."""
    print("=== Storage Persistence Demonstration ===\n")
    
    # First client instance
    print("🏁 First client instance - initial sync...")
    storage1 = AzureBlobDeltaLinkStorage()
    client1 = AsyncDeltaQueryClient(delta_link_storage=storage1)
    
    try:
        users1, _, metadata1 = await client1.delta_query_all(
            resource="users",
            select=["id", "displayName"],
            top=10
        )
        print(f"   First sync: {len(users1)} users, {metadata1.change_summary}")
    finally:
        await storage1.close()
    
    print("\n🔄 Second client instance - should use stored delta link...")
    
    # Second client instance (simulates app restart)
    storage2 = AzureBlobDeltaLinkStorage()
    client2 = AsyncDeltaQueryClient(delta_link_storage=storage2)
    
    try:
        users2, _, metadata2 = await client2.delta_query_all(
            resource="users",
            select=["id", "displayName"],
            top=10
        )
        print(f"   Second sync: {len(users2)} users, {metadata2.change_summary}")
        
        if len(users2) == 0:
            print("   🎯 Perfect! No changes detected - delta link was used successfully!")
        else:
            print(f"   📝 Found {len(users2)} changes since first sync")
            
    finally:
        await storage2.close()


async def main():
    """Run Azure Blob Storage examples."""
    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}\n")
    else:
        print(f"⚠️  No .env file found at {env_path}")
        print("Will use system environment variables and defaults\n")
    
    # Verify Microsoft Graph credentials
    required_vars = ['AZURE_CLIENT_ID', 'AZURE_TENANT_ID', 'AZURE_CLIENT_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required Microsoft Graph environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file or environment")
        return
    
    print(f"🔐 Microsoft Graph Config:")
    print(f"   Tenant: {os.getenv('AZURE_TENANT_ID')}")
    print(f"   Client: {os.getenv('AZURE_CLIENT_ID')}")
    
    # Show storage configuration
    print(f"\n🗄️  Storage Configuration:")
    storage_account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
    connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING') or os.getenv('AzureWebJobsStorage')
    
    if storage_account:
        print(f"   Production: Managed identity with '{storage_account}'")
    elif connection_string:
        if 'UseDevelopmentStorage=true' in connection_string or '127.0.0.1' in connection_string:
            print(f"   Development: Azurite emulator")
        else:
            print(f"   Development: Custom connection string")
    else:
        print(f"   Fallback: Default Azurite configuration")
        print(f"   Note: Start Azurite with: azurite --silent --location c:\\azurite")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60 + "\n")
    
    # Run examples - start with the simplest one
    await simple_example()
    print("\n" + "-"*60 + "\n")
    
    await persistent_users_sync()
    print("\n" + "-"*60 + "\n")
    
    await persistent_applications_sync()
    print("\n" + "-"*60 + "\n")
    
    await demonstrate_storage_persistence()
    print("\n" + "-"*60 + "\n")
    
    # Uncomment to try other examples:
    # await multi_resource_sync()
    
    print("🎉 All Azure Blob Storage examples completed!")
    print("\n💡 Key Features Demonstrated:")
    print("   ✨ Automatic environment detection with AzureBlobDeltaLinkStorage()")
    print("   🔄 Delta links persist in Azure Blob Storage between runs")
    print("   🏭 Production: Uses managed identity (set AZURE_STORAGE_ACCOUNT_NAME)")
    print("   🔧 Development: Uses connection string (set AZURE_STORAGE_CONNECTION_STRING)")
    print("   🧪 Local dev: Falls back to Azurite or local.settings.json")
    print("   📦 Run multiple times to see incremental delta queries in action!")
    print("\n🚀 No configuration needed - just use AzureBlobDeltaLinkStorage()!")


if __name__ == "__main__":
    asyncio.run(main())
