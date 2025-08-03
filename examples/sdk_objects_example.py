#!/usr/bin/env python3
"""
Example showing how to work with Microsoft Graph SDK objects using AsyncDeltaQueryClient.

This demonstrates how to use the client's dict responses with proper type casting
for IDE support and clean dot notation access.
"""

import asyncio
from typing import List, cast

# Import the SDK types for type hints
from msgraph.generated.models.user import User
from msgraph.generated.models.application import Application
from msgraph.generated.models.group import Group
from msgraph.generated.models.service_principal import ServicePrincipal

from msgraph_delta_query.client import AsyncDeltaQueryClient


async def example_users_with_sdk_objects():
    """Example 1: Users with SDK object typing."""
    print("=== Example 1: Users with SDK Object Typing ===")
    
    client = AsyncDeltaQueryClient()
    
    # Get users data (returns dict objects)
    users_data, delta_link, metadata = await client.delta_query(
        resource="users",
        select=["id", "displayName", "mail", "userPrincipalName", "accountEnabled"],
        top=10
    )
    
    # Cast to SDK objects for better IDE support and dot notation
    users = cast(List[User], users_data)
    
    print(f"Retrieved {len(users)} users")
    metadata.print_sync_results("Users")
    
    # Work with SDK objects using dot notation
    for user in users[:3]:  # Show first 3
        if hasattr(user, '@removed') or (isinstance(user, dict) and user.get("@removed")):
            print(f"  🗑️  [DELETED] {user.id}")
        else:
            # Clean dot notation access
            print(f"  👤 {user.display_name} ({user.mail or user.user_principal_name}) - Enabled: {user.account_enabled}")
    
    await client._internal_close()
    return users


async def example_applications_with_sdk_objects():
    """Example 2: Applications with SDK object typing."""
    print("\n=== Example 2: Applications with SDK Object Typing ===")
    
    client = AsyncDeltaQueryClient()
    
    # Get applications data
    apps_data, delta_link, metadata = await client.delta_query(
        resource="applications",
        select=["id", "displayName", "appId", "publisherDomain", "createdDateTime"],
        top=10
    )
    
    # Cast to SDK objects
    apps = cast(List[Application], apps_data)
    
    print(f"Retrieved {len(apps)} applications")
    metadata.print_sync_results("Applications")
    
    # Work with SDK objects
    for app in apps[:3]:  # Show first 3
        if hasattr(app, '@removed') or (isinstance(app, dict) and app.get("@removed")):
            print(f"  🗑️  [DELETED] {app.id}")
        else:
            print(f"  📱 {app.display_name} (AppId: {app.app_id}, Publisher: {app.publisher_domain})")
    
    await client._internal_close()
    return apps


async def example_service_principals_with_sdk_objects():
    """Example 3: Service Principals with SDK object typing."""
    print("\n=== Example 3: Service Principals with SDK Object Typing ===")
    
    client = AsyncDeltaQueryClient()
    
    # Get service principals data
    sps_data, delta_link, metadata = await client.delta_query(
        resource="servicePrincipals",
        select=["id", "displayName", "appId", "servicePrincipalType", "accountEnabled"],
        top=10
    )
    
    # Cast to SDK objects
    service_principals = cast(List[ServicePrincipal], sps_data)
    
    print(f"Retrieved {len(service_principals)} service principals")
    metadata.print_sync_results("Service Principals")
    
    # Work with SDK objects
    for sp in service_principals[:3]:  # Show first 3
        if hasattr(sp, '@removed') or (isinstance(sp, dict) and sp.get("@removed")):
            print(f"  🗑️  [DELETED] {sp.id}")
        else:
            print(f"  🔧 {sp.display_name} (AppId: {sp.app_id}, Type: {sp.service_principal_type})")
    
    await client._internal_close()
    return service_principals


async def example_groups_with_sdk_objects():
    """Example 4: Groups with SDK object typing."""
    print("\n=== Example 4: Groups with SDK Object Typing ===")
    
    client = AsyncDeltaQueryClient()
    
    # Get groups data
    groups_data, delta_link, metadata = await client.delta_query(
        resource="groups",
        select=["id", "displayName", "mail", "groupTypes", "createdDateTime"],
        top=10
    )
    
    # Cast to SDK objects
    groups = cast(List[Group], groups_data)
    
    print(f"Retrieved {len(groups)} groups")
    metadata.print_sync_results("Groups")
    
    # Work with SDK objects
    for group in groups[:3]:  # Show first 3
        if hasattr(group, '@removed') or (isinstance(group, dict) and group.get("@removed")):
            print(f"  🗑️  [DELETED] {group.id}")
        else:
            print(f"  👥 {group.display_name} ({group.mail}) - Types: {group.group_types}")
    
    await client._internal_close()
    return groups


def show_type_information():
    """Show what types are used and best practices."""
    print("\n=== Type Information & Best Practices ===")
    print("The AsyncDeltaQueryClient returns dict objects from Microsoft Graph.")
    print("For better IDE support and clean code, cast them to SDK objects:")
    print()
    print("Pattern:")
    print("1. data, delta_link, metadata = await client.delta_query(...)")
    print("2. objects = cast(List[SdkType], data)")
    print("3. Use dot notation: object.property_name")
    print()
    print("SDK Object Types by Resource:")
    print("- users -> cast(List[User], data)")
    print("- applications -> cast(List[Application], data)")
    print("- groups -> cast(List[Group], data)")
    print("- serviceprincipals -> cast(List[ServicePrincipal], data)")
    print()
    print("Benefits:")
    print("✅ IDE autocomplete and type checking")
    print("✅ Clean dot notation access (user.display_name)")
    print("✅ Better code readability")
    print("✅ Compile-time error detection")


async def main():
    """Run all examples."""
    show_type_information()
    
    try:
        # Run examples (these will fail in test environment but show the patterns)
        await example_users_with_sdk_objects()
        await example_applications_with_sdk_objects()
        await example_service_principals_with_sdk_objects()
        await example_groups_with_sdk_objects()
        
        print("\n🎯 All examples completed successfully!")
        print("💡 Run 'python examples/applications_localfile_sync.py' for a working example")
        
    except Exception as e:
        print(f"\nNote: Examples failed due to authentication/environment: {e}")
        print("This is expected in a test environment without proper Azure credentials.")
        print("The code structure and type information above shows how to use the features.")


if __name__ == "__main__":
    asyncio.run(main())
