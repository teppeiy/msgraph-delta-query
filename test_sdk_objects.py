#!/usr/bin/env python3
"""
Test script to demonstrate returning SDK objects vs dictionaries.
"""

import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from msgraph_delta_query.client import AsyncDeltaQueryClient


async def test_sdk_objects():
    """Test returning SDK objects vs dictionaries."""
    
    print("Testing SDK object return types...")
    
    # Mock credential
    mock_credential = AsyncMock()
    
    # Test 1: Dictionary return (default)
    print("\n=== Test 1: Dictionary objects (default) ===")
    client_dict = AsyncDeltaQueryClient(credential=mock_credential)
    print(f"return_sdk_objects setting: {client_dict.return_sdk_objects}")
    
    # Mock a user object from the SDK
    mock_user = Mock()
    mock_user.id = "user123"
    mock_user.display_name = "John Doe"
    mock_user.mail = "john@example.com"
    mock_user.__dict__ = {
        "id": "user123",
        "display_name": "John Doe", 
        "mail": "john@example.com"
    }
    
    # Test the processing method
    result_dict = client_dict._process_sdk_object(mock_user)
    print(f"Result type: {type(result_dict)}")
    print(f"Result content: {result_dict}")
    
    # Test 2: SDK object return
    print("\n=== Test 2: SDK objects ===")
    client_sdk = AsyncDeltaQueryClient(credential=mock_credential, return_sdk_objects=True)
    print(f"return_sdk_objects setting: {client_sdk.return_sdk_objects}")
    
    result_sdk = client_sdk._process_sdk_object(mock_user)
    print(f"Result type: {type(result_sdk)}")
    print(f"Result is same object: {result_sdk is mock_user}")
    print(f"Result ID: {result_sdk.id}")
    print(f"Result display name: {result_sdk.display_name}")
    print(f"Result mail: {result_sdk.mail}")


if __name__ == "__main__":
    asyncio.run(test_sdk_objects())
