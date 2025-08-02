#!/usr/bin/env python3
"""
Example showing how to use the AsyncDeltaQueryClient with SDK objects.

This demonstrates three ways to get data from Microsoft Graph:
1. As dictionaries (default, backward compatible)
2. As strongly-typed SDK objects (new feature)
3. Using the typed convenience method
"""

import asyncio
from typing import List, Union

# Import the SDK types for type hints
from msgraph.generated.models.user import User
from msgraph.generated.models.application import Application
from msgraph.generated.models.group import Group
from msgraph.generated.models.service_principal import ServicePrincipal

from msgraph_delta_query.client import AsyncDeltaQueryClient


async def example_dictionary_usage():
    """Example 1: Using dictionaries (default behavior)."""
    print("=== Example 1: Dictionary Results ===")
    
    client = AsyncDeltaQueryClient()
    
    # This returns List[Dict[str, Any]]
    users, delta_link, metadata = await client.delta_query_all(
        resource="users",
        select=["id", "displayName", "mail", "userPrincipalName"],
        top=10
    )
    
    print(f"Retrieved {len(users)} users as dictionaries")
    
    # Work with dictionary data
    for user in users[:3]:  # Show first 3
        print(f"  User: {user.get('displayName')} ({user.get('mail')})")
    
    return users, delta_link, metadata


async def example_sdk_objects_usage():
    """Example 2: Using strongly-typed SDK objects."""
    print("\n=== Example 2: SDK Object Results ===")
    
    client = AsyncDeltaQueryClient(return_sdk_objects=True)
    
    # This returns List[User] (strongly typed)
    users, delta_link, metadata = await client.delta_query_all(
        resource="users",
        select=["id", "displayName", "mail", "userPrincipalName"],
        top=10
    )
    
    print(f"Retrieved {len(users)} users as SDK objects")
    
    # Work with strongly-typed objects
    for user in users[:3]:  # Show first 3
        # IDE autocomplete and type checking work here!
        display_name = getattr(user, 'display_name', 'Unknown')
        mail = getattr(user, 'mail', 'No email')
        print(f"  User: {display_name} ({mail})")
    
    return users, delta_link, metadata


async def example_typed_convenience_method():
    """Example 3: Using the typed convenience method."""
    print("\n=== Example 3: Typed Convenience Method ===")
    
    client = AsyncDeltaQueryClient()  # Can use default client
    
    # This method temporarily switches to SDK objects for this call
    users, delta_link, metadata = await client.delta_query_all_typed(
        resource="users",
        select=["id", "displayName", "mail", "userPrincipalName"],
        top=10
    )
    
    print(f"Retrieved {len(users)} users using typed method")
    
    # Work with strongly-typed objects
    for user in users[:3]:  # Show first 3
        display_name = getattr(user, 'display_name', 'Unknown')
        mail = getattr(user, 'mail', 'No email')
        print(f"  User: {display_name} ({mail})")
    
    return users, delta_link, metadata


async def example_different_resource_types():
    """Example 4: Different resource types with SDK objects."""
    print("\n=== Example 4: Different Resource Types ===")
    
    client = AsyncDeltaQueryClient(return_sdk_objects=True)
    
    # Applications -> List[Application]
    print("Fetching applications...")
    apps, _, _ = await client.delta_query_all(
        resource="applications",
        select=["id", "displayName", "appId"],
        top=5
    )
    print(f"Retrieved {len(apps)} applications")
    for app in apps[:2]:
        display_name = getattr(app, 'display_name', 'Unknown')
        app_id = getattr(app, 'app_id', 'No app ID')
        print(f"  App: {display_name} (AppId: {app_id})")
    
    # Groups -> List[Group] 
    print("\nFetching groups...")
    groups, _, _ = await client.delta_query_all(
        resource="groups",
        select=["id", "displayName", "mail"],
        top=5
    )
    print(f"Retrieved {len(groups)} groups")
    for group in groups[:2]:
        display_name = getattr(group, 'display_name', 'Unknown')
        mail = getattr(group, 'mail', 'No email')
        print(f"  Group: {display_name} ({mail})")


def show_type_information():
    """Show what types are returned for different configurations."""
    print("\n=== Type Information ===")
    print("Configuration options:")
    print("1. AsyncDeltaQueryClient() -> returns List[Dict[str, Any]]")
    print("2. AsyncDeltaQueryClient(return_sdk_objects=True) -> returns List[SDK_Object]")
    print("3. client.delta_query_all_typed() -> returns List[SDK_Object]")
    print("\nSDK Object Types by Resource:")
    print("- users -> List[msgraph.generated.models.user.User]")
    print("- applications -> List[msgraph.generated.models.application.Application]")
    print("- groups -> List[msgraph.generated.models.group.Group]") 
    print("- serviceprincipals -> List[msgraph.generated.models.service_principal.ServicePrincipal]")


async def main():
    """Run all examples."""
    show_type_information()
    
    try:
        # Run examples (these will fail in test environment but show the patterns)
        await example_dictionary_usage()
        await example_sdk_objects_usage()
        await example_typed_convenience_method()
        await example_different_resource_types()
        
    except Exception as e:
        print(f"\nNote: Examples failed due to authentication/environment: {e}")
        print("This is expected in a test environment without proper Azure credentials.")
        print("The code structure and type information above shows how to use the features.")


if __name__ == "__main__":
    asyncio.run(main())
