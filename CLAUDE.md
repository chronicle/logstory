# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LogStory is a Python tool for replaying security telemetry (logs) into Google Security Operations (SecOps) tenants with updated timestamps. It organizes security scenarios as "usecases" that tell information security stories.

## Development Commands

### Build and Package
```bash
# Build Python package (creates dist/ with wheel and tarball)
make build

# Clean build artifacts
make clean

# Clean and rebuild
make rebuild

# Publish to Test PyPI
twine upload --repository testpypi dist/*

# Publish to PyPI (production)
twine upload dist/*
```

### Documentation
```bash
# Build and serve live documentation locally
cd docs/
make livehtml
# View at http://localhost:8000
```

### Testing
```bash
# Run tests (minimal test coverage currently)
python -m pytest tests/
```

### Running LogStory
```bash
# Basic usage with flagfile
logstory usecase_replay RULES_SEARCH_WORKSHOP --flagfile=config.cfg

# List available usecases
logstory usecases_list

# Download a usecase from GCS
logstory usecase_get EDR_WORKSHOP

# Run with specific timestamp delta
logstory usecase_replay RULES_SEARCH_WORKSHOP \
  --customer_id=<uuid> \
  --credentials_path=<path> \
  --timestamp_delta=1d
```

## High-Level Architecture

### Core Components

1. **CLI Interface** (`src/logstory/logstory.py`)
   - Uses Google's Abseil library for flag-based CLI
   - Entry point: `logstory.logstory:entry_point`
   - Main subcommands: `usecase_replay`, `usecase_replay_logtype`, `usecases_list`, `usecase_get`

2. **Timestamp Management**
   - Updates timestamps while preserving relative time differences
   - Base timestamp (BTS) calculation for each usecase
   - Supports delta options: days (`Nd`), hours (`Nh`), minutes (`Nm`)

3. **Usecase Structure**
   - Located in `src/logstory/usecases/` (when installed via pip)
   - Each usecase contains:
     - `EVENTS/` - Security log files
     - `ENTITIES/` - Contextual information (optional)
     - `RULES/` - YARA-L 2.0 detection rules (optional)
     - `*.md` - Documentation for the usecase

4. **Google SecOps Integration**
   - Uses Google Security Operations Ingestion API (not the newer RESTful v1alpha yet)
   - Requires customer UUID and ingestion API credentials
   - Handles both events and entities ingestion

5. **Cloud Functions** (`cloudfunctions/`)
   - Terraform-managed Google Cloud Functions for:
     - Entity processing (24h and 3-day variants)
     - Event processing (24h and 3-day variants)
     - Rule creation
   - Each function has its own requirements.txt and main.py

### Key Files and Their Purposes

- `pyproject.toml` - Modern Python packaging configuration
- `logtypes_entities_timestamps.yaml` - Entity timestamp field mappings
- `logtypes_events_timestamps.yaml` - Event timestamp field mappings
- `usecases_entities_logtype_map.yaml` - Usecase to entity logtype mappings
- `usecases_events_logtype_map.yaml` - Usecase to event logtype mappings

### Publishing Usecases

Usecases can be published to Google Cloud Storage:
```bash
gsutil rsync -r /path/to/usecase gs://logstory-usecases-20241216/USECASE_NAME
```

## Important Notes

- Python 3.11+ required
- Uses setuptools>=61.0 with wheel for packaging
- Documentation uses Sphinx with MyST parser for Markdown
- Follows Google's Open Source Community Guidelines
- Requires Google CLA for contributions