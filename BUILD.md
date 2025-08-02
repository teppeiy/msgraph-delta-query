# Build and Distribution Commands

This file contains the commands needed to build and publish the msgraph-delta-query package.

## Building the Package

### Install build dependencies
```bash
pip install build twine
```

### Build the package
```bash
python -m build
```

This will create both wheel and source distributions in the `dist/` directory.

## Publishing to PyPI

### Test on TestPyPI first (recommended)
```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Install from TestPyPI to test
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ msgraph-delta-query
```

### Publish to PyPI
```bash
python -m twine upload dist/*
```

## Development Installation

### Install in development mode
```bash
pip install -e .
```

### Install with development dependencies
```bash
pip install -e ".[dev]"
```

## Testing

### Run tests
```bash
pytest
```

### Run tests with coverage
```bash
pytest --cov=delta_query --cov-report=html
```

## Code Quality

### Format code
```bash
black src/ tests/ examples/
```

### Check types
```bash
mypy src/
```

### Lint code
```bash
flake8 src/ tests/
```

## Clean Build Artifacts

```bash
# Remove build artifacts
Remove-Item -Recurse -Force build, dist, *.egg-info
```
