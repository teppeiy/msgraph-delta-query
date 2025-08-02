# Publishing Guide for msgraph-delta-query

This guide walks you through publishing your `msgraph-delta-query` package to PyPI.

## Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/
2. **TestPyPI Account**: Create an account at https://test.pypi.org/ (for testing)
3. **API Tokens**: Generate API tokens for both PyPI and TestPyPI for secure authentication

## Step-by-Step Publishing Process

### 1. Prepare Your Package

Ensure your package is ready:
```bash
# Install build tools
pip install build twine

# Clean previous builds
Remove-Item -Recurse -Force build, dist, *.egg-info

# Build the package
python -m build
```

### 2. Test on TestPyPI First

**Always test on TestPyPI before publishing to the main PyPI!**

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ msgraph-delta-query

# Test your package
python -c "from msgraph_delta_query import AsyncDeltaQueryClient; print('Success!')"
```

### 3. Publish to PyPI

Once testing is successful:

```bash
# Upload to PyPI
python -m twine upload dist/*
```

### 4. Verify Installation

```bash
# Install from PyPI
pip install msgraph-delta-query

# Test
python -c "from msgraph_delta_query import AsyncDeltaQueryClient; print('Package works!')"
```

## Security Best Practices

### Using API Tokens (Recommended)

1. **Generate API Tokens**:
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/

2. **Configure `.pypirc`** in your home directory:
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-your-api-token-here

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-your-test-api-token-here
   ```

### Environment Variables (Alternative)

```bash
# Set environment variables
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-your-api-token-here"

# Upload
python -m twine upload dist/*
```

## Version Management

Update version in `pyproject.toml` before each release:

```toml
[project]
version = "0.1.1"  # Increment as needed
```

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Pre-publication Checklist

- [ ] All tests pass
- [ ] Version number updated
- [ ] README.md is up to date
- [ ] CHANGELOG updated (if you have one)
- [ ] Dependencies are correctly specified
- [ ] Package builds successfully
- [ ] Tested on TestPyPI
- [ ] All necessary files included in package

## Troubleshooting

### Common Issues:

1. **Package name already exists**: Choose a different name
2. **Version already exists**: Increment version number
3. **Authentication failed**: Check API tokens
4. **Missing dependencies**: Update `pyproject.toml` dependencies

### Useful Commands:

```bash
# Check package contents
python -m twine check dist/*

# View package info
pip show msgraph-delta-query

# Uninstall for testing
pip uninstall msgraph-delta-query
```

## Automation (Optional)

Consider setting up GitHub Actions for automated publishing:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

Remember to add your PyPI API token as a GitHub secret named `PYPI_API_TOKEN`.
