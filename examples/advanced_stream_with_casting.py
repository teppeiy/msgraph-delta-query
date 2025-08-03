#!/usr/bin/env python3
"""
Advanced Delta Query Stream Example with Proper SDK Model Casting

This example demonstrates how to properly cast Microsoft Graph objects to their
corresponding SDK models for better type safety, IDE support, and maintainability.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, cast
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
from msgraph.generated.models.group import Group

# Set up logging to suppress verbose storage messages
logging.basicConfig(level=logging.WARNING)


async def stream_users_with_proper_casting():
    """
    Stream users with proper SDK model casting for type safety
    """
    print("🚀 Streaming Users with Proper SDK Model Casting")
    print("=" * 60)
    
    async with AsyncDeltaQueryClient() as client:
        user_count = 0
        
        async for objects, page_meta in client.delta_query_stream(
            resource="users",
            select=["id", "displayName", "userPrincipalName", "mail", "jobTitle", "department"],
            top=100  # Larger batch size for better performance
        ):
            # Filter objects to only include actual User objects  
            user_objects = []
            for obj in objects:
                # Check if object has User-specific attributes before casting
                if hasattr(obj, 'user_principal_name') or (hasattr(obj, '@odata.type') and 'user' in str(getattr(obj, '@odata.type', '')).lower()):
                    user_objects.append(obj)
                elif hasattr(obj, 'display_name') and not hasattr(obj, 'app_id'):  # User has display_name but not app_id
                    user_objects.append(obj)
            
            # Cast filtered objects for type hint purposes - objects are User SDK objects
            users = cast(List[User], user_objects)
            
            print(f"\n📄 Page {page_meta.page} - Processing {len(users)} users")
            print("-" * 40)
            
            for i, user in enumerate(users, 1):
                user_count += 1
                
                # Check if user is deleted (proper additional_data access)
                if hasattr(user, 'additional_data') and user.additional_data and "@removed" in user.additional_data:
                    removed_reason = user.additional_data["@removed"].get("reason", "unknown")
                    print(f"  🗑️  [{i:2}] DELETED ({removed_reason}): {user.display_name}")
                    continue
                
                # Display user with proper type-safe access
                print(f"  👤 [{i:2}] {user.display_name or 'No Name'}")
                print(f"      📧 Email: {user.mail or user.user_principal_name or 'No email'}")
                print(f"      🏢 Department: {user.department or 'Not specified'}")
                print(f"      💼 Job Title: {user.job_title or 'Not specified'}")
                print(f"      🆔 ID: {user.id}")
                
                # Demonstrate type safety - IDE will show autocomplete for these properties
                if user.created_date_time:
                    print(f"      📅 Created: {user.created_date_time.strftime('%Y-%m-%d')}")
                
                # Only add delay every 10 users for better performance
                if i % 10 == 0:
                    await asyncio.sleep(0.1)
            
            print(f"\n📊 Total users processed so far: {user_count}")
            
            if not page_meta.has_next_page:
                break
        
        print(f"\n✅ Completed! Total users processed: {user_count}")


async def stream_applications_with_proper_casting():
    """
    Stream applications with proper SDK model casting
    """
    print("\n🚀 Streaming Applications with Proper SDK Model Casting")
    print("=" * 60)
    
    async with AsyncDeltaQueryClient() as client:
        app_count = 0
        
        async for objects, page_meta in client.delta_query_stream(
            resource="applications",
            select=["id", "displayName", "appId", "createdDateTime", "publisherDomain"],
            top=50  # Larger batch size for better performance
        ):
            # Filter objects to only include actual Application objects
            app_objects = []
            for obj in objects:
                # Check if object has Application-specific attributes
                if hasattr(obj, 'app_id') or (hasattr(obj, '@odata.type') and 'application' in str(getattr(obj, '@odata.type', '')).lower()):
                    app_objects.append(obj)
                elif hasattr(obj, 'display_name') and not hasattr(obj, 'user_principal_name'):  # App has display_name but not user_principal_name
                    app_objects.append(obj)
            
            # Cast filtered objects for type hint purposes - objects are Application SDK objects
            applications = cast(List[Application], app_objects)
            
            print(f"\n📄 Page {page_meta.page} - Processing {len(applications)} applications")
            print("-" * 40)
            
            for i, app in enumerate(applications, 1):
                app_count += 1
                
                # Check if application is deleted
                if hasattr(app, 'additional_data') and app.additional_data and "@removed" in app.additional_data:
                    print(f"  🗑️  [{i:2}] DELETED: {app.display_name}")
                    continue
                
                # Display application with proper type-safe access
                print(f"  🏢 [{i:2}] {app.display_name or 'No Name'}")
                print(f"      🆔 App ID: {app.app_id or 'No App ID'}")
                print(f"      🌐 Publisher: {app.publisher_domain or 'Not specified'}")
                print(f"      🔗 Object ID: {app.id}")
                
                # Demonstrate type safety with datetime
                if app.created_date_time:
                    created_str = app.created_date_time.strftime('%Y-%m-%d %H:%M')
                    print(f"      📅 Created: {created_str}")
                
                # Only add delay every 5 apps for better performance
                if i % 5 == 0:
                    await asyncio.sleep(0.05)
            
            print(f"\n📊 Total applications processed so far: {app_count}")
            
            # Demo: stop after 2 pages
            if page_meta.page >= 2:
                print("🛑 Demo limit reached (2 pages)")
                break
        
        print(f"\n✅ Completed! Total applications processed: {app_count}")


async def stream_service_principals_with_proper_casting():
    """
    Stream service principals with proper SDK model casting
    """
    print("\n🚀 Streaming Service Principals with Proper SDK Model Casting")
    print("=" * 60)
    
    async with AsyncDeltaQueryClient() as client:
        sp_count = 0
        
        async for objects, page_meta in client.delta_query_stream(
            resource="servicePrincipals",
            select=["id", "displayName", "servicePrincipalType", "appId", "accountEnabled"],
            top=50  # Larger batch size for better performance
        ):
            # Filter objects to only include actual ServicePrincipal objects
            sp_objects = []
            for obj in objects:
                # Check if object has ServicePrincipal-specific attributes
                if hasattr(obj, 'service_principal_type') or hasattr(obj, 'account_enabled') or (hasattr(obj, '@odata.type') and 'serviceprincipal' in str(getattr(obj, '@odata.type', '')).lower()):
                    sp_objects.append(obj)
                elif hasattr(obj, 'app_id') and hasattr(obj, 'display_name'):  # Has both app_id and display_name (SP characteristics)
                    sp_objects.append(obj)
            
            # Cast filtered objects for type hint purposes - objects are ServicePrincipal SDK objects
            service_principals = cast(List[ServicePrincipal], sp_objects)
            
            print(f"\n📄 Page {page_meta.page} - Processing {len(service_principals)} service principals")
            print("-" * 40)
            
            for i, sp in enumerate(service_principals, 1):
                sp_count += 1
                
                # Check if service principal is deleted
                if hasattr(sp, 'additional_data') and sp.additional_data and "@removed" in sp.additional_data:
                    print(f"  🗑️  [{i:2}] DELETED: {sp.display_name}")
                    continue
                
                # Display service principal with proper type-safe access
                status = "🟢 Enabled" if sp.account_enabled else "🔴 Disabled"
                print(f"  🔧 [{i:2}] {sp.display_name or 'No Name'} {status}")
                print(f"      📂 Type: {sp.service_principal_type or 'Unknown'}")
                print(f"      🆔 App ID: {sp.app_id or 'No App ID'}")
                print(f"      🔗 Object ID: {sp.id}")
                
                # Only add delay every 10 SPs for better performance
                if i % 10 == 0:
                    await asyncio.sleep(0.05)
            
            print(f"\n📊 Total service principals processed so far: {sp_count}")
            
            # Demo: stop after 1 page
            if page_meta.page >= 1:
                print("🛑 Demo limit reached (1 page)")
                break
        
        print(f"\n✅ Completed! Total service principals processed: {sp_count}")


async def demonstrate_type_safety_benefits():
    """
    Demonstrate the benefits of proper type casting for IDE support and type checking
    """
    print("\n🎯 Demonstrating Type Safety Benefits")
    print("=" * 60)
    
    async with AsyncDeltaQueryClient() as client:
        print("📝 Getting a few users to demonstrate type safety...")
        
        async for objects, page_meta in client.delta_query_stream(
            resource="users",
            select=["id", "displayName", "userPrincipalName", "createdDateTime"],
            top=5  # Just a few for demo
        ):
            # Cast for type hint purposes - objects are User SDK objects
            users = cast(List[User], objects)
            
            for user in users[:2]:  # Just first 2 users
                print(f"\n👤 Analyzing user: {user.display_name}")
                
                # Type-safe property access (IDE will show autocomplete)
                print(f"   • ID type: {type(user.id).__name__}")
                print(f"   • Display name type: {type(user.display_name).__name__}")
                print(f"   • UPN type: {type(user.user_principal_name).__name__}")
                
                # Type-safe datetime handling
                if user.created_date_time:
                    print(f"   • Created datetime type: {type(user.created_date_time).__name__}")
                    print(f"   • Created (formatted): {user.created_date_time.strftime('%B %d, %Y')}")
                    print(f"   • Days since creation: {(datetime.now() - user.created_date_time.replace(tzinfo=None)).days}")
                
                # Additional data access (for @removed objects)
                if hasattr(user, 'additional_data') and user.additional_data:
                    print(f"   • Additional data keys: {list(user.additional_data.keys())}")
                else:
                    print("   • No additional data")
                
                print("   ✅ All properties accessed with full type safety!")
            
            break  # Just process first page for demo
    
    print("\n🎉 Type safety demonstration completed!")


async def main():
    """
    Run all streaming examples with proper SDK model casting
    """
    print("🌟 Advanced Delta Query Stream Examples")
    print("🔧 Featuring Proper Microsoft Graph SDK Model Casting")
    print("=" * 70)
    
    try:
        await stream_users_with_proper_casting()
        await stream_applications_with_proper_casting()
        await stream_service_principals_with_proper_casting()
        await demonstrate_type_safety_benefits()
        
        print("\n🎉 All advanced streaming examples completed successfully!")
        print("💡 Benefits achieved:")
        print("   ✅ Full type safety and IDE autocomplete support")
        print("   ✅ High-performance batch processing with larger page sizes")
        print("   ✅ Efficient type casting using typing.cast() for better performance")
        print("   ✅ Proper handling of datetime objects")
        print("   ✅ Consistent additional_data access for deleted objects")
        print("   ✅ Better maintainability and debugging")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        logging.exception("Full error details:")


if __name__ == "__main__":
    asyncio.run(main())
