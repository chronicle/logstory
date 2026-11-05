---
schema_version: "2.0"
id: NETWORK_ANALYSIS
title: NETWORK_ANALYSIS
version: "2.0.0"
created: "2025-07-26"
updated: "2026-11-05"
author: Google Cloud Security
license: Apache-2.0
description: Network analysis usecase providing logs for workshops on advanced search capabilities and statistical search for Google Security Operations.
tags:
  - network-analysis
  - zeek
  - bro
  - workshops
  - ocsf
  - google-secops
environment:
  organization: cymbal-investments.org
  scenario_type: workshop
  paired_baselines: []
  timestamp_policy:
    base_date: "2025-07-26"
    preserve_relative_offsets: true
    default_delta: 1d
    entity_offset_days: 1
telemetry:
  events:
    - stream_id: zeek_conn
      path: EVENTS/BRO_JSON.log
      log_type: BRO_JSON
      vendor_name: Zeek
      product_name: Bro
      ocsf_category_uid: 4
      ocsf_class_uid: 4001
      ocsf_class_name: Network Activity
      notes: "Zeek JSON network connection logs for statistical and investigative search workshops."
  entities: []
platforms:
  google_secops:
    run_frequency:
      events: "Every 1 day"
    log_type_mappings:
      zeek_conn: BRO_JSON
    detections:
      - name: network_analysis
        path: RULES/network_analysis.yl2
        live: false
        alerting: false
        notes: "Detects network connection events that exceed statistical byte transfer thresholds."
    saved_searches:
      - name: Zeek_Investigative_Search
        creator: jstoner@google.com
        notes: "Advanced Search Workshop - Search Templates Exercise"
    reference_lists: []
  databricks:
    catalog: security_lakehouse
    schema_name: ocsf_silver
    table_mappings:
      zeek_conn: secops_ocsf.network_activity
    detections: []
  splunk:
    sourcetypes:
      zeek_conn: "zeek:conn:json"
---

# NETWORK_ANALYSIS

## Introduction

This usecase provides logs for workshops:
 1. Advanced Search Capabilities
 2. Statistical Search for Google Security Operations

## Events

| Stream ID | Log Type | Product Name | Vendor Name | OCSF Class | Notes |
|-----------|----------|--------------|-------------|------------|-------|
| zeek_conn | BRO_JSON | Bro | Zeek | Network Activity (4001) | Zeek JSON network connection logs for statistical and investigative search workshops. |

## Entities

No entities configured for this usecase.

<!-- BEGIN_SOLUTION -->

## Rules

| Rule Name         | Live  | Alerting | Notes |
|-------------------|-------|----------|-------|
| network_analysis  | False | False    | Detects network connection events that exceed statistical byte transfer thresholds. |

## Saved Searches

| Search Name                 | Creator             | Notes |
|-----------------------------|---------------------|-------|
| Zeek_Investigative_Search   | jstoner@google.com  | Advanced Search Workshop - Search Templates Exercise |

## Reference Lists

No reference lists configured for this usecase.
