import aiohttp
import logging
import os
import json
import urllib.parse
import asyncio
import weakref
from typing import Optional, Any, Dict, List, Tuple, AsyncGenerator
from azure.identity.aio import DefaultAzureCredential
from datetime import datetime, timezone
from .storage import DeltaLinkStorage, LocalFileDeltaLinkStorage




# Global registry to track all client instances for cleanup
_client_registry = weakref.WeakSet()

async def _cleanup_all_clients():
    """Cleanup function for all clients - called during event loop shutdown."""
    for client in list(_client_registry):
        try:
            await client._internal_close()
        except Exception as e:
            logging.warning(f"Error cleaning up client: {e}")

# ---------- Enhanced AsyncDeltaQueryClient ----------

class AsyncDeltaQueryClient:
    GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=300, connect=30)

    def __init__(
        self,
        credential: Optional[DefaultAzureCredential] = None,
        delta_link_storage: Optional[DeltaLinkStorage] = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
        max_concurrent_requests: int = 10
    ):
        self.credential = credential
        self.delta_link_storage = delta_link_storage or LocalFileDeltaLinkStorage()
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._session: Optional[aiohttp.ClientSession] = None
        self._credential_created = False
        self._initialized = False
        self._closed = False
        
        # Register this instance for cleanup
        _client_registry.add(self)
        
        # Set up automatic cleanup when event loop shuts down
        try:
            loop = asyncio.get_running_loop()
            # Only add the cleanup callback once
            if not hasattr(loop, '_delta_client_cleanup_added'):
                # Check if signal handler method exists before using it
                if hasattr(loop, 'add_signal_handler'):
                    try:
                        import signal
                        for sig in [signal.SIGTERM, signal.SIGINT]:
                            try:
                                loop.add_signal_handler(sig, lambda: asyncio.create_task(_cleanup_all_clients()))
                            except (NotImplementedError, OSError):
                                pass  # Signal handlers not supported on this platform
                    except ImportError:
                        pass
                # Mark that we've attempted to set up cleanup (use setattr to avoid pylint warning)
                setattr(loop, '_delta_client_cleanup_added', True)
        except RuntimeError:
            pass  # No running loop

    async def _initialize(self):
        """Initialize the client - create session and credential if needed."""
        if self._initialized or self._closed:
            return
            
        # Create session
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
            logging.debug("Created aiohttp session")
        
        # Create credential if not provided
        if self.credential is None:
            self.credential = DefaultAzureCredential()
            self._credential_created = True
            logging.debug("Created DefaultAzureCredential")
        
        self._initialized = True

    async def _internal_close(self):
        """Internal close method - can be called multiple times safely."""
        if self._closed:
            return
            
        self._closed = True
        
        # Close our session
        if self._session and not self._session.closed:
            await self._session.close()
            logging.debug("Closed aiohttp session")
        self._session = None
        
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

    async def get_token(self) -> str:
        """Get access token for Microsoft Graph API."""
        await self._initialize()
        if self.credential is None:
            raise ValueError("Credential is not initialized")
        try:
            token = await self.credential.get_token("https://graph.microsoft.com/.default")
            return token.token
        except Exception as e:
            logging.error(f"Failed to get access token: {e}")
            raise

    async def _make_request(
        self, 
        url: str, 
        headers: Dict[str, str]
    ) -> Tuple[int, str, Dict[str, Any]]:
        """Make HTTP request with rate limiting and error handling."""
        await self._initialize()
        
        if self._session is None:
            raise ValueError("HTTP session is not initialized")
        
        async with self.semaphore:
            backoff, max_backoff = 1, 60
            max_retries = 5
            
            for attempt in range(max_retries):
                try:
                    logging.debug(f"Request attempt {attempt + 1}: {url}")
                    async with self._session.get(url, headers=headers) as resp:
                        text = await resp.text()
                        
                        if resp.status == 429:
                            retry_after = resp.headers.get("Retry-After")
                            wait = int(retry_after) if retry_after and retry_after.isdigit() else backoff
                            logging.warning(f"Rate limited (429) - waiting {wait}s before retry")
                            await asyncio.sleep(wait)
                            backoff = min(backoff * 2, max_backoff)
                            continue
                        elif resp.status == 503:
                            logging.warning(f"Service unavailable (503) - waiting {backoff}s before retry")
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * 2, max_backoff)
                            continue
                        elif resp.status in (500, 502, 504):
                            logging.warning(f"Server error ({resp.status}) - waiting {backoff}s before retry")
                            await asyncio.sleep(backoff)
                            backoff = min(backoff * 2, max_backoff)
                            continue
                        elif resp.status == 401:
                            logging.error("Unauthorized (401) - token may be expired")
                            return resp.status, text, {}
                        elif resp.status != 200:
                            logging.error(f"HTTP {resp.status}: {text}")
                            return resp.status, text, {}

                        result = await resp.json()
                        return resp.status, text, result

                except asyncio.TimeoutError:
                    logging.warning(f"Request timeout - attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                except Exception as e:
                    logging.error(f"Request failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
            
            raise Exception(f"Max retries ({max_retries}) exceeded")

    async def delta_query_stream(
        self,
        resource: str,
        select: Optional[List[str]] = None,
        filter: Optional[str] = None,
        delta_link: Optional[str] = None,
        deltatoken_latest: bool = False,
        top: Optional[int] = None
    ) -> AsyncGenerator[Tuple[List[Dict[str, Any]], Dict[str, Any]], None]:
        """
        Stream delta query results page by page.
        Yields (objects, page_metadata) for each page.
        """
        page = 0
        next_link: Optional[str] = None
        
        # Load existing delta link if not provided
        if not delta_link:
            delta_link = await self.delta_link_storage.get(resource)

        token = await self.get_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        # Build initial URL
        base_url = f"{self.GRAPH_BASE}/{resource}/delta"
        params: Dict[str, str] = {}

        if select:
            params["$select"] = ",".join(select)
        if filter:
            params["$filter"] = filter
        if deltatoken_latest:
            params["$deltatoken"] = "latest"
        elif delta_link:
            parsed = urllib.parse.urlparse(delta_link)
            qs = urllib.parse.parse_qs(parsed.query)
            dt = qs.get('$deltatoken') or qs.get('deltatoken')
            if dt:
                params["$deltatoken"] = dt[0]
        if top:
            params["$top"] = str(top)

        first_call = True

        while True:
            url = (f"{base_url}?{urllib.parse.urlencode(params)}") if first_call else next_link
            first_call = False

            if not url:
                break

            status, text, result = await self._make_request(url, headers)
            
            if status != 200:
                break

            objects = result.get("value", [])
            page += 1
            next_link = result.get("@odata.nextLink")
            delta_link_resp = result.get("@odata.deltaLink")

            page_meta = {
                "page": page,
                "object_count": len(objects),
                "has_next_page": bool(next_link),
                "delta_link": delta_link_resp,
                "raw_response_size": len(text)
            }

            # Save delta link whenever we get one, not just at the end
            # This ensures it's saved even if the user breaks early from the loop
            if delta_link_resp:
                metadata = {
                    "last_sync": datetime.now(timezone.utc).isoformat(),
                    "total_pages": page,
                    "resource_params": {
                        "select": select,
                        "filter": filter,
                        "top": top
                    }
                }
                await self.delta_link_storage.set(resource, delta_link_resp, metadata)
                logging.info(f"Saved delta link for {resource} (page {page})")

            yield objects, page_meta

            if not next_link:
                # We've reached the end naturally
                break

    async def delta_query_all(
        self,
        resource: str,
        select: Optional[List[str]] = None,
        filter: Optional[str] = None,
        delta_link: Optional[str] = None,
        deltatoken_latest: bool = False,
        top: Optional[int] = None,
        max_objects: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Dict[str, Any]]:
        """
        Execute delta query and return all results.
        Enhanced with better metadata and optional limits.
        """
        all_objects: List[Dict[str, Any]] = []
        final_delta_link: Optional[str] = None
        total_pages = 0
        start_time = datetime.now(timezone.utc)
        
        # Check if we used a stored delta link before starting
        used_stored_deltalink = bool(not delta_link and await self.delta_link_storage.get(resource))

        try:
            async for objects, page_meta in self.delta_query_stream(
                resource, select, filter, delta_link, deltatoken_latest, top
            ):
                all_objects.extend(objects)
                total_pages = page_meta["page"]
                final_delta_link = page_meta.get("delta_link") or final_delta_link
                
                logging.info(f"Page {total_pages}: received {len(objects)} objects "
                            f"(cumulative: {len(all_objects)})")
                
                # Respect max_objects limit
                if max_objects and len(all_objects) >= max_objects:
                    all_objects = all_objects[:max_objects]
                    logging.info(f"Reached max_objects limit ({max_objects})")
                    break
        finally:
            # Auto-cleanup after each major operation
            await self._internal_close()

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        meta = {
            "changed_count": len(all_objects),
            "pages_fetched": total_pages,
            "duration_seconds": duration,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "used_stored_deltalink": used_stored_deltalink,
            "resource_params": {
                "select": select,
                "filter": filter,
                "top": top,
                "deltatoken_latest": deltatoken_latest,
                "max_objects": max_objects
            }
        }

        return all_objects, final_delta_link, meta

    async def reset_delta_link(self, resource: str):
        """Reset/delete the stored delta link for a resource."""
        await self.delta_link_storage.delete(resource)
        logging.info(f"Reset delta link for {resource}")

    def __del__(self):
        """Destructor - schedule cleanup if not already closed."""
        if not self._closed:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._internal_close())
            except RuntimeError:
                # No running loop, can't clean up async resources
                logging.warning("AsyncDeltaQueryClient destroyed without proper cleanup (no running event loop)")

# ---------- Usage Example ----------

async def example_usage():
    """Example of simplified usage - no context manager, no manual closing needed."""
    
    # Simple instantiation - everything handled internally
    client = AsyncDeltaQueryClient()
    
    # Just use it - sessions are created and cleaned up automatically
    users, delta_link, meta = await client.delta_query_all(
        resource="users",
        select=["id", "displayName", "mail"],
        top=100
    )
    
    print(f"Retrieved {len(users)} users in {meta['duration_seconds']:.2f}s")
    # No need to close anything - handled automatically

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Simple usage
    asyncio.run(example_usage())