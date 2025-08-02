"""
Basic example of using msgraph-delta-query to fetch users and applications from Microsoft Graph.

This example demonstrates:
1. Loading environment variables from .env file
2. Simple client instantiation
3. Performing delta queries on multiple resource types (users and applications)
4. Automatic session management
5. Batch processing with streaming
6. Separate functions for different resource types and processing methods
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
    
    # Simple instantiation - everything handled internally
    client = AsyncDeltaQueryClient()
    
    try:
        # Fetch users
        print("\n--- Fetching Users ---")
        users, user_delta_link, user_meta = await client.delta_query_all(
            resource="users",
            select=["id", "displayName", "mail", "userPrincipalName"],
            top=100
        )
        
        print(f"Retrieved {len(users)} users in {user_meta['duration_seconds']:.2f}s")
        print(f"User delta link stored: {user_delta_link is not None}")
        
        # Show first few users
        for i, user in enumerate(users[:3]):
            print(f"  {i+1}. {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
        
        if len(users) > 3:
            print(f"  ... and {len(users) - 3} more users")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # No need to close anything - handled automatically


async def applications_example():
    """Example of fetching applications with delta query."""
    print("\n=== Applications Delta Query Example ===")
    
    # Simple instantiation - everything handled internally
    client = AsyncDeltaQueryClient()
    
    try:
        # Fetch applications
        print("\n--- Fetching Applications ---")
        apps, app_delta_link, app_meta = await client.delta_query_all(
            resource="applications",
            select=["id", "displayName", "appId", "createdDateTime"],
            top=50
        )
        
        print(f"Retrieved {len(apps)} applications in {app_meta['duration_seconds']:.2f}s")
        print(f"Application delta link stored: {app_delta_link is not None}")
        
        # Show first few applications
        for i, app in enumerate(apps[:3]):
            print(f"  {i+1}. {app.get('displayName', 'N/A')} - AppID: {app.get('appId', 'N/A')}")
        
        if len(apps) > 3:
            print(f"  ... and {len(apps) - 3} more applications")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # No need to close anything - handled automatically


async def users_streaming_example():
    """Example of processing users in batches using streaming."""
    print("\n=== Users Streaming Example ===")
    
    client = AsyncDeltaQueryClient()
    
    try:
        # Process users in batches
        print("\n--- Streaming Users ---")
        batch_count = 0
        total_users = 0
        
        async for users, page_metadata in client.delta_query_stream(
            resource="users",
            select=["id", "displayName", "mail"],
            top=50  # This controls the page size from Microsoft Graph
        ):
            batch_count += 1
            total_users += len(users)
            
            print(f"User Batch {batch_count}: {len(users)} users (Page {page_metadata.get('page', 'N/A')})")
            
            # Process your batch here
            for user in users[:2]:  # Show first 2 users from each batch
                print(f"  - {user.get('displayName', 'N/A')} ({user.get('mail', 'N/A')})")
            
            if len(users) > 2:
                print(f"  ... and {len(users) - 2} more users in this batch")
            
            # Break after a few batches for demo purposes
            if batch_count >= 2:
                print("Breaking after 2 user batches for demo purposes...")
                break
        
        print(f"Processed {total_users} users in {batch_count} batches")
        
    except Exception as e:
        print(f"Error: {e}")


async def applications_streaming_example():
    """Example of processing applications in batches using streaming."""
    print("\n=== Applications Streaming Example ===")
    
    client = AsyncDeltaQueryClient()
    
    try:
        # Process applications in batches
        print("\n--- Streaming Applications ---")
        batch_count = 0
        total_apps = 0
        
        async for apps, page_metadata in client.delta_query_stream(
            resource="applications",
            select=["id", "displayName", "appId"],
            top=25  # Smaller batch size for applications
        ):
            batch_count += 1
            total_apps += len(apps)
            
            print(f"App Batch {batch_count}: {len(apps)} applications (Page {page_metadata.get('page', 'N/A')})")
            print(f"  Page metadata: has_next_page={page_metadata.get('has_next_page')}, delta_link_present={bool(page_metadata.get('delta_link'))}")
            
            # Process your batch here
            for app in apps[:2]:  # Show first 2 applications from each batch
                print(f"  - {app.get('displayName', 'N/A')} (AppID: {app.get('appId', 'N/A')})")
            
            if len(apps) > 2:
                print(f"  ... and {len(apps) - 2} more applications in this batch")
            
            # Check if this is the last page and we got a delta link
            if page_metadata.get('delta_link'):
                print(f"✅ Delta link received: {page_metadata['delta_link'][:50]}...")
                print(f"✅ Delta link saved for incremental sync!")
                break
            
            # Break after a reasonable number of batches for demo purposes
            if batch_count >= 10:
                print("Breaking after 10 application batches for demo purposes...")
                break
        
        print(f"Processed {total_apps} applications in {batch_count} batches")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Properly close the client to avoid cleanup warnings
        await client._internal_close()
        print("✅ Client properly closed")


async def main():
    """Run all examples."""
    # Load environment variables from .env file
    # Look for .env file in the parent directory (project root)
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
    
    # Set our library logging to DEBUG to see delta link operations
    logging.getLogger('msgraph_delta_query').setLevel(logging.DEBUG)
    
    # Run all examples
    # await users_example()
    # await applications_example()
    # await users_streaming_example()
    await applications_streaming_example()


if __name__ == "__main__":
    asyncio.run(main())
