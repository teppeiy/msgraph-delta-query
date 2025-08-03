# Microsoft Graph Delta Query Package Structure

This document describes the complete structure of the msgraph-delta-query PyPI package.

## Package Structure

```
msgraph-delta-query/
├── src/                         # Library source code (shipped to PyPI)
│   └── msgraph_delta_query/
│       ├── __init__.py          # Package initialization and exports
│       ├── client.py            # Main AsyncDeltaQueryClient class
│       ├── models.py            # Data models and change summaries
│       └── storage.py           # Storage backends for delta links
├── tests/                       # Library quality tests (not shipped, CI/CD only)
│   ├── README.md                # Test documentation
│   ├── __init__.py              # Test package initialization
│   ├── test_client.py           # AsyncDeltaQueryClient tests
│   ├── test_models.py           # Data model tests
│   ├── test_storage.py          # Storage backend tests
│   ├── test_integration.py      # Microsoft Graph integration tests
│   └── test_examples.py         # Example code validation
├── research/                    # Research and verification tests (not shipped)
│   ├── README.md                # Research test documentation
│   ├── graph_behavior/          # Microsoft Graph API behavior studies
│   ├── storage_verification/    # Storage implementation verification
│   └── client_verification/     # Client behavior verification
├── examples/                    # Usage examples and demos (optionally shipped)
│   ├── basic_usage.py           # Simple usage example
│   ├── change_summary_demo.py   # Change summary features
│   └── periodic_sync.py         # Periodic synchronization pattern
├── pyproject.toml               # Modern Python package configuration
├── README.md                    # Package documentation
├── LICENSE                      # MIT License
├── MANIFEST.in                  # Additional files to include in package
├── .gitignore                   # Git ignore rules
├── BUILD.md                     # Build instructions
└── PUBLISHING.md                # Publishing guide
```

## Key Files Explained

### `src/msgraph_delta_query/__init__.py`
- Package initialization
- Exports main classes: `AsyncDeltaQueryClient`, `DeltaLinkStorage`, `LocalFileDeltaLinkStorage`
- Version information

### `src/msgraph_delta_query/client.py`
- Main `AsyncDeltaQueryClient` class
- Handles Microsoft Graph API delta queries
- Automatic session management
- Concurrent request limiting
- Delta link management integration

### `src/msgraph_delta_query/models.py`

- Data models for change summaries and query results
- Type definitions for API responses
- Utility classes for data processing

### `tests/` (Library Quality Tests)

- Core test suite that must pass for every release
- Run automatically in CI/CD pipelines
- Covers all public APIs and critical functionality
- **Not shipped to PyPI** - development and CI only
- See `/tests/README.md` for detailed test organization

### `research/` (Research and Verification Tests)

- Exploratory tests for understanding system behavior
- Verification scripts for design decisions and external API behavior
- Not required to pass for releases
- **Not shipped to PyPI** - development only
- Organized by research category (graph_behavior, storage_verification, client_verification)
- See `/research/README.md` for detailed organization

### `pyproject.toml`

- Modern Python package configuration
- Dependencies: `aiohttp>=3.8.0`, `azure-identity>=1.12.0`
- Development dependencies for testing and linting
- Build system configuration

## Installation

### From PyPI (when published)
```bash
pip install msgraph-delta-query
```

### Development Installation
```bash
git clone <repository-url>
cd msgraph-delta-query
pip install -e .
```

### With Development Dependencies
```bash
pip install -e ".[dev]"
```

## Usage

```python
import asyncio
from msgraph_delta_query import AsyncDeltaQueryClient

async def main():
    client = AsyncDeltaQueryClient()
    
    users, delta_link, metadata = await client.delta_query(
        resource="users",
        select=["id", "displayName", "mail"],
        top=100
    )
    
    print(f"Retrieved {len(users)} users")

asyncio.run(main())
```

## Features

- **Asynchronous**: Built with aiohttp for high performance
- **Delta Query Support**: Automatic delta link management
- **Flexible Storage**: Pluggable storage backends
- **Azure Integration**: Built-in Azure Identity support
- **Easy to Use**: Simple API with automatic session management
- **Concurrent Requests**: Configurable rate limiting

## Dependencies

### Runtime Dependencies
- `aiohttp>=3.8.0` - Async HTTP client
- `azure-identity>=1.12.0` - Azure authentication

### Development Dependencies
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support
- `black>=22.0.0` - Code formatting
- `flake8>=4.0.0` - Linting
- `mypy>=0.950` - Type checking

## Building and Publishing

### Build Package
```bash
python -m build
```

### Test on TestPyPI
```bash
python -m twine upload --repository testpypi dist/*
```

### Publish to PyPI
```bash
python -m twine upload dist/*
```

## License

MIT License - see LICENSE file for details.

## Project Status

- Version: 0.1.0
- Status: Alpha
- Python Support: 3.8+
- Platform: Cross-platform (Windows, macOS, Linux)
