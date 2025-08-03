#!/usr/bin/env python3
"""
Filtered Users Only Example

Shows how to use delta_query_stream to get ONLY users, filtering out
other directory objects like applications and service principals.
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


async def filtered_users_example():
    """
    Example: Stream only users, filtering out applications and other objects
    """
    print("🚀 Starting filtered users delta query stream...")
    
    # Create client (uses DefaultAzureCredential automatically)
    async with AsyncDeltaQueryClient() as client:
        
        user_count = 0
        page_count = 0
        
        # Stream users with basic properties
        async for objects, page_meta in client.delta_query_stream(
            resource="users",
            select=["displayName", "userPrincipalName", "mail"],
            top=50  # Larger pages for efficiency
        ):
            page_count += 1
            
            print(f"\n📄 Page {page_meta.page} - Received {len(objects)} objects:")
            print("-" * 50)
            
            # Filter to only User objects before casting
            user_objects = [obj for obj in objects if getattr(obj, 'odata_type', '') == '#microsoft.graph.user']
            
            if not user_objects:
                print(f"⏭️  No users in this page (contains other object types)")
                continue
                
            # Cast the filtered user objects to List[User] for proper type safety
            users = cast(List[User], user_objects)
            user_count += len(users)
            
            print(f"👥 Found {len(users)} users in this page:")
            
            # Display each user
            for i, user in enumerate(users, 1):
                name = user.display_name or 'Unknown'
                email = user.user_principal_name or 'No email'
                
                # Check if user is deleted
                if user.additional_data and "@removed" in user.additional_data:
                    print(f"  🗑️  [{i:2}] DELETED: {name}")
                    continue
                
                print(f"  👤 [{i:2}] {name}")
                print(f"      📧 {email}")
            
            print(f"\n📊 Running totals:")
            print(f"   • Pages processed: {page_count}")
            print(f"   • Users found: {user_count}")
            print(f"   • Total objects: {page_meta.total_new_or_updated}")
            
            # Stop after processing a reasonable number of pages for demo
            if page_count >= 5:
                print("\n🛑 Stopping after 5 pages for demo purposes")
                break
                
            # Check if more pages are coming
            if page_meta.has_next_page:
                print("⏳ Fetching next page...")
            else:
                print("✅ All pages processed!")
                break
    
    print(f"\n🎉 Demo completed! Found {user_count} users across {page_count} pages")


if __name__ == "__main__":
    asyncio.run(filtered_users_example())
