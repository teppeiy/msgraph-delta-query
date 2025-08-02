# SDK Object Types Feature

The `AsyncDeltaQueryClient` now supports returning strongly-typed Microsoft Graph SDK objects instead of dictionaries, providing better type safety and IDE support.

## Usage Options

### 1. Dictionary Results (Default - Backward Compatible)
```python
client = AsyncDeltaQueryClient()
users, delta_link, metadata = await client.delta_query_all(resource="users")
# Returns: List[Dict[str, Any]]

# Access data as dictionary
user_name = users[0]["displayName"]
user_email = users[0]["mail"]
```

### 2. Strongly-Typed SDK Objects
```python
client = AsyncDeltaQueryClient(return_sdk_objects=True)
users, delta_link, metadata = await client.delta_query_all(resource="users")
# Returns: List[msgraph.generated.models.user.User]

# Access data with type safety and IDE autocomplete
user_name = users[0].display_name
user_email = users[0].mail
```

### 3. Typed Convenience Method
```python
client = AsyncDeltaQueryClient()  # Can use default client
users, delta_link, metadata = await client.delta_query_all_typed(resource="users")
# Returns: List[msgraph.generated.models.user.User]

# This temporarily switches to SDK objects for just this call
user_name = users[0].display_name
user_email = users[0].mail
```

## SDK Object Types by Resource

| Resource | SDK Object Type |
|----------|----------------|
| `users` | `msgraph.generated.models.user.User` |
| `applications` | `msgraph.generated.models.application.Application` |
| `groups` | `msgraph.generated.models.group.Group` |
| `serviceprincipals` | `msgraph.generated.models.service_principal.ServicePrincipal` |

## Benefits of SDK Objects

1. **Type Safety**: Full type checking with mypy/pylance
2. **IDE Support**: Autocomplete and IntelliSense for all properties
3. **Documentation**: Built-in docstrings for all properties and methods
4. **Validation**: SDK objects include built-in validation
5. **Consistency**: Same objects used throughout Microsoft Graph SDK

## Example with Type Hints

```python
from typing import List
from msgraph.generated.models.user import User
from msgraph_delta_query.client import AsyncDeltaQueryClient

async def get_users() -> List[User]:
    client = AsyncDeltaQueryClient(return_sdk_objects=True)
    users, _, _ = await client.delta_query_all(
        resource="users",
        select=["id", "displayName", "mail"]
    )
    return users  # Type checker knows this is List[User]

# Usage with full type safety
users = await get_users()
for user in users:
    print(f"{user.display_name}: {user.mail}")  # IDE autocomplete works!
```

## Migration Guide

### Existing Code (Dictionaries)
```python
# Old approach
users, _, _ = await client.delta_query_all(resource="users")
name = users[0]["displayName"]  # String key access
email = users[0].get("mail", "")  # Need .get() for safety
```

### New Code (SDK Objects)
```python
# New approach
client = AsyncDeltaQueryClient(return_sdk_objects=True)
users, _, _ = await client.delta_query_all(resource="users")
name = users[0].display_name  # Attribute access with type safety
email = users[0].mail or ""  # Direct attribute access
```

## Backward Compatibility

- Default behavior remains unchanged (returns dictionaries)
- All existing code continues to work without modification
- New feature is opt-in via constructor parameter or convenience method
