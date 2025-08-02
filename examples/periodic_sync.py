"""
Periodic Microsoft Graph Sync

This example demonstrates continuous synchronization of Microsoft Graph objects
with configurable intervals and object types. Uses Azure Blob Storage by default
for delta link persistence with automatic fallback to local storage.

Features:
- Configurable sync interval (default: 1 minute)
- Configurable object type (default: applications)
- Azure Blob Storage with Azurite fallback
- Automatic incremental sync using delta links
- Graceful shutdown handling
- Clean client lifecycle management

Perfect for:
- Production background services
- Scheduled sync jobs
- Keeping data up-to-date automatically
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage


class GraphSyncService:
    """Configurable Microsoft Graph sync service with graceful shutdown."""
    
    def __init__(self, 
                 resource_type: str = "applications",
                 interval_minutes: int = 1,
                 use_azure_storage: bool = True):
        """
        Initialize sync service.
        
        Args:
            resource_type: Type of Graph object to sync (applications, users, servicePrincipals, etc.)
            interval_minutes: How often to sync (default: 1 minute)
            use_azure_storage: Use Azure Blob Storage (default: True)
        """
        self.resource_type = resource_type
        self.interval_minutes = interval_minutes
        self.use_azure_storage = use_azure_storage
        self.running = True
        self.sync_count = 0
        
        # Configure select fields based on resource type
        self.select_fields = self._get_select_fields(resource_type)
        
    def _get_select_fields(self, resource_type: str) -> list:
        """Get appropriate select fields for the resource type."""
        field_configs = {
            "applications": [
                "id", "displayName", "appId", "publisherDomain", 
                "createdDateTime", "signInAudience"
            ],
            "users": [
                "id", "displayName", "mail", "userPrincipalName", 
                "accountEnabled", "lastSignInDateTime"
            ],
            "servicePrincipals": [
                "id", "displayName", "appId", "servicePrincipalType",
                "accountEnabled", "createdDateTime"
            ],
            "groups": [
                "id", "displayName", "mail", "groupTypes",
                "createdDateTime", "membershipRule"
            ]
        }
        
        return field_configs.get(resource_type, [
            "id", "displayName", "createdDateTime"  # Default fields
        ])
    
    def _format_object_display(self, obj: dict) -> str:
        """Format object for display based on type."""
        if obj.get("@removed"):
            return f"[DELETED] {obj.get('id', 'N/A')}"
        
        # Handle field name mapping (snake_case vs camelCase)
        display_name = obj.get('display_name') or obj.get('displayName', 'N/A')
        
        if self.resource_type == "applications":
            app_id = obj.get('app_id') or obj.get('appId', 'N/A')
            publisher = obj.get('publisher_domain') or obj.get('publisherDomain', 'N/A')
            return f"📱 {display_name} (AppId: {app_id[:8]}..., Publisher: {publisher})"
        
        elif self.resource_type == "users":
            email = obj.get('mail') or obj.get('user_principal_name') or obj.get('userPrincipalName', 'N/A')
            enabled = obj.get('account_enabled') or obj.get('accountEnabled', 'N/A')
            return f"👤 {display_name} ({email}, Enabled: {enabled})"
        
        elif self.resource_type == "servicePrincipals":
            app_id = obj.get('app_id') or obj.get('appId', 'N/A')
            sp_type = obj.get('service_principal_type') or obj.get('servicePrincipalType', 'N/A')
            return f"🔧 {display_name} (AppId: {app_id[:8]}..., Type: {sp_type})"
        
        elif self.resource_type == "groups":
            email = obj.get('mail', 'N/A')
            group_types = obj.get('group_types') or obj.get('groupTypes', [])
            return f"👥 {display_name} ({email}, Types: {group_types})"
        
        else:
            # Generic display for other resource types
            obj_id = obj.get('id', 'N/A')
            return f"📄 {display_name} (ID: {obj_id[:8]}...)"
    
    async def sync_once(self) -> list:
        """Run a single sync operation."""
        self.sync_count += 1
        print(f"\n=== Sync #{self.sync_count} ===")
        print(f"Resource: {self.resource_type}")
        print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Create fresh client for each sync
        storage = None
        if self.use_azure_storage:
            storage = AzureBlobDeltaLinkStorage(container_name="msgraph-deltalinks")
            client = AsyncDeltaQueryClient(delta_link_storage=storage)
        else:
            client = AsyncDeltaQueryClient()
        
        try:
            objects, delta_link, metadata = await client.delta_query_all(
                resource=self.resource_type,
                select=self.select_fields,
                top=1000
            )
            
            # Report results
            print(f"✓ Completed in {metadata.duration_seconds:.2f}s")
            print(f"✓ {metadata.change_summary}")
            
            sync_type = "Incremental" if metadata.used_stored_deltalink else "Full"
            print(f"✓ Type: {sync_type} sync")
            
            # Show changes if any
            if objects:
                new_objects = [obj for obj in objects if not obj.get("@removed")]
                deleted_objects = [obj for obj in objects if obj.get("@removed")]
                
                if new_objects:
                    print(f"📥 New/Updated: {len(new_objects)} {self.resource_type}")
                    for obj in new_objects[:3]:
                        print(f"   {self._format_object_display(obj)}")
                    if len(new_objects) > 3:
                        print(f"   ... and {len(new_objects) - 3} more")
                
                if deleted_objects:
                    print(f"🗑️  Deleted: {len(deleted_objects)} {self.resource_type}")
                    for obj in deleted_objects[:3]:
                        print(f"   {self._format_object_display(obj)}")
                    if len(deleted_objects) > 3:
                        print(f"   ... and {len(deleted_objects) - 3} more")
            else:
                print("📋 No changes detected")
            
            return objects
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            return []
        finally:
            await client._internal_close()
            if storage is not None:
                await storage.close()
    
    async def run_continuous(self):
        """Run periodic synchronization until stopped."""
        storage_info = "Azure Blob Storage (Azurite fallback)" if self.use_azure_storage else "Local File Storage"
        print(f"🚀 Starting periodic {self.resource_type} sync")
        print(f"⏱️  Interval: {self.interval_minutes} minutes")
        print(f"💾 Storage: {storage_info}")
        if self.use_azure_storage:
            print(f"☁️  Container: msgraph-deltalinks")
        else:
            print(f"📁 Local path: deltalinks/{self.resource_type}.json")
        print(f"🛑 Press Ctrl+C to stop\n")
        
        while self.running:
            try:
                # Run sync
                objects = await self.sync_once()
                
                if self.running:  # Don't wait if we're shutting down
                    print(f"⏰ Next sync in {self.interval_minutes} minutes...")
                    
                    # Wait for next sync (with early exit if stopped)
                    for i in range(self.interval_minutes * 60):
                        if not self.running:
                            break
                        await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                print("\n🛑 Shutdown requested...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                if self.running:
                    print(f"⏰ Retrying in {self.interval_minutes} minutes...")
                    # Wait before retry
                    for i in range(self.interval_minutes * 60):
                        if not self.running:
                            break
                        await asyncio.sleep(1)
        
        print(f"✅ Sync service stopped after {self.sync_count} operations")
    
    def stop(self):
        """Stop the sync service."""
        self.running = False


async def main(resource_type: str = "applications", 
               interval_minutes: int = 15,
               use_local_storage: bool = False):
    """
    Run the periodic sync service.
    
    Args:
        resource_type: Type of Graph object to sync (applications, users, servicePrincipals, groups)
        interval_minutes: How often to sync in minutes
        use_local_storage: If True, use local storage instead of Azure Blob Storage
    """
    # Load environment
    load_dotenv()
    print("ℹ️  No .env file found, using system environment variables" if not Path(".env").exists() else "✅ Loaded .env file")
    print("💡 Create a .env file in the root directory with AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID")
    print("   or use Azure CLI (az login) or managed identity in Azure\n")

    # Minimal logging
    logging.basicConfig(level=logging.WARNING)

    # Create and start sync service
    service = GraphSyncService(
        resource_type=resource_type,
        interval_minutes=interval_minutes,
        use_azure_storage=not use_local_storage
    )
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}")
        service.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.run_continuous()
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt")
        service.stop()


if __name__ == "__main__":
    import argparse
    
    # Command line argument parsing
    parser = argparse.ArgumentParser(description="Periodic Microsoft Graph Sync")
    parser.add_argument("--resource", "-r", default="applications",
                       choices=["applications", "users", "servicePrincipals", "groups"],
                       help="Type of Graph object to sync (default: applications)")
    parser.add_argument("--interval", "-i", type=int, default=1,
                       help="Sync interval in minutes (default: 1)")
    parser.add_argument("--local-storage", "-l", action="store_true",
                       help="Use local file storage instead of Azure Blob Storage")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(main(
            resource_type=args.resource,
            interval_minutes=args.interval,
            use_local_storage=args.local_storage
        ))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
