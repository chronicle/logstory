# RULES_SEARCH_WORKSHOP

## Introduction

Usecase providing logs for workshops on advanced search capabilities, building rules for Google SecOps, entity graph exploration, and statistical search

**Tags**: rules-workshop, yara-l, google-secops, entity-graph, advanced-search, statistical-search, visualization

**Created**: 2025-07-26

**Updated**: 2025-07-26

## Run Frequency

**Events**: Every 3 days

**Entities**: Every 3 days (offset to 1 day before Events)

## Data RBAC

**Note**: Must be disabled because the entity graph join rules don't work with it on

## Events

| Log Type | Product Name | Vendor Name | Notes |
|----------|--------------|-------------|-------|
| POWERSHELL.log | PowerShell | Microsoft |  |
| WINDOWS_DEFENDER_AV.log | Windows Defender AV | Microsoft |  |
| WINDOWS_SYSMON.log | Microsoft-Windows-Sysmon | Microsoft |  |
| WINEVTLOG.log | Microsoft-Windows-Security-Auditing | Microsoft |  |
| WINEVTLOG.log | Microsoft-Windows-TaskScheduler | Microsoft |  |
| WINEVTLOG.log | SecurityCenter | Microsoft |  |
| WINEVTLOG.log | Service Control Manager | Microsoft |  |

## Entities

| Log Type | Product Name | Vendor Name | Notes |
|----------|--------------|-------------|-------|
| POWERSHELL.log | PowerShell | Microsoft |  |
| WINDOWS_DEFENDER_AV.log | Windows Defender AV | Microsoft |  |
| WINDOWS_SYSMON.log | Microsoft-Windows-Sysmon | Microsoft |  |
| WINEVTLOG.log | Microsoft-Windows-Security-Auditing | Microsoft | Additional product_names in this log type include: Microsoft-Windows-TaskScheduler, SecurityCenter, and Service Control Manager |

## Rules

| Rule Name | Live | Alerting | Notes |
|-----------|------|----------|-------|
| whoami_execution.yaral | True | False | Rule Workshop slide 17 |
| mitre_attack_T1021_002_windows_admin_share_basic.yaral | False | False | Rule Workshop slide 22 |
| suspicious_unusual_location_lnk_file.yaral | False | False | Rule Workshop slide 27 |
| rw_mimikatz_T1003.yaral | True | False | Rule Workshop slide 29 |
| win_password_spray.yaral | False | False | Rule Workshop slide 44 |
| win_repeatedAuthFailure_thenSuccess_T1110_001.yaral | True | True | Rule Workshop slide 60 |
| mitre_attack_T1021_002_windows_admin_share_with_user_enrichment.yaral | False | False | Rule Workshop slide 50 |
| mitre_attack_T1021_002_windows_admin_share_with_user_entity_non_domain_admin.yaral | False | False | Rule Workshop slide 55 |
| mitre_attack_T1021_002_windows_admin_share_with_user_entity_domain_admin.yaral | False | False | EG workshop slide 43 |
| mitre_attack_T1021_002_windows_admin_share_with_user_entity.yaral | False | False | EG workshop slide 41 |
| rw_utilities_associated_with_ntdsdit_T1003_003.yaral | False | False | Rule Workshop slide 75 |
| mitre_attack_T1021_002_windows_admin_share_with_asset_entity.yaral | False | False | EG workshop slide 45 |
| win_repeatedAuthFailure_thenSuccess_T1110_001_user_asset_entity.yaral | False | False | EG workshop slide 47 |
| safebrowsing_hashes_seen_more_than_7_days.yaral | False | False | EG Workshop slide 105 - Works with this usecase as well as MISP and SAFEBROWSING |
| google_safebrowsing_file_process_creation.yaral | True | True | EG Workshop slide 113 - Works with this usecase as well as MISP and SAFEBROWSING |
| google_safebrowsing_with_prevalence.yaral | False | False | EG Workshop slide 115 - Works with this usecase as well as MISP and SAFEBROWSING |

## Saved Searches

| Search Name | Creator | Notes |
|-------------|---------|-------|
| Failed User Logins by Vendor or Product | Google SecOps Curated | Advanced Search Workshop - slide 15 - Also returns data from AZURE_AD and TEMP_ACCOUNT use cases |

## Reference Lists

| List Name | Type | Notes |
|-----------|------|-------|
| key_servers | String | Key server names - Used for rules workshop |
| ntds_suspicious_processes | String | process names often associated with accessing ntds.dit - Used for rules workshop - Stoner |

---

*This document was generated from YAML frontmatter using the usecase template.*
