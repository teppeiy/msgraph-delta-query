"""
Microsoft Graph Delta Query Client using the official Microsoft Graph SDK.

This module provides an enhanced client for performing delta queries against Microsoft Graph
using the official Python SDK, offering improved reliability, type safety, and maintainability.
"""

import logging
import json
import urllib.parse
import asyncio
import weakref
from typing import Optional, Any, Dict, List, Tuple, AsyncGenerator, Union
from azure.identity.aio import DefaultAzureCredential
from datetime import datetime, timezone

# Microsoft Graph SDK imports
from msgraph.graph_service_client import GraphServiceClient

from .storage import DeltaLinkStorage, LocalFileDeltaLinkStorage
from .models import ChangeSummary, ResourceParams, PageMetadata, DeltaQueryMetadata


# Global registry to track all client instances for cleanup
_client_registry: weakref.WeakSet = weakref.WeakSet()


async def _cleanup_all_clients() -> None:
    """Cleanup function for all clients - called during event loop shutdown."""
    for client in list(_client_registry):
        try:
            await client._internal_close()
        except Exception as e:
            logging.warning(f"Error cleaning up client: {e}")


class AsyncDeltaQueryClient:
    """
    Enhanced AsyncDeltaQueryClient using Microsoft Graph SDK for Python.
    
    This client provides delta query capabilities with automatic authentication,
    rate limiting, retry logic, and comprehensive error handling through the
    official Microsoft Graph SDK.
    """

    SUPPORTED_RESOURCES = {
        "users": "users",
        "applications": "applications", 
        "groups": "groups",
        "serviceprincipals": "servicePrincipals",
        "servicePrincipals": "servicePrincipals"
    }

    def __init__(
        self,
        credential: Optional[DefaultAzureCredential] = None,
        delta_link_storage: Optional[DeltaLinkStorage] = None,
        scopes: Optional[List[str]] = None,
    ):
        """
        Initialize the Microsoft Graph SDK-based delta query client.
        
        Args:
            credential: Azure credential for authentication
            delta_link_storage: Storage backend for delta links
            scopes: OAuth scopes for Graph API access
        """
        self.credential = credential
        self.delta_link_storage = delta_link_storage or LocalFileDeltaLinkStorage()
        self.scopes = scopes or ["https://graph.microsoft.com/.default"]
        self._graph_client: Optional[GraphServiceClient] = None
        self._credential_created = False
        self._initialized = False
        self._closed = False

        # Log the delta link storage source being used
        storage_type = type(self.delta_link_storage).__name__
        storage_info = f"Using {storage_type} for delta link storage"

        # Add specific details for different storage types
        if storage_type == "AzureBlobDeltaLinkStorage":
            container_name = getattr(
                self.delta_link_storage, "container_name", "deltalinks"
            )
            account_name = "auto-detecting..."
            account_url = getattr(self.delta_link_storage, "_account_url", None)
            connection_string = getattr(
                self.delta_link_storage, "_connection_string", None
            )

            if account_url:
                try:
                    account_name = account_url.split("//")[1].split(".")[0]
                except (IndexError, AttributeError):
                    account_name = "from account URL"
            elif connection_string:
                try:
                    if "AccountName=" in connection_string:
                        account_name = connection_string.split("AccountName=")[1].split(
                            ";"
                        )[0]
                except (IndexError, AttributeError):
                    account_name = "from connection string"

            storage_info += f" (Account: {account_name}, Container: {container_name})"
        elif storage_type == "LocalFileDeltaLinkStorage":
            deltalinks_dir = getattr(
                self.delta_link_storage, "deltalinks_dir", "deltalinks"
            )
            storage_info += f" (Directory: {deltalinks_dir})"

        logging.info(storage_info)

        # Register this instance for cleanup
        _client_registry.add(self)

        # Set up automatic cleanup when event loop shuts down
        try:
            loop = asyncio.get_running_loop()
            if not hasattr(loop, "_delta_client_cleanup_added"):
                if hasattr(loop, "add_signal_handler"):
                    try:
                        import signal
                        for sig in [signal.SIGTERM, signal.SIGINT]:
                            try:
                                loop.add_signal_handler(
                                    sig,
                                    lambda: asyncio.create_task(_cleanup_all_clients()),
                                )
                            except (NotImplementedError, OSError):
                                pass
                    except ImportError:
                        pass
                setattr(loop, "_delta_client_cleanup_added", True)
        except RuntimeError:
            pass

    async def _initialize(self) -> None:
        """Initialize the Graph client and authentication."""
        if self._initialized and not self._closed:
            return
        
        # Reset state if we were previously closed
        if self._closed:
            self._closed = False
            self._initialized = False

        # Create credential if not provided
        if self.credential is None:
            self.credential = DefaultAzureCredential()
            self._credential_created = True
            logging.debug("Created DefaultAzureCredential")

        # Create Graph client with the credential
        self._graph_client = GraphServiceClient(
            credentials=self.credential,
            scopes=self.scopes
        )
        
        logging.debug("Created GraphServiceClient with Microsoft Graph SDK")
        self._initialized = True

    async def _internal_close(self) -> None:
        """Internal close method - can be called multiple times safely."""
        if self._closed:
            return

        self._closed = True

        # Close Graph client if it exists
        if self._graph_client:
            # The SDK handles its own cleanup
            self._graph_client = None
            logging.debug("Closed GraphServiceClient")

        # Close credential if we created it
        if self.credential and self._credential_created:
            try:
                await self.credential.close()
                logging.debug("Closed DefaultAzureCredential")
            except Exception as e:
                logging.warning(f"Error closing credential: {e}")

        self.credential = None
        self._credential_created = False
        self._initialized = False

    def _get_delta_request_builder(self, resource: str):
        """Get the appropriate delta request builder for the resource type."""
        if not self._graph_client:
            raise ValueError("Graph client not initialized")
            
        resource_lower = resource.lower()
        
        if resource_lower == "users":
            return self._graph_client.users.delta
        elif resource_lower == "applications":
            return self._graph_client.applications.delta
        elif resource_lower == "groups":
            return self._graph_client.groups.delta
        elif resource_lower in ("serviceprincipals", "servicePrincipals"):
            return self._graph_client.service_principals.delta
        else:
            raise ValueError(
                f"Unsupported resource type: {resource}. "
                f"Supported types: {list(self.SUPPORTED_RESOURCES.keys())}"
            )

    def _build_query_parameters(
        self,
        select: Optional[List[str]] = None,
        filter: Optional[str] = None,
        top: Optional[int] = None,
        deltatoken: Optional[str] = None,
        deltatoken_latest: bool = False,
        skiptoken: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build query parameters for the delta request."""
        params = {}
        
        if select:
            params["select"] = select
        if filter:
            params["filter"] = filter
        if top:
            params["top"] = top
        if deltatoken_latest:
            params["deltatoken"] = "latest"
        elif deltatoken:
            params["deltatoken"] = deltatoken
        if skiptoken:
            params["skiptoken"] = skiptoken
            
        return params

    def _convert_sdk_object_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert SDK object to dictionary for compatibility."""
        if obj is None:
            return {}
            
        result = {}
        
        # Handle SDK objects with additional_data
        if hasattr(obj, 'additional_data') and obj.additional_data:
            result.update(obj.additional_data)
        
        # Add regular properties
        if hasattr(obj, '__dict__'):
            for attr_name, attr_value in obj.__dict__.items():
                if not attr_name.startswith('_') and attr_value is not None:
                    # Skip some internal SDK attributes
                    if attr_name in ('backing_store', 'additional_data'):
                        continue
                    result[attr_name] = attr_value
        
        # Fallback: try to convert if it has items method (dict-like)
        if not result and hasattr(obj, 'items'):
            try:
                result = dict(obj)
            except (TypeError, ValueError):
                pass
        
        # Last resort: convert to string representation
        if not result:
            result = {"value": str(obj)}
            
        return result

    async def _extract_delta_token_from_link(self, delta_link: Optional[str]) -> Optional[str]:
        """Extract delta token from a delta link URL."""
        if not delta_link:
            return None
            
        try:
            parsed = urllib.parse.urlparse(delta_link)
            qs = urllib.parse.parse_qs(parsed.query)
            dt = qs.get("$deltatoken") or qs.get("deltatoken")
            return dt[0] if dt else None
        except Exception as e:
            logging.warning(f"Failed to extract delta token from link: {e}")
            return None

    def _extract_skiptoken_from_url(self, url: Optional[str]) -> Optional[str]:
        """Extract skiptoken from a URL."""
        if not url:
            return None
            
        try:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            st = qs.get("$skiptoken") or qs.get("skiptoken")
            return st[0] if st else None
        except Exception as e:
            logging.warning(f"Failed to extract skiptoken from URL: {e}")
            return None

    async def _execute_delta_request(
        self,
        request_builder,
        query_params: Dict[str, Any],
        fallback_to_full_sync: bool = True,
        used_stored_deltalink: bool = False,
        resource: str = "",
    ) -> Tuple[Any, bool]:
        """
        Execute a delta request with proper error handling and fallback logic.
        
        Returns:
            Tuple of (response, fallback_occurred)
        """
        # Get the classes once for reuse
        QueryParamsClass = request_builder.DeltaRequestBuilderGetQueryParameters
        RequestConfigClass = request_builder.DeltaRequestBuilderGetRequestConfiguration
        
        try:
            # Create query parameters using the SDK's classes
            query_params_obj = QueryParamsClass()
            
            # Set query parameters - for pagination with skiptoken, we need special handling
            for key, value in query_params.items():
                if hasattr(query_params_obj, key) and value is not None:
                    setattr(query_params_obj, key, value)
                elif key == "skiptoken":
                    # For skiptoken, we'll need to fall back to using the original approach
                    # but still through the Graph Service Client when possible
                    logging.debug(f"Handling skiptoken pagination: {value}")
            
            # Create request configuration
            request_config = RequestConfigClass(query_parameters=query_params_obj)
            
            # Execute the request
            response = await request_builder.get(request_config)
            return response, False
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if this is a delta token related error
            is_delta_error = any(
                phrase in error_msg for phrase in [
                    "token", "expired", "invalid", "bad", "malformed", "gone"
                ]
            )
            
            # Try fallback if it's a delta error and we have fallback enabled
            if (is_delta_error and fallback_to_full_sync and 
                "deltatoken" in query_params and used_stored_deltalink):
                
                logging.warning(
                    f"Delta token failed ({e}), falling back to full sync for {resource}"
                )
                
                # Clear stored delta link if it was invalid
                if used_stored_deltalink:
                    logging.info(f"Clearing invalid stored delta link for {resource}")
                    await self.delta_link_storage.delete(resource)
                
                try:
                    # Retry without delta token (full sync)
                    fallback_params = query_params.copy()
                    fallback_params.pop("deltatoken", None)
                    
                    fallback_query_params_obj = QueryParamsClass()
                    for key, value in fallback_params.items():
                        if hasattr(fallback_query_params_obj, key) and value is not None:
                            setattr(fallback_query_params_obj, key, value)
                    
                    fallback_config = RequestConfigClass(query_parameters=fallback_query_params_obj)
                    response = await request_builder.get(fallback_config)
                    return response, True
                    
                except Exception as fallback_error:
                    logging.error(f"Fallback to full sync also failed: {fallback_error}")
                    raise fallback_error
            else:
                # Re-raise the original error if no fallback or fallback not applicable
                raise e

    async def delta_query_stream(
        self,
        resource: str,
        select: Optional[List[str]] = None,
        filter: Optional[str] = None,
        delta_link: Optional[str] = None,
        deltatoken_latest: bool = False,
        top: Optional[int] = None,
        fallback_to_full_sync: bool = True,
    ) -> AsyncGenerator[Tuple[List[Dict[str, Any]], PageMetadata], None]:
        """
        Stream delta query results page by page using Microsoft Graph SDK.
        
        Args:
            resource: The resource type (e.g., "users", "applications")
            select: List of properties to select
            filter: OData filter expression
            delta_link: Explicit delta link to use (overrides stored one)
            deltatoken_latest: Use latest deltatoken for initial sync
            top: Maximum items per page
            fallback_to_full_sync: If True, retry with full sync when delta link fails
            
        Yields:
            Tuple of (objects_list, page_metadata) for each page
        """
        await self._initialize()
        
        if resource.lower() not in [k.lower() for k in self.SUPPORTED_RESOURCES.keys()]:
            raise ValueError(
                f"Unsupported resource type: {resource}. "
                f"Supported types: {list(self.SUPPORTED_RESOURCES.keys())}"
            )

        page = 0
        total_new_or_updated = 0
        total_deleted = 0
        total_changed = 0

        # Load existing delta link if not provided and get previous sync timestamp
        previous_sync_timestamp = None
        used_stored_deltalink = False
        deltatoken = None
        stored_delta_link = None
        
        if not delta_link and not deltatoken_latest:
            stored_delta_link = await self.delta_link_storage.get(resource)
            if stored_delta_link:
                used_stored_deltalink = True
                deltatoken = await self._extract_delta_token_from_link(stored_delta_link)
                
                # Get the timestamp from the previous sync
                metadata = await self.delta_link_storage.get_metadata(resource)
                if metadata and metadata.get("last_updated"):
                    try:
                        previous_sync_timestamp = datetime.fromisoformat(
                            metadata["last_updated"].replace("Z", "+00:00")
                        )
                    except Exception:
                        pass
        elif delta_link:
            deltatoken = await self._extract_delta_token_from_link(delta_link)

        # Get the appropriate request builder
        request_builder = self._get_delta_request_builder(resource)
        
        # Execute initial request - handle stored delta link vs new sync differently
        try:
            if used_stored_deltalink and stored_delta_link:
                # Use the stored delta link directly - it contains all original parameters
                logging.info(f"Using stored delta link for {resource} incremental sync")
                
                try:
                    # Create a request info object for the stored delta link URL
                    from kiota_abstractions.request_information import RequestInformation
                    from kiota_abstractions.method import Method
                    from msgraph.generated.applications.delta.delta_get_response import DeltaGetResponse
                    
                    request_info = RequestInformation()
                    request_info.http_method = Method.GET
                    request_info.url_template = stored_delta_link
                    
                    # Ensure the graph client and request adapter are available
                    if not self._graph_client or not self._graph_client.request_adapter:
                        raise ValueError("Graph client or request adapter not available")
                    
                    # Use the request adapter to send the request directly to the stored delta link
                    response = await self._graph_client.request_adapter.send_async(
                        request_info, DeltaGetResponse, {}
                    )
                    fallback_occurred = False
                    
                except Exception as e:
                    if fallback_to_full_sync:
                        logging.warning(f"Stored delta link failed ({e}), falling back to full sync with current parameters")
                        
                        # Clear the invalid stored delta link
                        await self.delta_link_storage.delete(resource)
                        used_stored_deltalink = False
                        
                        # Fall back to new sync with current parameters
                        query_params = self._build_query_parameters(
                            select=select,
                            filter=filter, 
                            top=top,
                            deltatoken_latest=deltatoken_latest
                        )
                        
                        response, fallback_occurred = await self._execute_delta_request(
                            request_builder,
                            query_params,
                            fallback_to_full_sync,
                            False,  # Not using stored delta link anymore
                            resource
                        )
                    else:
                        raise e
                
            else:
                # Build query parameters for new sync (no stored delta link)
                query_params = self._build_query_parameters(
                    select=select,
                    filter=filter, 
                    top=top,
                    deltatoken=deltatoken,
                    deltatoken_latest=deltatoken_latest
                )
                
                # Execute new sync request
                response, fallback_occurred = await self._execute_delta_request(
                    request_builder,
                    query_params,
                    fallback_to_full_sync,
                    used_stored_deltalink,
                    resource
                )
            
            if fallback_occurred:
                used_stored_deltalink = False  # No longer using stored delta link after fallback
                
        except Exception as e:
            logging.error(f"Failed to execute delta query for {resource}: {e}")
            raise

        # Process pages
        while response:
            page += 1
            
            # Extract objects from response
            objects = []
            if hasattr(response, 'value') and response.value:
                objects = [self._convert_sdk_object_to_dict(obj) for obj in response.value]

            # Analyze change types in this page
            page_new_or_updated = 0
            page_deleted = 0
            page_changed = 0

            for obj in objects:
                removed_info = obj.get("@removed")
                if removed_info:
                    reason = removed_info.get("reason", "unknown")
                    if reason == "deleted":
                        page_deleted += 1
                        total_deleted += 1
                    elif reason == "changed":
                        page_changed += 1
                        total_changed += 1
                    else:
                        page_changed += 1
                        total_changed += 1
                else:
                    page_new_or_updated += 1
                    total_new_or_updated += 1

            # Get delta link from response
            delta_link_resp = None
            
            # Try different delta link attribute names
            delta_link_attrs = ['odata_delta_link', 'deltaLink', 'delta_link', '@odata.deltaLink']
            for attr in delta_link_attrs:
                value = getattr(response, attr, None)
                if value:
                    delta_link_resp = value
                    break
            else:
                # Check additional_data for delta link
                if hasattr(response, 'additional_data') and response.additional_data:
                    for key in ['@odata.deltaLink', 'deltaLink', 'odata_delta_link']:
                        if key in response.additional_data:
                            delta_link_resp = response.additional_data[key]
                            break
            # Check for next page
            has_next_page = bool(hasattr(response, 'odata_next_link') and response.odata_next_link)

            page_meta = PageMetadata(
                page=page,
                object_count=len(objects),
                has_next_page=has_next_page,
                delta_link=delta_link_resp,
                raw_response_size=len(str(response)),  # Approximate size
                page_new_or_updated=page_new_or_updated,
                page_deleted=page_deleted,
                page_changed=page_changed,
                total_new_or_updated=total_new_or_updated,
                total_deleted=total_deleted,
                total_changed=total_changed,
                since_timestamp=previous_sync_timestamp,
            )

            # Save delta link whenever we get one
            if delta_link_resp:
                change_summary = ChangeSummary(
                    new_or_updated=total_new_or_updated,
                    deleted=total_deleted,
                    changed=total_changed,
                    timestamp=previous_sync_timestamp,
                )

                metadata = {
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                    "total_pages": page,
                    "change_summary": {
                        "new_or_updated": change_summary.new_or_updated,
                        "deleted": change_summary.deleted,
                        "changed": change_summary.changed,
                        "total": change_summary.total,
                    },
                    "resource_params": {"select": select, "filter": filter, "top": top},
                }
                await self.delta_link_storage.set(resource, delta_link_resp, metadata)
                logging.info(
                    f"Saved delta link for {resource} (page {page}) - "
                    f"{total_new_or_updated} new/updated, {total_deleted} deleted, "
                    f"{total_changed} changed"
                )
            else:
                logging.debug(f"No delta link found on page {page} for {resource}")

            yield objects, page_meta

            # Check if we should continue to next page
            if not has_next_page:
                break
                
            # For delta queries, follow pagination using the next URL directly
            next_url = response.odata_next_link
            logging.debug(f"Following next page URL: {next_url}")
            
            try:
                # Use the Graph SDK's request adapter to make a direct request to the next URL
                # This preserves all the parameters encoded in the next_url
                logging.info(f"Calling delta query for resource: {resource} page {page + 1}")
                
                # Create a request info object for the next URL
                from kiota_abstractions.request_information import RequestInformation
                from kiota_abstractions.method import Method
                from msgraph.generated.applications.delta.delta_get_response import DeltaGetResponse
                
                request_info = RequestInformation()
                request_info.http_method = Method.GET
                request_info.url_template = next_url
                
                # Ensure the graph client and request adapter are available
                if not self._graph_client or not self._graph_client.request_adapter:
                    logging.error("Graph client or request adapter not available")
                    break
                
                # Use the request adapter to send the request
                response = await self._graph_client.request_adapter.send_async(
                    request_info, DeltaGetResponse, {}
                )
                    
            except Exception as e:
                logging.error(f"Error fetching next page: {e}")
                break

    async def delta_query_all(
        self,
        resource: str,
        select: Optional[List[str]] = None,
        filter: Optional[str] = None,
        delta_link: Optional[str] = None,
        deltatoken_latest: bool = False,
        top: Optional[int] = None,
        max_objects: Optional[int] = None,
        fallback_to_full_sync: bool = True,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], DeltaQueryMetadata]:
        """
        Execute delta query and return all results using Microsoft Graph SDK.
        
        Args:
            resource: The resource type (e.g., "users", "applications")
            select: List of properties to select
            filter: OData filter expression
            delta_link: Explicit delta link to use (overrides stored one)
            deltatoken_latest: Use latest deltatoken for initial sync
            top: Maximum items per page
            max_objects: Maximum total objects to return
            fallback_to_full_sync: If True, retry with full sync when delta link fails
            
        Returns:
            Tuple of (all_objects, final_delta_link, metadata)
        """
        all_objects: List[Dict[str, Any]] = []
        final_delta_link: Optional[str] = None
        total_pages = 0
        start_time = datetime.now(timezone.utc)

        # Track change types
        total_new_or_updated = 0
        total_deleted = 0
        total_changed = 0

        # Check if we used a stored delta link before starting
        used_stored_deltalink = (
            not delta_link and 
            not deltatoken_latest and 
            bool(await self.delta_link_storage.get(resource))
        )

        # Get the timestamp from the previous sync
        previous_sync_timestamp = None
        if used_stored_deltalink:
            metadata = await self.delta_link_storage.get_metadata(resource)
            if metadata and metadata.get("last_updated"):
                try:
                    previous_sync_timestamp = datetime.fromisoformat(
                        metadata["last_updated"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

        async for objects, page_meta in self.delta_query_stream(
            resource,
            select,
            filter,
            delta_link,
            deltatoken_latest,
            top,
            fallback_to_full_sync,
        ):
                all_objects.extend(objects)
                total_pages = page_meta.page
                final_delta_link = page_meta.delta_link or final_delta_link

                # Update totals from page metadata
                total_new_or_updated = page_meta.total_new_or_updated
                total_deleted = page_meta.total_deleted
                total_changed = page_meta.total_changed

                logging.info(
                    f"Page {total_pages}: received {len(objects)} objects "
                    f"(cumulative: {len(all_objects)}) - "
                    f"{page_meta.page_new_or_updated} new/updated, "
                    f"{page_meta.page_deleted} deleted, "
                    f"{page_meta.page_changed} changed"
                )

                # Respect max_objects limit
                if max_objects and len(all_objects) >= max_objects:
                    logging.info(f"Reached max_objects limit ({max_objects})")
                    # Trim the list to the exact limit
                    all_objects = all_objects[:max_objects]
                    break

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        change_summary = ChangeSummary(
            new_or_updated=total_new_or_updated,
            deleted=total_deleted,
            changed=total_changed,
            timestamp=previous_sync_timestamp,
        )

        resource_params = ResourceParams(
            select=select,
            filter=filter,
            top=top,
            deltatoken_latest=deltatoken_latest,
            max_objects=max_objects,
        )

        meta = DeltaQueryMetadata(
            changed_count=len(all_objects),
            pages_fetched=total_pages,
            duration_seconds=duration,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            used_stored_deltalink=used_stored_deltalink,
            change_summary=change_summary,
            resource_params=resource_params,
        )

        return all_objects, final_delta_link, meta

    async def reset_delta_link(self, resource: str) -> None:
        """Reset/delete the stored delta link for a resource."""
        await self.delta_link_storage.delete(resource)
        logging.info(f"Reset delta link for {resource}")

    def __del__(self) -> None:
        """Destructor - schedule cleanup if not already closed."""
        if not self._closed:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._internal_close())
            except RuntimeError:
                logging.warning(
                    "AsyncDeltaQueryClient destroyed without proper cleanup "
                    "(no running event loop)"
                )


# ---------- Usage Example ----------


async def example_usage() -> None:
    """
    Example of simplified usage with Microsoft Graph SDK.
    
    This example demonstrates how authentication works with DefaultAzureCredential:
    1. Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
    2. Managed Identity (in Azure environments)
    3. Azure CLI (az login)
    4. Visual Studio/VS Code
    5. Azure PowerShell
    
    For local development, set these environment variables:
    - AZURE_CLIENT_ID=your-app-registration-client-id
    - AZURE_CLIENT_SECRET=your-app-registration-client-secret
    - AZURE_TENANT_ID=your-azure-tenant-id
    """
    
    # Load environment variables if using a .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("📄 Loaded environment variables from .env file")
    except ImportError:
        print("ℹ️  python-dotenv not available, using system environment variables")
    
    # Simple instantiation with Microsoft Graph SDK
    client = AsyncDeltaQueryClient()

    # Just use it - authentication and sessions handled by SDK
    users, delta_link, meta = await client.delta_query_all(
        resource="users", 
        select=["id", "displayName", "mail"], 
        top=100
    )

    print(f"Retrieved {len(users)} users in {meta.duration_seconds:.2f}s")
    print(
        f"Change summary: {meta.change_summary.new_or_updated} new/updated, "
        f"{meta.change_summary.deleted} deleted, {meta.change_summary.changed} changed"
    )
    # SDK handles cleanup automatically


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Simple usage with Microsoft Graph SDK
    asyncio.run(example_usage())
