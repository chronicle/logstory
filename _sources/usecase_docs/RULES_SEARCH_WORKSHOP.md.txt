
# RULES_SEARCH_WORKSHOP

## Introduction

This usecase provides logs for the following workshops:
 1. Advanced Search Capabilities
 1. Building Rules for Google SecOps
 1. Diving Deep into the Entity Graph
 1. Searching with Google Secops
 1. Statistical Search with Google SecOps (Exercise #2)
 1. Visualizing Alerts in Google SecOps

The "Building Rules for Google SecOps" workshop focuses on using YARA-L 2.0 to create rules within the Google SecOps platform. The workshop is hands-on and designed to help participants learn how to build rules for detecting security events. The material covers a range of topics, including YARA-L basics, constructing rules, using entity data, outcomes, functions, and lists. It also covers the rule-building process, from detecting single events to detecting across multiple events. The workshop also emphasizes the importance of testing rules and provides guidance for doing so. It assumes that users will be duplicating or copying rules to test. The workshop also encourages users to start simple and test their rules on existing data, adding additional criteria as needed.

## Events

**Run Frequency**: Every 3 days

| Log Type                | Product Name                         | Vendor Name | Notes |
|-------------------------|--------------------------------------|-------------|-------|
| POWERSHELL.log          | PowerShell                           | Microsoft   |       |
| WINDOWS_DEFENDER_AV.log | Windows Defender AV                  | Microsoft   |       |
| WINDOWS_SYSMON.log.     | Microsoft-Windows-Sysmon             | Microsoft   |       |
| WINEVTLOG.log           | Microsoft-Windows-Security-Auditing  | Microsoft   |       |
|                         | Microsoft-Windows-TaskScheduler      |             |       |
|                         | SecurityCenter                       |             |       |
|                         | Service Control Manager              |             |       |
|                         | Microsoft-Windows-TaskScheduler      |             |       |

## Entities

**Run Frequency**: Every 3 days (offset to 1 day before Events)

| Log Type                | Product Name                        | Vendor Name | Notes                                                                                                                           |
|-------------------------|-------------------------------------|-------------|---------------------------------------------------------------------------------------------------------------------------------|
| POWERSHELL.log          | PowerShell                          | Microsoft   |                                                                                                                                 |
| WINDOWS_DEFENDER_AV.log | Windows Defender AV                 | Microsoft   |                                                                                                                                 |
| WINDOWS_SYSMON.log      | Microsoft-Windows-Sysmon            | Microsoft   |                                                                                                                                 |
| WINEVTLOG.log           | Microsoft-Windows-Security-Auditing | Microsoft   | Additional product_names in this log type include: Microsoft-Windows-TaskScheduler, SecurityCenter, and Service Control Manager |


## Rules

**Data RBAC for the Rules**: Must be disabled because the entity graph join rules (in the Rules Workshop) don’t work with it on.


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



