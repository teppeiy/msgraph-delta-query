# Azure Blob Storage for Delta Link Persistence

This guide explains how to configure Azure Blob Storage specifically for persisting Microsoft Graph delta links between application runs.

## Purpose

The `AzureBlobDeltaLinkStorage` class is designed to store **delta links only** - not user data. Delta links are small JSON files that contain:

- The Microsoft Graph delta token/URL for incremental sync
- Metadata about the last sync (timestamp, resource info)
- This enables efficient incremental queries instead of full data pulls

**What it stores**: Delta links and sync metadata (small JSON files)
**What it does NOT store**: Actual Microsoft Graph data (users, groups, etc.)

## Installation

Install the library with Azure support:

```bash
pip install msgraph-delta-query[azure]
```

## Configuration Options

The `AzureBlobDeltaLinkStorage` class supports multiple configuration methods:

### 1. Auto-Detection (Recommended)

```python
from msgraph_delta_query import AzureBlobDeltaLinkStorage

# Auto-detects configuration from environment
storage = AzureBlobDeltaLinkStorage(
    container_name="deltalinks"  # Optional: defaults to "deltalinks"
)
```

The auto-detection process checks in this order:

1. Environment variables (`AZURE_STORAGE_CONNECTION_STRING` or `AzureWebJobsStorage`)
2. Managed identity with environment-based account URL
3. Fallback to `DefaultAzureCredential` with account URL detection

### 2. Connection String (Local Development)

```python
storage = AzureBlobDeltaLinkStorage(
    connection_string="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=key;EndpointSuffix=core.windows.net"
)
```

### 3. Managed Identity (Production)

```python
storage = AzureBlobDeltaLinkStorage(
    account_url="https://mystorageaccount.blob.core.windows.net"
    # Uses DefaultAzureCredential for managed identity
)
```

### 4. Custom Credential

```python
from azure.identity.aio import ManagedIdentityCredential

credential = ManagedIdentityCredential(client_id="your-client-id")
storage = AzureBlobDeltaLinkStorage(
    account_url="https://mystorageaccount.blob.core.windows.net",
    credential=credential
)
```

## Environment Setup

### Azure Functions Production

1. **Enable Managed Identity** on your Function App
2. **Grant permissions** to the storage account:
   ```bash
   # Get the Function App's managed identity principal ID
   az functionapp identity show --name <function-app-name> --resource-group <rg-name> --query principalId -o tsv
   
   # Assign Storage Blob Data Contributor role
   az role assignment create \
     --assignee <principal-id> \
     --role "Storage Blob Data Contributor" \
     --scope "/subscriptions/<subscription-id>/resourceGroups/<rg-name>/providers/Microsoft.Storage/storageAccounts/<storage-name>"
   ```

3. **Set environment variables** in Function App settings:
   ```
   AZURE_STORAGE_ACCOUNT_NAME=mystorageaccount
   ```

### Azure Functions Local Development

1. **Create `local.settings.json`**:
   ```json
   {
     "IsEncrypted": false,
     "Values": {
       "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=mystorageaccount;AccountKey=...",
       "FUNCTIONS_WORKER_RUNTIME": "python",
       "AZURE_CLIENT_ID": "your-app-registration-id",
       "AZURE_TENANT_ID": "your-tenant-id",
       "AZURE_CLIENT_SECRET": "your-client-secret"
     }
   }
   ```

2. **Or use Azurite** (Azure Storage Emulator):
   ```bash
   npm install -g azurite
   azurite --silent --location c:\azurite --debug c:\azurite\debug.log
   ```
   
   Then in `local.settings.json`:
   ```json
   {
     "Values": {
       "AzureWebJobsStorage": "UseDevelopmentStorage=true"
     }
   }
   ```

### Local Development (Non-Azure Functions)

1. **Option A: Environment Variables**
   ```bash
   set AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."
   # or
   set AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
   ```

2. **Option B: Azure CLI Authentication**
   ```bash
   az login
   set AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
   ```

3. **Option C: Service Principal**
   ```bash
   set AZURE_CLIENT_ID="your-app-id"
   set AZURE_TENANT_ID="your-tenant-id"
   set AZURE_CLIENT_SECRET="your-secret"
   set AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
   ```

## Usage Examples

### Basic Usage

```python
import asyncio
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage

async def sync_with_blob_storage():
    # Create storage (auto-detects configuration)
    storage = AzureBlobDeltaLinkStorage(
        container_name="msgraph-deltalinks"
    )
    
    # Create client
    client = AsyncDeltaQueryClient(delta_link_storage=storage)
    
    try:
        # Run delta query
        users, delta_link, metadata = await client.delta_query(
            resource="users",
            select=["id", "displayName", "mail"]
        )
        
        print(f"Synced {len(users)} users")
        print(f"Change summary: {metadata.change_summary}")
        
    finally:
        # Clean up
        await storage.close()
        await client._internal_close()

# Run the sync
asyncio.run(sync_with_blob_storage())
```

### Azure Function Integration

```python
import azure.functions as func
from msgraph_delta_query import AsyncDeltaQueryClient, AzureBlobDeltaLinkStorage

async def main(mytimer: func.TimerRequest) -> None:
    """Timer-triggered Azure Function."""
    
    # Storage automatically configured from Function App settings
    storage = AzureBlobDeltaLinkStorage()
    client = AsyncDeltaQueryClient(delta_link_storage=storage)
    
    try:
        users, _, metadata = await client.delta_query(
            resource="users",
            select=["id", "displayName", "mail"],
            top=1000
        )
        
        logging.info(f"Processed {len(users)} users in {metadata.duration_seconds:.2f}s")
        
    finally:
        await storage.close()
        await client._internal_close()
```

## Container and Blob Structure

The Azure Blob Storage implementation creates:

- **Container**: `deltalinks` (or custom name)
- **Blobs**: `{resource_name}.json` (e.g., `users.json`, `groups.json`)

Each blob contains:
```json
{
  "delta_link": "https://graph.microsoft.com/v1.0/users/delta?$skiptoken=...",
  "last_updated": "2025-08-01T10:30:00.000Z",
  "resource": "users",
  "metadata": {}
}
```

## Error Handling

The implementation includes robust error handling:

- **Missing dependencies**: Clear error message with installation instructions
- **Authentication failures**: Detailed logging for credential issues
- **Storage errors**: Graceful fallback with warning logs
- **Container creation**: Automatic container creation if it doesn't exist

## Security Best Practices

1. **Use Managed Identity** in production (no secrets in code)
2. **Least privilege**: Grant only "Storage Blob Data Contributor" role
3. **Network security**: Use private endpoints if needed
4. **Monitoring**: Enable storage analytics and monitoring

## Troubleshooting

### Common Issues

1. **"Import could not be resolved"**
   ```bash
   pip install azure-storage-blob azure-identity
   ```

2. **"Authentication failed"**
   - Check managed identity is enabled
   - Verify role assignments
   - Ensure correct environment variables

3. **"Container not found"**
   - Container is created automatically
   - Check storage account permissions

4. **"Connection string invalid"**
   - Verify connection string format
   - Check account name and key

### Debug Logging

Enable debug logging to troubleshoot:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Reduce Azure SDK noise
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
```

## Performance Considerations

- **Container reuse**: Container existence is checked once per client instance
- **Connection pooling**: BlobServiceClient handles connection pooling automatically
- **Blob caching**: Delta links are small JSON files, minimal performance impact
- **Concurrent access**: Thread-safe for multiple Azure Function instances
