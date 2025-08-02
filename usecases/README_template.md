# Usecase Template System

This directory contains a Jinja2 template system for generating standardized usecase documentation from YAML frontmatter.

## Files

- `usecase_template.j2` - Jinja2 template for generating usecase documentation
- `generate_usecase_docs.py` - Python script for processing templates
- `README_template.md` - This documentation file

## Template Usage

### 1. YAML Frontmatter Structure

The template expects markdown files with YAML frontmatter containing structured data:

```yaml
---
title: MY_USECASE
description: Description of what this usecase provides
tags:
  - tag1
  - tag2
created: 2025-01-01
updated: 2025-01-02
run_frequency:
  events: "Every 3 days"
  entities: "Every 3 days (offset to 1 day before Events)"
data_rbac: "Any special RBAC requirements"
events:
  - log_type: LOG_TYPE.log
    product_name: Product Name
    vendor_name: Vendor Name
    notes: "Any notes"
entities:
  - log_type: LOG_TYPE.log
    product_name: Product Name
    vendor_name: Vendor Name
    notes: "Any notes"
rules:
  - name: rule_name.yaral
    live: true
    alerting: false
    notes: "Rule description"
saved_searches:
  - name: Search Name
    creator: creator@example.com
    notes: "Search description"
reference_lists:
  - name: list_name
    type: String
    notes: "List description"
---
```

### 2. Generate Documentation

Use the Python script to generate documentation:

```bash
# Generate documentation for a single usecase directory
python generate_usecase_docs.py RULES_SEARCH_WORKSHOP/

# Generate documentation for a specific markdown file
python generate_usecase_docs.py RULES_SEARCH_WORKSHOP/RULES_SEARCH_WORKSHOP.md

# Preview output without writing files
python generate_usecase_docs.py RULES_SEARCH_WORKSHOP/ --dry-run

# Use custom template
python generate_usecase_docs.py RULES_SEARCH_WORKSHOP/ --template my_template.j2

# Specify output location
python generate_usecase_docs.py RULES_SEARCH_WORKSHOP/ --output ./generated/
```

### 3. Template Features

The template automatically generates:

- **Header section** with title, description, tags, dates
- **Run frequency** information if provided
- **Data RBAC** notes if specified
- **Events table** from events array
- **Entities table** from entities array
- **Rules table** from rules array
- **Saved Searches table** from saved_searches array
- **Reference Lists table** from reference_lists array

### 4. Conditional Rendering

The template intelligently handles:

- Missing or empty sections (shows "No X configured")
- Optional fields using `| default('')` filter
- Boolean values converted to title case (True/False)
- Empty arrays or placeholder values (N/A entries)

## Requirements

```bash
pip install jinja2 pyyaml
```

## Examples

See the existing usecase files for examples:
- `NETWORK_ANALYSIS/NETWORK_ANALYSIS.md` - Simple example
- `RULES_SEARCH_WORKSHOP/RULES_SEARCH_WORKSHOP.md` - Complex example with all sections

## Customization

To create custom templates:

1. Copy `usecase_template.j2` to a new file
2. Modify the template syntax and structure
3. Use with `--template your_template.j2`

### Available Variables

All YAML frontmatter keys are available as template variables:
- `title` - Usecase title
- `description` - Usecase description
- `tags` - Array of tags
- `created` - Creation date
- `updated` - Last updated date
- `run_frequency` - Object with `events` and `entities` keys
- `data_rbac` - RBAC requirements string
- `events` - Array of event objects
- `entities` - Array of entity objects
- `rules` - Array of rule objects
- `saved_searches` - Array of saved search objects
- `reference_lists` - Array of reference list objects
