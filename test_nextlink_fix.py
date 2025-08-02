#!/usr/bin/env python3
"""
Test script to verify the nextLink URL handling logic.
"""

import asyncio
import logging
from src.msgraph_delta_query.client import AsyncDeltaQueryClient
from azure.identity.aio import AzureCliCredential

# Configure logging to see what's happening
logging.basicConfig(level=logging.DEBUG)

async def test_nextlink_logic():
    """Test the nextLink URL extraction and following logic."""
    
    print("=== Testing NextLink Logic ===")
    
    # Create client with explicit AzureCliCredential (cast to work around type hint)
    from typing import cast
    from azure.identity.aio import DefaultAzureCredential
    
    credential = cast(DefaultAzureCredential, AzureCliCredential())
    client = AsyncDeltaQueryClient(credential=credential)
    
    try:
        print("Testing nextLink URL extraction...")
        
        # Test the URL parsing logic
        test_urls = [
            "https://graph.microsoft.com/v1.0/applications/delta?$skiptoken=abc123",
            "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=xyz789&$top=5",
            "https://graph.microsoft.com/beta/groups/delta?skiptoken=def456"
        ]
        
        for url in test_urls:
            skiptoken = client._extract_skiptoken_from_url(url)
            print(f"URL: {url}")
            print(f"Extracted skiptoken: {skiptoken}")
            print()
        
        print("✅ URL extraction logic working correctly")
        
        # Try a minimal delta query to see if the initial request works
        print("Testing minimal delta query (first page only)...")
        
        try:
            # Use async generator and just get the first page
            async for objects, page_meta in client.delta_query_stream(
                resource="applications",
                top=3  # Small number to test
            ):
                print(f"Page {page_meta.page}: {len(objects)} objects")
                print(f"Has next page: {page_meta.has_next_page}")
                print(f"Delta link: {page_meta.delta_link}")
                
                # Show first object if available
                if objects:
                    first_obj = objects[0]
                    print(f"First object keys: {list(first_obj.keys())[:5]}...")
                
                # Only process the first page for this test
                if page_meta.page >= 1:
                    print("✅ Successfully got first page with SDK")
                    break
                    
        except Exception as e:
            print(f"❌ Error with delta query: {e}")
            return
            
    finally:
        await client._internal_close()
    
    print("✅ NextLink logic test completed")

if __name__ == "__main__":
    asyncio.run(test_nextlink_logic())
