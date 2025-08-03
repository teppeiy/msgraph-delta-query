# Microsoft Graph Delta Query Client

A Python library for efficiently querying Microsoft Graph API using delta queries with automatic delta link management and asynchronous support.

## Features

- 🚀 **Asynchronous**: Built with `aiohttp` for high-performance async operations
- 🔄 **Delta Query Support**: Automatic delta link management for incremental data synchronization
- 💾 **Flexible Storage**: Pluggable storage backends for delta links (local file system included)
- 🛡️ **Azure Integration**: Built-in support for Azure Identity authentication
- 🔧 **Easy to Use**: Simple API with automatic session management
- ⚡ **Concurrent Requests**: Configurable rate limiting and concurrent request handling

## Installation

```bash
pip install msgraph-delta-query
```

## Quick Start

```python
import asyncio
from msgraph_delta_query import AsyncDeltaQueryClient

async def main():
    # Simple instantiation - everything handled internally
    client = AsyncDeltaQueryClient()
    
    # Query users with delta support
    users, delta_link, metadata = await client.delta_query(
        resource="users",
        select=["id", "displayName", "mail"],
        top=100
    )
    
    print(f"Retrieved {len(users)} users in {metadata['duration_seconds']:.2f}s")
    # No need to close anything - handled automatically

if __name__ == "__main__":
    asyncio.run(main())
```

## Advanced Usage

### Custom Delta Link Storage

```python
from msgraph_delta_query import AsyncDeltaQueryClient, DeltaLinkStorage

class CustomDeltaLinkStorage(DeltaLinkStorage):
    async def get(self, resource: str) -> Optional[str]:
        # Your custom storage logic
        pass
    
    async def set(self, resource: str, delta_link: str, metadata: Optional[Dict] = None):
        # Your custom storage logic
        pass
    
    async def delete(self, resource: str):
        # Your custom storage logic
        pass

# Use custom storage
client = AsyncDeltaQueryClient(delta_link_storage=CustomDeltaLinkStorage())
```

### Custom Authentication

```python
from azure.identity.aio import ClientSecretCredential
from msgraph_delta_query import AsyncDeltaQueryClient

credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-client-id", 
    client_secret="your-client-secret"
)

client = AsyncDeltaQueryClient(credential=credential)
```

### Batch Processing

```python
async def process_all_users():
    client = AsyncDeltaQueryClient()
    
    async for batch in client.delta_query_batches(
        resource="users",
        select=["id", "displayName", "mail"],
        batch_size=100
    ):
        users, delta_link, metadata = batch
        print(f"Processing batch of {len(users)} users")
        # Process your batch here
```

## API Reference

### AsyncDeltaQueryClient

The main client class for performing delta queries against Microsoft Graph API.

#### Constructor Parameters

- `credential` (Optional[DefaultAzureCredential]): Azure credential for authentication
- `delta_link_storage` (Optional[DeltaLinkStorage]): Storage backend for delta links
- `timeout` (Optional[aiohttp.ClientTimeout]): HTTP client timeout configuration
- `max_concurrent_requests` (int): Maximum number of concurrent requests (default: 10)

#### Methods

##### `delta_query(resource, **params)`

Performs a complete delta query and returns all results.

**Parameters:**
- `resource` (str): The Graph API resource to query (e.g., "users", "groups")
- `**params`: Additional query parameters (select, filter, top, etc.)

**Returns:**
- `Tuple[List[Dict], Optional[str], Dict]`: (data, delta_link, metadata)

##### `delta_query_batches(resource, batch_size=100, **params)`

Returns an async generator that yields batches of results.

**Parameters:**
- `resource` (str): The Graph API resource to query
- `batch_size` (int): Number of items per batch
- `**params`: Additional query parameters

**Yields:**
- `Tuple[List[Dict], Optional[str], Dict]`: (batch_data, delta_link, metadata)

### Storage Backends

#### LocalFileDeltaLinkStorage

Default storage backend that saves delta links to local JSON files.

```python
from msgraph_delta_query import LocalFileDeltaLinkStorage

storage = LocalFileDeltaLinkStorage(folder="my_deltalinks")
```

## Requirements

- Python 3.8+
- aiohttp>=3.8.0
- azure-identity>=1.12.0

## Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/msgraph-delta-query.git
cd msgraph-delta-query
pip install -e ".[dev]"
```

### Running Tests

#### Library Quality Tests

These tests must pass for every release and are run in CI/CD:

```bash
# Run all quality tests
pytest tests/

# With coverage
pytest tests/ --cov=src/msgraph_delta_query
```

#### Research and Verification Tests

These are exploratory tests for understanding behavior and validating design decisions:

```bash
# Run specific research tests
python -m research.graph_behavior.delta_link_behavior_study
python -m research.storage_verification.azure_blob_priority_verification

# Or run from their directories
cd research/graph_behavior && python delta_link_behavior_study.py
```

See `/tests/README.md` and `/research/README.md` for more details on test organization.

### Code Formatting

```bash
black src/ tests/
```

### Type Checking

```bash
mypy src/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Changelog

### 0.1.0 (2025-08-01)

- Initial release
- Basic delta query functionality
- Local file storage backend
- Azure Identity integration
- Async/await support
