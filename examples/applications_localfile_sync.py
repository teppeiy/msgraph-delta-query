"""
Simple Application Sync with Local Storage

This example shows how to sync Microsoft Graph applications using local file storage.
Delta links are automatically stored in a local 'deltalinks' folder.

Authentication Options (DefaultAzureCredential tries these in order):
1. Environment Variables: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID
2. Managed Identity (when running in Azure)
3. Azure CLI (az login)
4. Visual Studio / VS Code
5. Azure PowerShell

For local development:
- Copy .env.example to .env and fill in your Azure App Registration details
- Or use: az login
- Or set environment variables directly

Perfect for:
- Monitoring application changes
- Security auditing
- Application inventory management
- Development and testing
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient
from msgraph_delta_query.storage import LocalFileDeltaLinkStorage


async def sync_applications():
    """Sync applications using local file storage for delta links."""
    print("=== Application Sync with Local Storage ===")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

    # Setup with deltalinks folder
    client = AsyncDeltaQueryClient(delta_link_storage=LocalFileDeltaLinkStorage(folder="deltalinks"))

    try:
        print("Syncing applications...")
        
        # Get applications with delta query - automatically handles full vs incremental sync
        applications, delta_link, metadata = await client.delta_query_all(
            resource="applications",
            select=[
                "id", 
                "displayName", 
                "appId",
                "createdDateTime",
                "publisherDomain",
                "signInAudience"
            ],
                        top=5  # Very small page size to see pagination behavior
        )

        # Show results using the comprehensive sync results method
        metadata.print_sync_results("Applications")

        # Show sample applications
        if applications:
            print(f"\n📋 Applications ({len(applications)} total):")
            for i, app in enumerate(applications[:5]):
                if app.get("@removed"):
                    print(f"   🗑️  [DELETED] {app.get('id', 'N/A')}")
                else:
                    # The Graph SDK returns snake_case keys instead of camelCase
                    display_name = app.get('display_name') or app.get('displayName', 'N/A')
                    app_id = app.get('app_id') or app.get('appId', 'N/A')
                    publisher = app.get('publisher_domain') or app.get('publisherDomain', 'N/A')
                    audience = app.get('sign_in_audience') or app.get('signInAudience', 'N/A')
                    created = app.get('created_date_time') or app.get('createdDateTime', 'N/A')
                    
                    print(f"   📱 {display_name}")
                    print(f"      App ID: {app_id}")
                    print(f"      Publisher: {publisher}")
                    print(f"      Audience: {audience}")
                    print(f"      Created: {created}")
                    print()
            
            if len(applications) > 5:
                print(f"   ... and {len(applications) - 5} more applications")
        else:
            print("\n📋 No changes since last sync")

        print(f"\n💾 Delta link saved to: deltalinks/applications.json")
        print(f"💡 Run again to see incremental sync in action!")
        
        return applications

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await client._internal_close()


async def main():
    """Load environment and run sync."""
    # Load .env
    load_dotenv()
    # Set up minimal logging
    logging.basicConfig(level=logging.INFO)

    # Run the sync
    applications = await sync_applications()
    
    # Use your data here
    print(f"\n🎯 Ready to use {len(applications)} applications in your application!")


if __name__ == "__main__":
    asyncio.run(main())
