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


async def main():
    """Sync service principals with local file storage."""
    print("=== Service Principals Sync Example ===")
    print("Syncing service principals from Microsoft Graph...")

    # Load .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    # Set up minimal logging
    logging.basicConfig(level=logging.WARNING)

    # Simple client setup - uses local file storage by default
    client = AsyncDeltaQueryClient()

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

        # Display results
        sync_type = "Incremental" if metadata.used_stored_deltalink else "Full"
        print(f"✓ Sync completed in {metadata.duration_seconds:.2f} seconds")
        print(f"✓ {metadata.change_summary}")
        print(f"✓ Sync type: {sync_type}")
        print(f"💾 Delta link saved for future incremental syncs")

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
