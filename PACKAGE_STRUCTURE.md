# Microsoft Graph Delta Query Package Structure

This document describes the complete structure of the msgraph-delta-query PyPI package.

## Package Structure

```
msgraph-delta-query/
├── src/
│   └── msgraph_delta_query/
│       ├── __init__.py          # Package initialization and exports
│       ├── client.py            # Main AsyncDeltaQueryClient class
│       └── storage.py           # Storage backends for delta links
├── tests/
│   ├── __init__.py              # Test package initialization
│   └── test_storage.py          # Tests for storage backends
├── examples/
│   └── basic_usage.py           # Usage examples
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

### `src/msgraph_delta_query/storage.py`
- Abstract base class `DeltaLinkStorage`
- `LocalFileDeltaLinkStorage` implementation
- Stores delta links in local JSON files

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
    
    users, delta_link, metadata = await client.delta_query_all(
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
