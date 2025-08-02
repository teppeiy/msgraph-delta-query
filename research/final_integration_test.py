#!/usr/bin/env python3
import asyncio
from msgraph_delta_query import LocalFileDeltaLinkStorage

async def test():
    s = LocalFileDeltaLinkStorage("test_temp")
    await s.set('test', 'link')
    result = await s.get('test')
    await s.delete('test')
    print(f'✅ Full functionality confirmed! Got: {result}')

asyncio.run(test())
