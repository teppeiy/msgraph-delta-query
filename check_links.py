import asyncio
from msgraph_delta_query.storage import LocalFileDeltaLinkStorage

async def check_stored_links():
    storage = LocalFileDeltaLinkStorage()
    apps_link = await storage.get('applications')
    if apps_link:
        print(f'Stored delta link length: {len(apps_link)}')
        print(f'Stored delta link preview: {apps_link[:100]}...')
        metadata = await storage.get_metadata('applications')
        if metadata:
            print(f'Last updated: {metadata.get("last_updated")}')
    else:
        print('No stored delta link found')

asyncio.run(check_stored_links())
