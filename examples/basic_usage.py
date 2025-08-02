"""
Basic example of using msgraph-delta-query to fetch users from Microsoft Graph.

This example demonstrates:
1. Simple client instantiation
2. Performing a delta query
3. Automatic session management
"""

import asyncio
import logging
from msgraph_delta_query import AsyncDeltaQueryClient


async def basic_example():
    """Basic example of fetching users with delta query."""
    print("=== Basic Delta Query Example ===")
    
    # Simple instantiation - everything handled internally
    client = AsyncDeltaQueryClient()
    
    try:
        # Just use it - sessions are created and cleaned up automatically
        users, delta_link, meta = await client.delta_query_all(
            resource="users",
            select=["id", "displayName", "mail"],
            top=100
        )
        
        print(f"Retrieved {len(users)} users in {meta['duration_seconds']:.2f}s")
        print(f"Delta link stored: {delta_link is not None}")
        
        # Show first few users
        for i, user in enumerate(users[:3]):
            print(f"  {i+1}. {user.get('displayName', 'N/A')} - {user.get('mail', 'N/A')}")
        
        if len(users) > 3:
            print(f"  ... and {len(users) - 3} more users")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # No need to close anything - handled automatically


async def batch_example():
    """Example of processing users in batches."""
    print("\n=== Batch Processing Example ===")
    
    client = AsyncDeltaQueryClient()
    
    try:
        batch_count = 0
        total_users = 0
        
        async for batch in client.delta_query_batches(
            resource="users",
            select=["id", "displayName", "mail"],
            batch_size=50
        ):
            users, delta_link, metadata = batch
            batch_count += 1
            total_users += len(users)
            
            print(f"Batch {batch_count}: {len(users)} users")
            
            # Process your batch here
            # For example, save to database, send notifications, etc.
            
            # Break after a few batches for demo purposes
            if batch_count >= 3:
                break
        
        print(f"Processed {total_users} users in {batch_count} batches")
        
    except Exception as e:
        print(f"Error: {e}")


async def main():
    """Run all examples."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    await basic_example()
    await batch_example()


if __name__ == "__main__":
    asyncio.run(main())
