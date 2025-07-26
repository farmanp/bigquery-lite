#!/usr/bin/env python3
"""Setup script for bqlite CLI tool."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bqlite",
    version="0.1.0",
    author="BigQuery-Lite Team",
    description="CLI tool for BigQuery-Lite backend operations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
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
    ],
    python_requires=">=3.8",
    install_requires=[
        "typer[all]>=0.9.0",
        "httpx>=0.24.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "bqlite=bqlite.cli:app",
        ],
    },
)