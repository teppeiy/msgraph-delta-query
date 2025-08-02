#!/usr/bin/env python3
"""
Test runner script for msgraph-delta-query package.

This script runs the complete test suite with coverage reporting.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"❌ {description} failed with return code {result.returncode}")
        return False
    else:
        print(f"✅ {description} completed successfully")
        return True


def main():
    """Run the complete test suite."""
    print("🚀 Starting msgraph-delta-query test suite")
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    success = True
    
    # Install test dependencies
    if not run_command([
        sys.executable, "-m", "pip", "install", "-e", ".[dev]"
    ], "Installing package and test dependencies"):
        success = False
    
    # Run pytest with coverage
    if not run_command([
        sys.executable, "-m", "pytest", 
        "tests/",
        "--cov=src/msgraph_delta_query",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "--cov-fail-under=95",
        "-v"
    ], "Running pytest with coverage"):
        success = False
    
    # Run type checking with mypy
    if not run_command([
        sys.executable, "-m", "mypy", "src/msgraph_delta_query"
    ], "Running mypy type checking"):
        print("⚠️  mypy failed, but continuing...")
        # Don't fail the entire suite for mypy issues
    
    # Run code formatting check with black
    if not run_command([
        sys.executable, "-m", "black", "--check", "src/", "tests/"
    ], "Checking code formatting with black"):
        print("⚠️  black formatting check failed, but continuing...")
        # Don't fail the entire suite for formatting issues
    
    # Run linting with flake8
    if not run_command([
        sys.executable, "-m", "flake8", "src/", "tests/"
    ], "Running flake8 linting"):
        print("⚠️  flake8 linting failed, but continuing...")
        # Don't fail the entire suite for linting issues
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 All critical tests passed!")
        print("📊 Coverage report generated in htmlcov/index.html")
        print("📋 XML coverage report saved as coverage.xml")
    else:
        print("❌ Some critical tests failed!")
        sys.exit(1)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
