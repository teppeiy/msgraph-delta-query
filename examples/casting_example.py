#!/usr/bin/env python3
"""
SDK Model Casting Example for Delta Query Stream

This example demonstrates the proper way to cast Microsoft Graph objects
to their corresponding SDK models when using delta_query_stream.
"""

import asyncio
from msgraph_delta_query import AsyncDeltaQueryClient
from msgraph.generated.models.user import User
from msgraph.generated.models.application import Application

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, skipping .env file loading")

async def basic_casting_example():
    """
    Show basic object casting with delta_query_stream
    """
    print("📚 Basic SDK Model Casting Example")
    print("=" * 50)
    
    async with AsyncDeltaQueryClient() as client:
        print("📡 Streaming users with proper SDK model casting...\n")
        
        async for objects, page_meta in client.delta_query_stream(
            resource="users",
            select=["id", "displayName", "userPrincipalName", "mail"],
            top=5  # Small number for demo
        ):
            print(f"📄 Page {page_meta.page} - {len(objects)} objects received")
            
            for i, user_obj in enumerate(objects, 1):
                # Method 1: Direct casting if already correct type
                if isinstance(user_obj, User):
                    user = user_obj
                    print(f"  ✅ [{i}] Already User object: {user.display_name}")
                else:
                    # Method 2: Manual casting for non-SDK objects
                    user = User()
                    
                    # Copy standard properties
                    user.id = getattr(user_obj, 'id', None)
                    user.display_name = getattr(user_obj, 'display_name', None)
                    user.user_principal_name = getattr(user_obj, 'user_principal_name', None)
                    user.mail = getattr(user_obj, 'mail', None)
                    
                    # Copy additional_data for deleted objects
                    if hasattr(user_obj, 'additional_data'):
                        setattr(user, 'additional_data', user_obj.additional_data)
                    
                    print(f"  🔄 [{i}] Casted to User: {user.display_name}")
                
                # Now use with full type safety
                print(f"      📧 Email: {user.mail or 'No email'}")
                print(f"      🆔 ID: {user.id}")
                
                # Check for deleted objects
                additional_data = getattr(user, 'additional_data', {})
                if additional_data and "@removed" in additional_data:
                    print(f"      🗑️  DELETED OBJECT")
            
            break  # Just show first page
    
    print("\n✅ Basic casting example completed!")

async def helper_function_casting_example():
    """
    Show casting using a reusable helper function
    """
    print("\n📚 Helper Function Casting Example")
    print("=" * 50)
    
    def cast_to_user(obj) -> User:
        """Helper function to cast any object to User"""
        if isinstance(obj, User):
            return obj
        
        user = User()
        # Copy all available properties
        for attr in ['id', 'display_name', 'user_principal_name', 'mail', 'job_title']:
            if hasattr(obj, attr):
                setattr(user, attr, getattr(obj, attr))
        
        # Preserve additional_data
        if hasattr(obj, 'additional_data'):
            setattr(user, 'additional_data', obj.additional_data)
        
        return user
    
    async with AsyncDeltaQueryClient() as client:
        print("📡 Streaming users with helper function casting...\n")
        
        async for objects, page_meta in client.delta_query_stream(
            resource="users",
            select=["id", "displayName", "userPrincipalName", "jobTitle"],
            top=3
        ):
            print(f"📄 Page {page_meta.page} - Processing objects")
            
            for i, user_obj in enumerate(objects, 1):
                # Use helper function for clean casting
                user: User = cast_to_user(user_obj)
                
                print(f"  👤 [{i}] {user.display_name}")
                print(f"      💼 Job: {user.job_title or 'Not specified'}")
                print(f"      📧 Email: {user.user_principal_name}")
                
                # Type-safe access (IDE will provide autocomplete)
                print(f"      🔤 Name length: {len(user.display_name or '')}")
            
            break
    
    print("\n✅ Helper function casting example completed!")

async def main():
    """Run all casting examples"""
    print("🎯 SDK Model Casting Examples for Delta Query Stream")
    print("🔧 Learn how to properly cast Graph objects to SDK models")
    print("=" * 70)
    
    try:
        await basic_casting_example()
        await helper_function_casting_example()
        
        print("\n🎉 All casting examples completed!")
        print("\n💡 Key Benefits of Proper Casting:")
        print("   ✅ Full IDE autocomplete support")
        print("   ✅ Type safety and error prevention")
        print("   ✅ Better code maintainability")
        print("   ✅ Consistent property access patterns")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
