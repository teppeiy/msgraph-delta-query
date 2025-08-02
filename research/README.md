# Research and Verification Tests

This directory contains research, verification, and behavior study tests that don't need to run with every library change but are valuable for understanding system behavior and validating design decisions.

## Directory Structure

### `/graph_behavior/`
Research into Microsoft Graph API behavior, edge cases, and response patterns.
- `delta_link_behavior_study.py` - Studies how Microsoft Graph handles invalid delta links

### `/storage_verification/` 
Verification tests for storage implementations and configurations.
- `azure_blob_priority_verification.py` - Verifies Azure Blob Storage connection priority order
- `storage_refactoring_verification.py` - Validates storage package refactoring
- `storage_logging_verification.py` - Checks storage source logging functionality
- `check_stored_delta_links.py` - Utility to inspect stored delta links

### `/client_verification/`
Client behavior verification and comprehensive testing.
- `comprehensive_delta_handling_verification.py` - Verifies comprehensive delta link error handling

### Root Research Files
- `comprehensive_system_test.py` - Full system integration testing
- `final_integration_test.py` - Final validation testing

## Purpose

These tests serve different purposes than the main test suite:

1. **Behavior Research**: Understanding how external systems (Microsoft Graph, Azure) behave
2. **Design Validation**: Confirming architectural decisions work as intended  
3. **Edge Case Documentation**: Recording how the system handles unusual scenarios
4. **Integration Verification**: End-to-end testing of complete workflows

## When to Run

- During initial development and design phases
- When investigating issues or edge cases
- When validating major architectural changes
- For documentation and learning purposes

## vs. Library Quality Tests

The main test suite (`/tests/`) contains tests that:
- Must pass for every library release
- Test core functionality and APIs
- Run in CI/CD pipelines
- Ensure backward compatibility

These research tests are more exploratory and don't need to pass for releases.
