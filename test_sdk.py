"""
Simple test to understand the Graph SDK delta functionality
"""
import asyncio
import logging
from msgraph import GraphServiceClient
from azure.identity.aio import DefaultAzureCredential

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_graph_sdk():
    """Test the Graph SDK delta functionality"""
    try:
        # Create client
        credential = DefaultAzureCredential()
        client = GraphServiceClient(
            credentials=credential,
            scopes=["https://graph.microsoft.com/.default"]
        )
        
        print("✅ Graph client created successfully")
        
        # Try to get users delta (this will likely fail without proper auth, but we can see the structure)
        try:
            users_delta_builder = client.users.delta
            print("✅ Users delta builder obtained")
            print("Delta builder type:", type(users_delta_builder))
            
            # Check the query parameters class
            QueryParams = users_delta_builder.DeltaRequestBuilderGetQueryParameters
            print("✅ Query parameters class:", QueryParams)
            
            # Create query params instance
            query_params = QueryParams()
            print("✅ Query params instance created")
            print("Query params attributes:", [attr for attr in dir(query_params) if not attr.startswith('_')])
            
            # Try to set some parameters
            if hasattr(query_params, 'select'):
                query_params.select = ["id", "displayName"]
                print("✅ Select parameter set")
            
            if hasattr(query_params, 'top'):
                query_params.top = 10
                print("✅ Top parameter set")
                
            # Check RequestConfiguration
            RequestConfig = users_delta_builder.DeltaRequestBuilderGetRequestConfiguration
            print("✅ Request configuration class:", RequestConfig)
            
            config = RequestConfig(query_parameters=query_params)
            print("✅ Request configuration created")
            
        except Exception as e:
            print(f"❌ Error with delta builder: {e}")
            
    except Exception as e:
        print(f"❌ Error creating client: {e}")
    finally:
        # Close credential
        if 'credential' in locals():
            await credential.close()

if __name__ == "__main__":
    asyncio.run(test_graph_sdk())
