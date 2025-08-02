# Library Quality Tests

This directory contains the core test suite that ensures the quality and reliability of the msgraph-delta-query library.

## Purpose

These tests **MUST PASS** for every library release and are run automatically in CI/CD pipelines.

## Test Categories

### Core Functionality Tests

- `test_client.py` - AsyncDeltaQueryClient core functionality
- `test_models.py` - Data models and change summaries
- `test_storage.py` - Storage implementations (local file, Azure blob)

### Integration Tests

- `test_integration.py` - Real Microsoft Graph API integration
- `test_examples.py` - Example code validation

### Edge Case and Error Handling

- `test_invalid_delta_links.py` - Invalid delta link fallback behavior
- `test_comprehensive_delta_handling.py` - Comprehensive error scenarios

### Package and API Tests

- `test_init.py` - Package initialization and exports

## Running Tests

```bash
# Run all quality tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/msgraph_delta_query

# Run specific test file
pytest tests/test_client.py
```

## Test Requirements

All tests in this directory must:

- Pass consistently across different environments
- Not require manual setup or external resources (beyond env vars)
- Execute quickly (< 5 minutes total)
- Have clear assertions and error messages
- Follow pytest conventions

## vs. Research Tests

For exploratory testing, behavior studies, and verification scripts, see `/src/research/`.
Those tests don't need to pass for releases and are used for development and investigation.
