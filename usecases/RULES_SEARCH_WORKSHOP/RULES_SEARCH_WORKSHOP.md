---
schema_version: "2.0"
id: RULES_SEARCH_WORKSHOP
title: RULES_SEARCH_WORKSHOP
version: "2.0.0"
created: "2025-07-26"
updated: "2026-11-05"
author: Google Cloud Security
license: Apache-2.0
description: Usecase providing logs for workshops on advanced search capabilities, building rules for Google Security Operations, entity graph exploration, and statistical search.
tags:
  - rules-workshop
  - yara-l
  - google-secops
  - entity-graph
  - advanced-search
  - statistical-search
  - visualization
  - ocsf
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
    - stream_id: powershell
      path: EVENTS/POWERSHELL.log
      log_type: POWERSHELL
      vendor_name: Microsoft
      product_name: PowerShell
      ocsf_category_uid: 1
      ocsf_class_uid: 1007
      ocsf_class_name: Process Activity
      notes: "Windows PowerShell script block and command execution logs."
    - stream_id: windows_defender_av
      path: EVENTS/WINDOWS_DEFENDER_AV.log
      log_type: WINDOWS_DEFENDER_AV
      vendor_name: Microsoft
      product_name: Windows Defender AV
      ocsf_category_uid: 2
      ocsf_class_uid: 2004
      ocsf_class_name: Detection Finding
      notes: "Microsoft Defender Antivirus detection and threat alert telemetry."
    - stream_id: windows_sysmon
      path: EVENTS/WINDOWS_SYSMON.log
      log_type: WINDOWS_SYSMON
      vendor_name: Microsoft
      product_name: Microsoft-Windows-Sysmon
      ocsf_category_uid: 1
      ocsf_class_uid: 1007
      ocsf_class_name: Process Activity
      notes: "Sysmon process creation, file creation, and network telemetry."
    - stream_id: winevtlog
      path: EVENTS/WINEVTLOG.log
      log_type: WINEVTLOG
      vendor_name: Microsoft
      product_name: Microsoft-Windows-Security-Auditing
      ocsf_category_uid: 3
      ocsf_class_uid: 3002
      ocsf_class_name: Authentication
      notes: "Additional product_names in this log type include: Microsoft-Windows-TaskScheduler, SecurityCenter, and Service Control Manager."
  entities:
    - stream_id: windows_ad
      path: ENTITIES/WINDOWS_AD.log
      log_type: WINDOWS_AD
      vendor_name: Microsoft
      product_name: Active Directory
      ocsf_category_uid: 5
      ocsf_class_uid: 5003
      ocsf_class_name: User Inventory
      notes: "Active Directory user and computer entity context for Entity Graph joins."
platforms:
  google_secops:
    run_frequency:
      events: "Every 3 days"
      entities: "Every 3 days (offset to 1 day before Events)"
    data_rbac: "Must be disabled because the entity graph join rules don't work with it on"
    log_type_mappings:
      powershell: POWERSHELL
      windows_defender_av: WINDOWS_DEFENDER_AV
      windows_sysmon: WINDOWS_SYSMON
      winevtlog: WINEVTLOG
      windows_ad: WINDOWS_AD
    parser_extensions:
      - PARSER_EXTENSIONS/WINDOWS_AD.proto
    detections:
      - name: whoami_execution.yaral
        path: null
        live: true
        alerting: false
        notes: "Rule Workshop slide 17"
      - name: mitre_attack_T1021_002_windows_admin_share_basic.yaral
        path: RULES/mitre_attack_T1021_002_windows_admin_share_basic.yl2
        live: false
        alerting: false
        notes: "Rule Workshop slide 22"
      - name: suspicious_unusual_location_lnk_file.yaral
        path: null
        live: false
        alerting: false
        notes: "Rule Workshop slide 27"
      - name: rw_mimikatz_T1003.yaral
        path: RULES/rw_mimikatz_T1003.yl2
        live: true
        alerting: false
        notes: "Rule Workshop slide 29"
      - name: win_password_spray.yaral
        path: RULES/win_password_spray.yl2
        live: false
        alerting: false
        notes: "Rule Workshop slide 44"
      - name: win_repeatedAuthFailure_thenSuccess_T1110_001.yaral
        path: RULES/win_repeatedAuthFailure_thenSuccess.yl2
        live: true
        alerting: true
        notes: "Rule Workshop slide 60"
      - name: mitre_attack_T1021_002_windows_admin_share_with_user_enrichment.yaral
        path: null
        live: false
        alerting: false
        notes: "Rule Workshop slide 50"
      - name: mitre_attack_T1021_002_windows_admin_share_with_user_entity_non_domain_admin.yaral
        path: null
        live: false
        alerting: false
        notes: "Rule Workshop slide 55"
      - name: mitre_attack_T1021_002_windows_admin_share_with_user_entity_domain_admin.yaral
        path: null
        live: false
        alerting: false
        notes: "EG workshop slide 43"
      - name: mitre_attack_T1021_002_windows_admin_share_with_user_entity.yaral
        path: null
        live: false
        alerting: false
        notes: "EG workshop slide 41"
      - name: rw_utilities_associated_with_ntdsdit_T1003_003.yaral
        path: null
        live: false
        alerting: false
        notes: "Rule Workshop slide 75"
      - name: mitre_attack_T1021_002_windows_admin_share_with_asset_entity.yaral
        path: null
        live: false
        alerting: false
        notes: "EG workshop slide 45"
      - name: win_repeatedAuthFailure_thenSuccess_T1110_001_user_asset_entity.yaral
        path: null
        live: false
        alerting: false
        notes: "EG workshop slide 47"
      - name: safebrowsing_hashes_seen_more_than_7_days.yaral
        path: null
        live: false
        alerting: false
        notes: "EG Workshop slide 105 - Works with this usecase as well as MISP and SAFEBROWSING"
      - name: google_safebrowsing_file_process_creation.yaral
        path: null
        live: true
        alerting: true
        notes: "EG Workshop slide 113 - Works with this usecase as well as MISP and SAFEBROWSING"
      - name: google_safebrowsing_with_prevalence.yaral
        path: null
        live: false
        alerting: false
        notes: "EG Workshop slide 115 - Works with this usecase as well as MISP and SAFEBROWSING"
    saved_searches:
      - name: Failed User Logins by Vendor or Product
        creator: Google SecOps Curated
        notes: "Advanced Search Workshop - slide 15 - Also returns data from AZURE_AD and TEMP_ACCOUNT use cases"
    reference_lists:
      - name: key_servers
        type: String
        notes: "Key server names - Used for rules workshop"
      - name: ntds_suspicious_processes
        type: String
        notes: "process names often associated with accessing ntds.dit - Used for rules workshop - Stoner"
  databricks:
    catalog: security_lakehouse
    schema_name: ocsf_silver
    table_mappings:
      powershell: secops_ocsf.process_activity
      windows_defender_av: secops_ocsf.detection_finding
      windows_sysmon: secops_ocsf.process_activity
      winevtlog: secops_ocsf.authentication
      windows_ad: secops_ocsf.user_inventory
    detections: []
  splunk:
    sourcetypes:
      powershell: "XmlWinEventLog:Microsoft-Windows-PowerShell/Operational"
      windows_defender_av: "XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational"
      windows_sysmon: "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational"
      winevtlog: "XmlWinEventLog:Security"
      windows_ad: "ms:ad:user"
---

# RULES_SEARCH_WORKSHOP

## Introduction

This usecase provides logs for the following workshops:
 1. Advanced Search Capabilities
 2. Building Rules for Google Security Operations
 3. Diving Deep into the Entity Graph
 4. Searching with Google Security Operations
 5. Statistical Search with Google Security Operations (Exercise #2)
 6. Visualizing Alerts in Google Security Operations

The "Building Rules for Google Security Operations" workshop focuses on using YARA-L 2.0 to create rules within the Google Security Operations platform. The workshop is hands-on and designed to help participants learn how to build rules for detecting security events. The material covers a range of topics, including YARA-L basics, constructing rules, using entity data, outcomes, functions, and lists. It also covers the rule-building process, from detecting single events to detecting across multiple events. The workshop also emphasizes the importance of testing rules and provides guidance for doing so. It assumes that users will be duplicating or copying rules to test. The workshop also encourages users to start simple and test their rules on existing data, adding additional criteria as needed.

## Events

**Run Frequency**: Every 3 days

| Stream ID | Log Type | Product Name | Vendor Name | OCSF Class | Notes |
|-----------|----------|--------------|-------------|------------|-------|
| powershell | POWERSHELL | PowerShell | Microsoft | Process Activity (1007) | Windows PowerShell script block and command execution logs. |
| windows_defender_av | WINDOWS_DEFENDER_AV | Windows Defender AV | Microsoft | Detection Finding (2004) | Microsoft Defender Antivirus detection and threat alert telemetry. |
| windows_sysmon | WINDOWS_SYSMON | Microsoft-Windows-Sysmon | Microsoft | Process Activity (1007) | Sysmon process creation, file creation, and network telemetry. |
| winevtlog | WINEVTLOG | Microsoft-Windows-Security-Auditing | Microsoft | Authentication (3002) | Additional product_names in this log type include: Microsoft-Windows-TaskScheduler, SecurityCenter, and Service Control Manager. |

## Entities

**Run Frequency**: Every 3 days (offset to 1 day before Events)

| Stream ID | Log Type | Product Name | Vendor Name | OCSF Class | Notes |
|-----------|----------|--------------|-------------|------------|-------|
| windows_ad | WINDOWS_AD | Active Directory | Microsoft | User Inventory (5003) | Active Directory user and computer entity context for Entity Graph joins. |

<!-- BEGIN_SOLUTION -->

## Rules

**Data RBAC for the Rules**: Must be disabled because the entity graph join rules (in the Rules Workshop) do not work with it on.

| Rule Name                                                                          | Live | Alerting | Notes                                                                                                                                                                                                                                                                 |
|------------------------------------------------------------------------------------|------|----------|----------------------------------------------------------------------------------|
| whoami_execution.yaral                                                             | True | False    | Rule Workshop slide 17                                                           |
| mitre_attack_T1021_002_windows_admin_share_basic.yaral                             | False| False    | Rule Workshop slide 22                                                           |
| suspicious_unusual_location_lnk_file.yaral                                         | False| False    | Rule Workshop slide 27                                                           |
| rw_mimikatz_T1003.yaral                                                            | True | False    | Rule Workshop slide 29                                                           |
| win_password_spray.yaral                                                           | False| False    | Rule Workshop slide 44                                                           |
| win_repeatedAuthFailure_thenSuccess_T1110_001.yaral                                | True | True     | Rule Workshop slide 60                                                           |
| mitre_attack_T1021_002_windows_admin_share_with_user_enrichment.yaral              | False| False    | Rule Workshop slide 50                                                           |
| mitre_attack_T1021_002_windows_admin_share_with_user_entity_non_domain_admin.yaral | False| False    | Rule Workshop slide 55                                                           |
| mitre_attack_T1021_002_windows_admin_share_with_user_entity_domain_admin.yaral     | False| False    | EG workshop slide 43                                                             |
| mitre_attack_T1021_002_windows_admin_share_with_user_entity.yaral                  | False| False    | EG workshop slide 41                                                             |
| rw_utilities_associated_with_ntdsdit_T1003_003.yaral                               | False| False    | Rule Workshop slide 75                                                           |
| mitre_attack_T1021_002_windows_admin_share_with_asset_entity.yaral                 | False| False    | EG workshop slide 45                                                             |
| win_repeatedAuthFailure_thenSuccess_T1110_001_user_asset_entity.yaral              | False| False    | EG workshop slide 47                                                             |
| safebrowsing_hashes_seen_more_than_7_days.yaral                                    | False| False    | EG Workshop slide 105 - Works with this usecase as well as MISP and SAFEBROWSING |
| google_safebrowsing_file_process_creation.yaral                                    | True | True     | EG Workshop slide 113 - Works with this usecase as well as MISP and SAFEBROWSING |
| google_safebrowsing_with_prevalence.yaral                                          | False| False    | EG Workshop slide 115 - Works with this usecase as well as MISP and SAFEBROWSING |

## Saved Searches

| Field           | Value                                                                                            |
|-----------------|--------------------------------------------------------------------------------------------------|
| Search Name     | Failed User Logins by Vendor or Product                                                          |
| Creator         | Google SecOps Curated                                                                            |
| Notes           | Advanced Search Workshop - slide 15 - Also returns data from AZURE_AD and TEMP_ACCOUNT use cases |

## Reference Lists

| Reference List            | Type   | Description                                                                               |
|---------------------------|--------|-------------------------------------------------------------------------------------------|
| key_servers               | String | Key server names - Used for rules workshop                                                |
| ntds_suspicious_processes | String | process names often associated with accessing ntds.dit - Used for rules workshop - Stoner |
