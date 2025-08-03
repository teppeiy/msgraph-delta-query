import asyncio
from msgraph_delta_query import AsyncDeltaQueryClient
from msgraph.generated.models.user import User
from typing import List, cast

async def query_all_users():
    async with AsyncDeltaQueryClient() as client:
        async for objects, page_meta in client.delta_query_stream(resource="users"):
            users = cast(List[User], [obj for obj in objects if getattr(obj, 'odata_type', '') == '#microsoft.graph.user'])
            print(f"Page {page_meta.page}: {len(users)} users")
            for user in users:
                print(f"  {user.display_name} ({user.user_principal_name})")
            if not page_meta.has_next_page:
                break

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables if needed
    asyncio.run(query_all_users())