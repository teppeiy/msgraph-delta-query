"""
Simple Service Principals Sync Example

Demonstrates basic synchronization of service principals from Microsoft Graph.
Service principals represent applications and services in your tenant.

Perfect for:
- Security auditing
- Application inventory
- Monitoring service principal changes
- Compliance reporting
"""

import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient
from msgraph_delta_query.storage import LocalFileDeltaLinkStorage


async def main():
    """Sync service principals with local file storage."""
    print("=== Service Principals Sync Example ===")
    print("Syncing service principals from Microsoft Graph...")

    # Load .env
    load_dotenv()

    # Set up minimal logging
    logging.basicConfig(level=logging.WARNING)

    # Setup with deltalinks folder at project root (parent of examples directory)
    storage = LocalFileDeltaLinkStorage(folder="deltalinks")
    client = AsyncDeltaQueryClient(delta_link_storage=storage)

    try:
        # Sync service principals with relevant fields
        service_principals, delta_link, metadata = await client.delta_query_all(
            resource="servicePrincipals",
            select=[
                "id", 
                "displayName", 
                "appId", 
                "servicePrincipalType",
                "accountEnabled",
                "createdDateTime"
            ],
            top=100  # Process in smaller batches
        )

        # Display results using the comprehensive sync results method
        metadata.print_sync_results("Service Principals")

        # Show sample data
        if service_principals:
            print(f"\n📋 Sample Service Principals:")
            for i, sp in enumerate(service_principals[:3]):  # Show first 3
                print(f"   {i+1}. {sp.get('displayName', 'N/A')} ({sp.get('servicePrincipalType', 'N/A')})")
            
            if len(service_principals) > 3:
                print(f"   ... and {len(service_principals) - 3} more")

        print(f"\n🚀 Ready to use {len(service_principals)} service principals in your application!")
        
        return service_principals

    except Exception as e:
        print(f"❌ Error syncing service principals: {e}")
        raise
    finally:
        await client._internal_close()


if __name__ == "__main__":
    asyncio.run(main())
