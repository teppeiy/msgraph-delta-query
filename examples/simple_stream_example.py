#!/usr/bin/env python3
"""
Simple Delta Query Stream Example

A straightforward example showing how to use delta_query_stream to process
Microsoft Graph objects in real-time as they are received.
"""

import asyncio
import logging
from typing import cast, List
from msgraph_delta_query import AsyncDeltaQueryClient

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, skipping .env file loading")

# Import Graph SDK models for proper type casting
from msgraph.generated.models.user import User

# Set up basic logging - use WARNING level to suppress verbose storage messages
logging.basicConfig(level=logging.WARNING)


async def simple_stream_example():
    """
    Simple example: Stream users and display basic info as they arrive
    """
    print("🚀 Starting simple delta query stream...")
    
    # Create client (uses DefaultAzureCredential automatically)
    async with AsyncDeltaQueryClient() as client:
        
        # Stream users with basic properties
        async for objects, page_meta in client.delta_query_stream(
            resource="users",
            select=["displayName", "userPrincipalName", "createdDateTime"],
            top=10  # Small pages for demo
        ):
            print(f"\n📄 Page {page_meta.page} - Received {len(objects)} objects:")
            print("-" * 50)
            
            # Filter to only User objects before casting (Microsoft Graph may return mixed types)
            user_objects = [obj for obj in objects if getattr(obj, 'odata_type', '') == '#microsoft.graph.user']
            
            # If we get fewer users than total objects, show what types we're getting
            if len(user_objects) < len(objects):
                object_types = {}
                for obj in objects:
                    odata_type = getattr(obj, 'odata_type', 'Unknown')
                    object_types[odata_type] = object_types.get(odata_type, 0) + 1
                
                print("📊 Object types in this page:")
                for obj_type, count in object_types.items():
                    print(f"   • {obj_type}: {count}")
            
            # Cast the filtered user objects to List[User] for proper type safety
            users = cast(List[User], user_objects)
            
            if len(user_objects) < len(objects):
                print(f"📊 Found {len(users)} user objects out of {len(objects)} total objects")
            else:
                print(f"📊 Processing {len(users)} users")
            
            # Display each user as it's processed (show only first 5 per page)
            for i, user in enumerate(users, 1):
                # Only show first 5 users per page
                if i > 5:
                    if len(users) > 5:
                        print(f"  ... and {len(users) - 5} more users")
                    break
                    
                # Now we have proper User objects with type safety
                name = user.display_name or 'Unknown'
                upn = user.user_principal_name or 'No UPN'
                
                # Check if user is deleted
                if user.additional_data and "@removed" in user.additional_data:
                    print(f"  🗑️  [{i:2}] DELETED: {name}")
                    continue

                print(f"  👤 [{i:2}] {name} ({upn}) - created at {user.created_date_time}")

                # Simulate some processing time
                await asyncio.sleep(0.2)
            
            # Show progress
            print(f"\n📊 Cumulative stats:")
            print(f"   • New/Updated: {page_meta.total_new_or_updated}")
            print(f"   • Deleted: {page_meta.total_deleted}")
            print(f"   • Changed: {page_meta.total_changed}")
            
            # Check if more pages are coming
            if page_meta.has_next_page:
                print("⏳ Fetching next page...\n")
            else:
                print("✅ All pages processed!")
                break
    
    print("🎉 Stream completed!")


if __name__ == "__main__":
    asyncio.run(simple_stream_example())
