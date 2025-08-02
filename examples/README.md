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

### `simple_local_sync.py`

**Purpose**: Get user data with local file storage  
**Best for**: Development, testing, simple scripts  
**What it does**: Runs delta query, stores delta links locally, shows you the data  
**Storage**: Uses local `deltalinks/` folder

```bash
python examples/simple_local_sync.py
```

### `simple_azure_sync.py`

**Purpose**: Get user data with Azure Blob Storage  
**Best for**: Production deployments, cloud services, multi-instance scenarios  
**What it does**: Runs delta query, stores delta links in Azure Blob, shows you the data  
**Storage**: Uses Azure Blob Storage container

```bash
python examples/simple_azure_sync.py
```

### `periodic_sync.py`

**Purpose**: Continuous background synchronization  
**Best for**: Services that need to stay up-to-date automatically  
**What it does**: Runs periodic syncs, graceful shutdown, progress reporting  
**Storage**: Auto-detects your storage configuration

```bash
python examples/periodic_sync.py
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

## Storage Backends

### Local File Storage (`simple_local_sync.py`)

- **Location**: `deltalinks/` directory
- **Benefits**: Simple setup, no external dependencies
- **Use when**: Development, testing, single-machine deployments

### Azure Blob Storage (`simple_azure_sync.py`)

- **Location**: Azure Blob Storage container
- **Benefits**: Cloud persistence, multi-instance support, production-ready
- **Use when**: Production deployments, cloud services, scalable applications

## Next Steps

1. **Start with** `simple_local_sync.py` to understand the basics
2. **Move to** `simple_azure_sync.py` for production scenarios  
3. **Use** `periodic_sync.py` for continuous synchronization services

Each example is self-contained and demonstrates a complete workflow from authentication to data retrieval to storage management.
