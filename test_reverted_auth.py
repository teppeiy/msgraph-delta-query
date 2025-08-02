import asyncio
import logging
from src.msgraph_delta_query.client import AsyncDeltaQueryClient

logging.basicConfig(level=logging.DEBUG)

async def test():
    print("Testing reverted DefaultAzureCredential...")
    client = AsyncDeltaQueryClient()
    await client._initialize()
    print('✅ DefaultAzureCredential initialized successfully')
    await client._internal_close()
    print('✅ Client closed successfully')

if __name__ == "__main__":
    asyncio.run(test())
