"""
Multi-Resource Sync Example

This example demonstrates syncing multiple Microsoft Graph resources
(users, applications, groups, service principals) using local file storage.

Perfect for:
- Comprehensive tenant monitoring
- Security auditing across all resources
- Building complete directory inventories
- Understanding the full scope of your tenant
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient


async def sync_resource(client, resource_name, display_name, select_fields, emoji):
    """Generic function to sync any supported resource."""
    print(f"\n{emoji} Syncing {display_name}...")
    
    try:
        items, delta_link, metadata = await client.delta_query_all(
            resource=resource_name,
            select=select_fields,
            top=500  # Reasonable page size
        )

        sync_type = "Incremental" if metadata.used_stored_deltalink else "Full"
        print(f"   ✓ Completed in {metadata.duration_seconds:.2f}s")
        print(f"   ✓ {metadata.change_summary}")
        print(f"   ✓ Sync type: {sync_type}")
        print(f"   💾 Delta link saved to: deltalinks/{resource_name}.json")
        
        return items, metadata
        
    except Exception as e:
        print(f"   ❌ Error syncing {display_name}: {e}")
        return [], None


async def sync_all_resources():
    """Sync all supported Microsoft Graph resources."""
    print("=== Multi-Resource Sync with Local Storage ===")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Resource configurations
    resources = [
        {
            "name": "users",
            "display": "Users",
            "emoji": "👥",
            "select": ["id", "displayName", "mail", "userPrincipalName", "accountEnabled"]
        },
        {
            "name": "applications", 
            "display": "Applications",
            "emoji": "📱",
            "select": ["id", "displayName", "appId", "createdDateTime", "publisherDomain"]
        },
        {
            "name": "groups",
            "display": "Groups", 
            "emoji": "👨‍👩‍👧‍👦",
            "select": ["id", "displayName", "description", "groupTypes", "mailEnabled"]
        },
        {
            "name": "servicePrincipals",
            "display": "Service Principals",
            "emoji": "🔧", 
            "select": ["id", "displayName", "appId", "servicePrincipalType", "accountEnabled"]
        }
    ]

    # Simple client setup - uses local file storage by default
    client = AsyncDeltaQueryClient()
    
    results = {}
    total_start_time = datetime.now(timezone.utc)

    try:
        for resource_config in resources:
            items, metadata = await sync_resource(
                client,
                resource_config["name"],
                resource_config["display"], 
                resource_config["select"],
                resource_config["emoji"]
            )
            
            results[resource_config["name"]] = {
                "items": items,
                "metadata": metadata,
                "display": resource_config["display"],
                "emoji": resource_config["emoji"]
            }

        # Summary
        total_duration = (datetime.now(timezone.utc) - total_start_time).total_seconds()
        print(f"\n{'='*50}")
        print(f"🎯 SYNC SUMMARY")
        print(f"{'='*50}")
        print(f"Total Duration: {total_duration:.2f}s")
        
        total_items = 0
        for resource_name, result in results.items():
            if result["metadata"]:
                count = len(result["items"])
                total_items += count
                sync_type = "Inc" if result["metadata"].used_stored_deltalink else "Full"
                print(f"{result['emoji']} {result['display']}: {count} items ({sync_type})")
        
        print(f"\n📊 Total items across all resources: {total_items}")
        print(f"💾 All delta links saved to: deltalinks/ directory")
        print(f"💡 Run again to see incremental sync in action!")
        
        return results

    except Exception as e:
        print(f"\n❌ Error during multi-resource sync: {e}")
        raise
    finally:
        # Clean up the client after all operations
        await client._internal_close()


async def main():
    """Load environment and run multi-resource sync."""
    # Load .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    # Set up minimal logging
    logging.basicConfig(level=logging.WARNING)

    # Run the sync
    results = await sync_all_resources()
    
    # Example: Use your data here
    print(f"\n🚀 Ready to use all synchronized resources in your application!")
    for resource_name, result in results.items():
        if result["items"]:
            print(f"   {result['emoji']} {len(result['items'])} {result['display']}")


if __name__ == "__main__":
    asyncio.run(main())
