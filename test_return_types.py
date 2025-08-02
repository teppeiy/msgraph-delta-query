#!/usr/bin/env python3
"""
Test script to show what types of objects are returned by msgraph-delta-query
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from msgraph_delta_query import AsyncDeltaQueryClient


async def test_return_types():
    """Test what types are returned by the delta query client"""
    print("=== msgraph-delta-query Return Type Analysis ===\n")
    
    # Create a mock user object like what Graph API returns
    sample_graph_user = {
        "id": "12345678-1234-1234-1234-123456789012",
        "displayName": "John Doe",
        "mail": "john.doe@example.com", 
        "userPrincipalName": "john.doe@example.com",
        "accountEnabled": True,
        "createdDateTime": "2024-01-15T10:30:45Z",
        "jobTitle": "Software Engineer",
        "department": "Engineering"
    }
    
    print("📋 What msgraph-delta-query returns:")
    print(f"Type: {type(sample_graph_user)}")
    print(f"Contents: {sample_graph_user}")
    print()
    
    print("🔍 Key differences from Python Graph SDK:")
    print("1. msgraph-delta-query returns: List[Dict[str, Any]]")
    print("   - Raw JSON dictionaries from Microsoft Graph API")
    print("   - Direct access via user['displayName']")
    print("   - No method calls needed")
    print()
    
    print("2. Python Graph SDK would return: List[User]")
    print("   - Strongly-typed User objects")
    print("   - Access via user.display_name")
    print("   - IntelliSense support for properties")
    print()
    
    print("📊 Example access patterns:")
    print("msgraph-delta-query:")
    print(f"  user['displayName'] = {sample_graph_user['displayName']}")
    print(f"  user['mail'] = {sample_graph_user['mail']}")
    print(f"  user.get('jobTitle', 'N/A') = {sample_graph_user.get('jobTitle', 'N/A')}")
    print()
    
    print("Python Graph SDK (for comparison):")
    print("  user.display_name = 'John Doe'")
    print("  user.mail = 'john.doe@example.com'")
    print("  user.job_title = 'Software Engineer'")
    print()
    
    print("✅ Benefits of msgraph-delta-query approach:")
    print("  - Works with any Graph API resource without SDK updates")
    print("  - Handles custom attributes and extensions seamlessly")
    print("  - Lightweight - no object model overhead")
    print("  - Direct control over what fields are selected")
    print("  - Works great for data processing and ETL scenarios")
    print()
    
    print("🔧 When to use Python Graph SDK instead:")
    print("  - Need strong typing and IntelliSense")
    print("  - Building complex applications with business logic")
    print("  - Need validation of property names at design time")
    print("  - Prefer object-oriented programming patterns")


if __name__ == "__main__":
    asyncio.run(test_return_types())
