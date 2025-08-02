# Examples

This directory contains practical examples showing how to use the Microsoft Graph Delta Query library.

## Overview

Each example demonstrates a specific real-world usage pattern. Examples are designed to be:

- **Simple**: No complex configuration switching - just run and get data
- **Focused**: Each example has a clear, single purpose
- **Production-ready**: Demonstrate best practices and error handling
- **Real-world**: Based on actual usage patterns people need

## Quick Start

1. **Install dependencies**: Ensure you have the library installed
2. **Set up authentication**: Configure Azure AD app registration and environment variables  
3. **Choose your example**: Pick the pattern that matches your needs
4. **Run**: They work out of the box with minimal setup

## Available Examples

### `users_localfile_sync.py`

**Purpose**: Get user data with local file storage  
**Best for**: Development, testing, simple scripts  
**What it does**: Runs delta query, stores delta links locally, shows you the data  
**Storage**: Uses local `deltalinks/` folder

```bash
python examples/users_localfile_sync.py
```

### `applications_localfile_sync.py`

**Purpose**: Sync application registrations from Microsoft Graph  
**Best for**: Security auditing, application inventory  
**What it does**: Retrieves all application registrations with their key properties  
**Storage**: Uses local `deltalinks/` folder

```bash
python examples/applications_localfile_sync.py
```

### `serviceprincipals_localfile_sync.py`

**Purpose**: Sync service principals (app instances) from Microsoft Graph  
**Best for**: Security monitoring, compliance reporting  
**What it does**: Retrieves all service principals with their configuration  
**Storage**: Uses local `deltalinks/` folder

```bash
python examples/serviceprincipals_localfile_sync.py
```

### `sdk_objects_example.py`

**Purpose**: Demonstrates how to use SDK objects with proper typing  
**Best for**: Learning best practices, understanding type casting  
**What it does**: Shows how to cast dict responses to SDK objects for better IDE support  
**Features**: Type hints, dot notation access, IDE autocomplete

```bash
python examples/sdk_objects_example.py
```
python examples/sdk_objects_example.py
```

### `users_azureblob_sync.py`

**Purpose**: Get user data with Azure Blob Storage  
**Best for**: Production deployments, cloud services, multi-instance scenarios  
**What it does**: Runs delta query, stores delta links in Azure Blob, shows you the data  
**Storage**: Uses Azure Blob Storage container

```bash
python examples/users_azureblob_sync.py
```

### `periodic_sync.py`

**Purpose**: Continuous background synchronization with configurable resource types  
**Best for**: Services that need to stay up-to-date automatically, comprehensive tenant sync  
**What it does**: Runs periodic syncs, graceful shutdown, progress reporting. Supports users, applications, service principals, and groups  
**Storage**: Uses Azure Blob Storage by default (with Azurite fallback for development)

```bash
# Sync applications (default)
python examples/periodic_sync.py

# Sync users instead
python examples/periodic_sync.py --resource-type users

# Sync service principals  
python examples/periodic_sync.py --resource-type service_principals

# Sync groups (if your app has permission)
python examples/periodic_sync.py --resource-type groups
```

## Authentication Setup

All examples require Microsoft Graph authentication. Set up your environment:

1. **Register Azure AD application** with `User.Read.All` permission
2. **Set environment variables**:

   ```bash
   # Required for all examples
   AZURE_CLIENT_ID=your-app-id
   AZURE_CLIENT_SECRET=your-app-secret  
   AZURE_TENANT_ID=your-tenant-id
   
   # Required for Azure Blob Storage examples
   AZURE_STORAGE_CONNECTION_STRING=your-connection-string
   ```

## SDK Object Usage

All examples demonstrate modern SDK object usage patterns. The library returns dict objects from Microsoft Graph, but you can cast them to SDK objects for better IDE support:

```python
from typing import cast, List
from msgraph.generated.models.user import User

# Get data from the library
users_data, delta_link, metadata = await client.delta_query_all("users", select=["id", "displayName"])

# Cast to SDK objects for better IDE support
users = cast(List[User], users_data)

# Use dot notation with full IDE autocomplete
for user in users:
    print(f"User: {user.display_name}")
```

**Benefits of SDK object casting:**

- ✅ IDE autocomplete and type checking
- ✅ Clean dot notation access (`user.display_name`)
- ✅ Better code readability
- ✅ Compile-time error detection

## Storage Backends

### Local File Storage (`users_localfile_sync.py`)

- **Location**: `deltalinks/` directory
- **Benefits**: Simple setup, no external dependencies
- **Use when**: Development, testing, single-machine deployments

### Azure Blob Storage (`users_azureblob_sync.py`)

- **Location**: Azure Blob Storage container
- **Benefits**: Cloud persistence, multi-instance support, production-ready
- **Use when**: Production deployments, cloud services, scalable applications

## Next Steps

1. **Start with** `users_localfile_sync.py` to understand the basics
2. **Move to** `users_azureblob_sync.py` for production scenarios  
3. **Use** `periodic_sync.py` for continuous synchronization services

Each example is self-contained and demonstrates a complete workflow from authentication to data retrieval to storage management.
