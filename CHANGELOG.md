# Changelog

All notable changes to BigQuery-Lite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure and documentation
- Architecture Decision Records (ADR) framework
- Comprehensive documentation templates

## [0.1.0] - 2024-01-26

### Added
- BigQuery-Lite backend with FastAPI
- React frontend with Monaco Editor integration
- DuckDB and ClickHouse dual engine support
- Docker compose setup for full-stack deployment
- NYC taxi sample dataset for testing
- Real-time query execution with slot-based scheduling
- Interactive query plans and performance metrics
- Schema registry and protobuf ingestion support
- Python CLI tool (bqlite) for backend interaction
- Comprehensive documentation with Docusaurus integration

### Features
- **Dual Analytics Engines**: DuckDB for embedded analytics, ClickHouse for distributed processing
- **Modern Web Interface**: BigQuery-inspired UI with syntax highlighting
- **Slot-Based Scheduling**: Simulates BigQuery's resource allocation system
- **Interactive Query Plans**: Detailed execution analysis and monitoring
- **Real-time Job Management**: Live query status updates
- **Performance Metrics**: Comprehensive execution statistics

### Technical Implementation
- FastAPI backend with async processing
- React 18 frontend with real-time updates
- Monaco Editor for professional SQL editing
- Docker containerization for all services
- Parquet file format support
- RESTful API with comprehensive endpoints

### Documentation
- Complete setup and installation guides
- API reference documentation
- Architecture overview and design principles
- Sample queries and tutorials
- Docker deployment instructions
- CLI tool usage guide

---

## Release Notes Template

For future releases, use this template:

### [Version] - YYYY-MM-DD

#### Added
- New features and functionality

#### Changed
- Changes to existing functionality

#### Deprecated
- Features marked for removal in future versions

#### Removed
- Features removed in this version

#### Fixed
- Bug fixes and corrections

#### Security
- Security-related changes and fixes

---

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

Examples:
- `1.0.0` - First stable release
- `1.1.0` - Added new feature, backwards compatible
- `1.1.1` - Bug fix, backwards compatible
- `2.0.0` - Breaking changes, not backwards compatible