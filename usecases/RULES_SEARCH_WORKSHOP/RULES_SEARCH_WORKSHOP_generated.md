# RULES_SEARCH_WORKSHOP

## Introduction

Usecase providing logs for workshops on advanced search capabilities, building rules for Google Security Operations, entity graph exploration, and statistical search.

**ID**: RULES_SEARCH_WORKSHOP

**Version**: 2.0.0

**Author**: Google Cloud Security

**License**: Apache-2.0

**Tags**: rules-workshop, yara-l, google-secops, entity-graph, advanced-search, statistical-search, visualization, ocsf

**Created**: 2025-07-26

**Updated**: 2026-11-05

## Environment

**Organization**: cymbal-investments.org

**Scenario Type**: workshop

## Run Frequency

**Events**: Every 3 days

**Entities**: Every 3 days (offset to 1 day before Events)

## Data RBAC

**Note**: Must be disabled because the entity graph join rules don't work with it on

## Events

| Stream ID | Log Type | Product Name | Vendor Name | OCSF Class | Notes |
|-----------|----------|--------------|-------------|------------|-------|
| powershell | POWERSHELL | PowerShell | Microsoft | Process Activity (1007) | Windows PowerShell script block and command execution logs. |
| windows_defender_av | WINDOWS_DEFENDER_AV | Windows Defender AV | Microsoft | Detection Finding (2004) | Microsoft Defender Antivirus detection and threat alert telemetry. |
| windows_sysmon | WINDOWS_SYSMON | Microsoft-Windows-Sysmon | Microsoft | Process Activity (1007) | Sysmon process creation, file creation, and network telemetry. |
| winevtlog | WINEVTLOG | Microsoft-Windows-Security-Auditing | Microsoft | Authentication (3002) | Additional product_names in this log type include: Microsoft-Windows-TaskScheduler, SecurityCenter, and Service Control Manager. |

## Entities

| Stream ID | Log Type | Product Name | Vendor Name | OCSF Class | Notes |
|-----------|----------|--------------|-------------|------------|-------|
| windows_ad | WINDOWS_AD | Active Directory | Microsoft | User Inventory (5003) | Active Directory user and computer entity context for Entity Graph joins. |

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

## Platform Bindings

### Google SecOps

- `powershell`: `POWERSHELL`
- `windows_defender_av`: `WINDOWS_DEFENDER_AV`
- `windows_sysmon`: `WINDOWS_SYSMON`
- `winevtlog`: `WINEVTLOG`
- `windows_ad`: `WINDOWS_AD`

### Databricks

- **Catalog**: `security_lakehouse`
- **Schema**: `ocsf_silver`
- `powershell`: `secops_ocsf.process_activity`
- `windows_defender_av`: `secops_ocsf.detection_finding`
- `windows_sysmon`: `secops_ocsf.process_activity`
- `winevtlog`: `secops_ocsf.authentication`
- `windows_ad`: `secops_ocsf.user_inventory`

### Splunk

- `powershell`: `XmlWinEventLog:Microsoft-Windows-PowerShell/Operational`
- `windows_defender_av`: `XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational`
- `windows_sysmon`: `XmlWinEventLog:Microsoft-Windows-Sysmon/Operational`
- `winevtlog`: `XmlWinEventLog:Security`
- `windows_ad`: `ms:ad:user`

---

*This document was generated from YAML frontmatter using the usecase template.*