---
title: NETWORK_ANALYSIS
description: Network analysis usecase providing logs for workshops on advanced search capabilities and statistical search for Google SecOps
tags:
  - network-analysis
  - zeek
  - bro
  - workshops
created: 2025-07-26
updated: 2025-07-26
events:
  - log_type: BRO_JSON
    product_name: Bro
    vendor_name: Zeek
    notes: ""
entities:
  - log_type: N/A
    product_name: ""
    vendor_name: ""
    notes: ""
rules:
  - name: network_analysis
    live: false
    alerting: false
    notes: ""
saved_searches:
  - name: Zeek_Investigative_Search
    creator: jstoner@google.com
    notes: ""
reference_lists:
  - name: N/A
    type: ""
    notes: ""
---

# NETWORK_ANALYSIS

## Introduction

This usecase provides logs for workshops:
 1. Advanced Search Capabilities
 1. Statistical Search for Google SecOps

## Events

| Log Type     | Product Name | Vendor Name | Notes |
|--------------|--------------|-------------|-------|
| BRO_JSON     | Bro          | Zeek        |       |

## Entities

| Log Type | Product Name | Vendor Name | Notes |
|----------|--------------|-------------|-------|
| N/A      |              |             |       |

## Rules

| Rule Name         | Live  | Alerting | Notes |
|-------------------|-------|----------|-------|
| network_analysis  | False | False    |       |

## Saved Searches

| Search Name                 | Creator             | Notes |
|-----------------------------|---------------------|-------|
| Zeek_Investigative_Search.  | j-stoner@users.noreply.github.com  |       |

## Reference Lists

| Reference List | Type   | Notes |
|----------------|--------|-------|
| N/A            |        |       |
