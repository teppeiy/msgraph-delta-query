"""Setup script for delta-query package."""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
readme_path = os.path.join(this_directory, "README.md")

try:
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "A Python library for efficiently querying Microsoft Graph API using delta queries."

setup(
    name="delta-query",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python library for efficiently querying Microsoft Graph API using delta queries",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/delta-query",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "azure-identity>=1.12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ]
    },
    keywords="microsoft graph api delta query async aiohttp azure",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/delta-query/issues",
        "Source": "https://github.com/yourusername/delta-query",
        "Documentation": "https://github.com/yourusername/delta-query#readme",
    },
)
