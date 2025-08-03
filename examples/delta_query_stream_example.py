#!/usr/bin/env python3
"""
Example: Using delta_query_stream for real-time processing

This example demonstrates how to use the delta_query_stream method to process
Microsoft Graph objects as they are received, providing real-time feedback
and the ability to handle large datasets without loading everything into memory.
"""

import asyncio
import logging
from datetime import datetime
from azure.identity.aio import DefaultAzureCredential
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
from msgraph.generated.models.application import Application
from msgraph.generated.models.service_principal import ServicePrincipal


# Configure logging to suppress verbose storage messages
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def stream_users_example():
    """
    Example: Stream users and display each object as it's received
    """
    print("🚀 Starting users delta query stream example...")
    print("=" * 60)
    
    # Initialize the client
    credential = DefaultAzureCredential()
    client = AsyncDeltaQueryClient(credential=credential)
    
    try:
        # Track statistics
        total_objects = 0
        total_pages = 0
        start_time = datetime.now()
        
        print("📡 Starting delta query stream for users...")
        print("🔄 Processing objects as they arrive...\n")
        
        # Stream users with selected properties
        async for objects, page_meta in client.delta_query_stream(
            resource="users",
            select=["id", "displayName", "userPrincipalName", "mail", "jobTitle"],
            top=50  # Smaller page size for more frequent updates
        ):
            total_pages = page_meta.page
            page_objects = len(objects)
            total_objects += page_objects
            
            # Display page header
            print(f"📄 Page {page_meta.page} - Received {page_objects} objects")
            print(f"   📊 Page Stats: {page_meta.page_new_or_updated} new/updated, "
                  f"{page_meta.page_deleted} deleted, {page_meta.page_changed} changed")
            
            # Process and display each object
            for i, user_obj in enumerate(objects, 1):
                # Cast to User model for proper type safety and IDE support
                user = User() if not isinstance(user_obj, User) else user_obj
                if not isinstance(user_obj, User):
                    # If it's a dict, populate the User object
                    if hasattr(user_obj, '__dict__'):
                        for key, value in user_obj.__dict__.items():
                            if hasattr(user, key):
                                setattr(user, key, value)
                    user.additional_data = getattr(user_obj, 'additional_data', {})
                
                # Now access properties with proper typing
                display_name = user.display_name or 'Unknown'
                upn = user.user_principal_name or 'No UPN'
                mail = user.mail or 'No email'
                job_title = user.job_title or 'No title'
                user_id = user.id or 'No ID'
                
                # Check if this is a deleted object
                is_deleted = False
                if user.additional_data and "@removed" in user.additional_data:
                    removed_info = user.additional_data["@removed"]
                    if removed_info:
                        is_deleted = True
                        print(f"   🗑️  [{i:2}] DELETED: {display_name} ({upn})")
                        continue
                
                # Display active user
                print(f"   👤 [{i:2}] {display_name}")
                print(f"       📧 {mail}")
                print(f"       🏢 {job_title}")
                print(f"       🆔 {user_id}")
                
                # Add a small delay to simulate processing time
                await asyncio.sleep(0.1)
            
            # Display cumulative statistics
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\n   📈 Cumulative: {total_objects} objects processed in {elapsed:.1f}s")
            print(f"   ⚡ Rate: {total_objects/elapsed:.1f} objects/second")
            
            # Show delta link status
            if page_meta.delta_link:
                print("   💾 Delta link saved for incremental sync")
            
            # Show next page indicator
            if page_meta.has_next_page:
                print("   ➡️  More pages available, continuing...\n")
            else:
                print("   ✅ All pages processed!\n")
                break
        
        # Final summary
        total_time = (datetime.now() - start_time).total_seconds()
        print("=" * 60)
        print("📊 FINAL SUMMARY")
        print("=" * 60)
        print(f"📄 Total pages processed: {total_pages}")
        print(f"👥 Total objects received: {total_objects}")
        print(f"⏱️  Total time: {total_time:.1f} seconds")
        print(f"⚡ Average rate: {total_objects/total_time:.1f} objects/second")
        print("✅ Stream processing completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during streaming: {e}")
        raise
    finally:
        # Always clean up resources
        await client.close()
        await credential.close()
        print("🧹 Resources cleaned up")


async def stream_applications_with_filter_example():
    """
    Example: Stream applications with a filter and show real-time processing
    """
    print("\n🚀 Starting applications delta query stream with filter...")
    print("=" * 60)
    
    # Initialize the client
    credential = DefaultAzureCredential()
    client = AsyncDeltaQueryClient(credential=credential)
    
    try:
        # Track statistics
        processed_count = 0
        start_time = datetime.now()
        
        print("📡 Streaming applications with display name filter...")
        print("🔍 Filter: startswith(displayName,'Microsoft')")
        print("🔄 Processing objects as they arrive...\n")
        
        # Stream applications with filter
        async for objects, page_meta in client.delta_query_stream(
            resource="applications",
            select=["id", "displayName", "appId", "createdDateTime"],
            filter="startswith(displayName,'Microsoft')",
            top=25
        ):
            page_count = len(objects)
            processed_count += page_count
            
            print(f"📄 Page {page_meta.page} - {page_count} applications received")
            
            # Process each application
            for i, app_obj in enumerate(objects, 1):
                # Cast to Application model for proper type safety
                app = Application() if not isinstance(app_obj, Application) else app_obj
                if not isinstance(app_obj, Application):
                    # If it's a dict, populate the Application object
                    if hasattr(app_obj, '__dict__'):
                        for key, value in app_obj.__dict__.items():
                            if hasattr(app, key):
                                setattr(app, key, value)
                    app.additional_data = getattr(app_obj, 'additional_data', {})
                
                # Now access properties with proper typing
                display_name = app.display_name or 'Unknown'
                app_id = app.app_id or 'No App ID'
                created = app.created_date_time.isoformat() if app.created_date_time else 'Unknown'
                object_id = app.id or 'No ID'
                
                print(f"   🏢 [{i:2}] {display_name}")
                print(f"       🆔 App ID: {app_id}")
                print(f"       📅 Created: {created}")
                print(f"       🔗 Object ID: {object_id}")
                
                # Simulate some processing
                await asyncio.sleep(0.05)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\n   📊 Progress: {processed_count} apps processed in {elapsed:.1f}s")
            
            if not page_meta.has_next_page:
                print("   ✅ All filtered applications processed!\n")
                break
            else:
                print("   ➡️  Fetching next page...\n")
        
        print("📊 Applications stream completed!")
        
    except Exception as e:
        print(f"❌ Error during application streaming: {e}")
        raise
    finally:
        await client.close()
        await credential.close()


async def stream_with_context_manager_example():
    """
    Example: Using delta_query_stream with async context manager for automatic cleanup
    """
    print("\n🚀 Starting stream with context manager example...")
    print("=" * 60)
    
    # Using async context manager ensures automatic cleanup
    async with AsyncDeltaQueryClient() as client:
        print("📡 Streaming service principals...")
        
        object_count = 0
        
        async for objects, page_meta in client.delta_query_stream(
            resource="serviceprincipals", 
            select=["id", "displayName", "servicePrincipalType"],
            top=20
        ):
            page_size = len(objects)
            object_count += page_size
            
            print(f"📄 Page {page_meta.page}: {page_size} service principals")
            
            # Show first few objects from each page
            for i, sp_obj in enumerate(objects[:3], 1):  # Show only first 3
                # Cast to ServicePrincipal model for proper type safety
                sp = ServicePrincipal() if not isinstance(sp_obj, ServicePrincipal) else sp_obj
                if not isinstance(sp_obj, ServicePrincipal):
                    # If it's a dict, populate the ServicePrincipal object
                    if hasattr(sp_obj, '__dict__'):
                        for key, value in sp_obj.__dict__.items():
                            if hasattr(sp, key):
                                setattr(sp, key, value)
                    sp.additional_data = getattr(sp_obj, 'additional_data', {})
                
                # Now access properties with proper typing
                display_name = sp.display_name or 'Unknown'
                sp_type = sp.service_principal_type or 'Unknown'
                
                print(f"   🔧 [{i}] {display_name} ({sp_type})")
            
            if len(objects) > 3:
                print(f"   ... and {len(objects) - 3} more objects")
            
            print(f"   📊 Total processed: {object_count}")
            
            # Process only first 2 pages for demo
            if page_meta.page >= 2:
                print("   🛑 Demo limit reached (2 pages)")
                break
            
            if page_meta.has_next_page:
                print("   ➡️  Getting next page...\n")
            else:
                print("   ✅ All pages processed!\n")
    
    print("🧹 Context manager automatically cleaned up resources!")


async def main():
    """
    Main function to run all stream examples
    """
    print("🌟 Microsoft Graph Delta Query Stream Examples")
    print("=" * 60)
    print("This example demonstrates real-time processing of Microsoft Graph objects")
    print("using the delta_query_stream method.\n")
    
    try:
        # Run examples
        await stream_users_example()
        await stream_applications_with_filter_example()
        await stream_with_context_manager_example()
        
        print("\n🎉 All streaming examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        logging.exception("Full error details:")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())
