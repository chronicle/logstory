# NETWORK_ANALYSIS

## Introduction

Network analysis usecase providing logs for workshops on advanced search capabilities and statistical search for Google Security Operations.

**ID**: NETWORK_ANALYSIS

**Version**: 2.0.0

**Author**: Google Cloud Security

**License**: Apache-2.0

**Tags**: network-analysis, zeek, bro, workshops, ocsf, google-secops

**Created**: 2025-07-26

**Updated**: 2026-11-05

## Environment

**Organization**: cymbal-investments.org

**Scenario Type**: workshop

## Run Frequency

**Events**: Every 1 day

## Events

| Stream ID | Log Type | Product Name | Vendor Name | OCSF Class | Notes |
|-----------|----------|--------------|-------------|------------|-------|
| zeek_conn | BRO_JSON | Bro | Zeek | Network Activity (4001) | Zeek JSON network connection logs for statistical and investigative search workshops. |

## Entities

No entities configured for this usecase.

## Rules

| Rule Name | Live | Alerting | Notes |
|-----------|------|----------|-------|
| network_analysis | False | False | Detects network connection events that exceed statistical byte transfer thresholds. |

## Saved Searches

| Search Name | Creator | Notes |
|-------------|---------|-------|
| Zeek_Investigative_Search | jstoner@google.com | Advanced Search Workshop - Search Templates Exercise |

## Platform Bindings

### Google SecOps

- `zeek_conn`: `BRO_JSON`

### Databricks

- **Catalog**: `security_lakehouse`
- **Schema**: `ocsf_silver`
- `zeek_conn`: `secops_ocsf.network_activity`

### Splunk

- `zeek_conn`: `zeek:conn:json`

---

*This document was generated from YAML frontmatter using the usecase template.*