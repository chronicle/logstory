# YAML Timestamp Consolidation Proposal

## Overview

With the group-only replacement feature, we can consolidate duplicate strftime dateformats within each log type.
This document proposes specific changes to reduce redundancy while preserving all `base_time: true` entries.

## Key Principles

1. **Always preserve** entries with `base_time: true` exactly as-is
2. **Always preserve** entries with `dateformat: 'epoch'` or `dateformat: 'windowsfiletime'`
3. **Consolidate** multiple entries with the same strftime dateformat into a single generic pattern
4. The generic pattern should be broad enough to match all field names but specific enough to match only timestamps

## Proposed Changes

### logtypes_entities_timestamps.yaml

#### AZURE_AD_CONTEXT

**Current**: 7 entries (1 base_time + 6 duplicates of `%Y-%m-%dT%H:%M:%S`)

**Proposed**: 2 entries

```yaml
AZURE_AD_CONTEXT:
  timestamps:
    # PRESERVED: base_time entry
    - name: onPremisesLastSyncDateTime_base_time
      pattern: '("onPremisesLastSyncDateTime":")(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(Z)'
      dateformat: '%Y-%m-%dT%H:%M:%S'
      group: 2
      base_time: true

    # NEW: Consolidated generic pattern
    - name: AZURE_AD_generic_timestamp
      pattern: '("[^"]+DateTime":")(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'
      dateformat: '%Y-%m-%dT%H:%M:%S'
      group: 2
      # Replaces: created_date_time, assigned_dt, refresh_token_valid_from_dt,
      #          signin_session_valid_from_dt, approx_last_signin_dt, registration_dt
```

#### GCP_DLP_CONTEXT

**Current**: 5 entries (1 base_time + 4 duplicates of `%Y-%m-%dT%H:%M:%S`)

**Proposed**: 2 entries

```yaml
GCP_DLP_CONTEXT:
  timestamps:
    # PRESERVED: base_time entry
    - name: gcp_dlp_entity_timestamp
      pattern: '(timestamp"\s*:\s*"?)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(.\d+Z\s*|Z")'
      dateformat: '%Y-%m-%dT%H:%M:%S'
      group: 2
      base_time: true

    # NEW: Consolidated generic pattern
    - name: GCP_DLP_generic_timestamp
      pattern: '([^"]+Time"\s*:\s*"?)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'
      dateformat: '%Y-%m-%dT%H:%M:%S'
      group: 2
      # Replaces: gcp_dlp_entity_createTime, gcp_dlp_entity_lastModifiedTime,
      #          gcp_dlp_entity_expirationTime, gcp_dlp_entity_profileLastGenerated
```

### logtypes_events_timestamps.yaml

#### WINDOWS_SYSMON

**Current**: 9 entries (1 base_time + 5 duplicates of `%Y-%m-%d %H:%M:%S` + 3 other formats)

**Proposed**: 5 entries

```yaml
WINDOWS_SYSMON:
  api: unstructuredlogentries
  log_dir: /tmp/var/log/logstory
  timestamps:
    # PRESERVED: base_time entry
    - name: UtcTimeQuotes
      base_time: true
      dateformat: "%Y-%m-%d %H:%M:%S"
      pattern: '("UtcTime"\s*:\s*"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
      group: 2

    # PRESERVED: Different formats
    - name: syslog_timestamp
      dateformat: "%b %d %H:%M:%S"
      pattern: '(<\d+>)([a-zA-Z]{3}\s+\d+\s+\d\d:\d\d:\d\d)'
      group: 2

    - name: EventTime
      pattern: ("EventTime":)(\d+)(,)
      dateformat: 'epoch'
      group: 2

    - name: EventReceivedTime
      pattern: ("EventReceivedTime":)(\d+)(,)
      dateformat: 'epoch'
      group: 2

    # NEW: Consolidated generic pattern
    - name: WINDOWS_SYSMON_generic_timestamp
      dateformat: "%Y-%m-%d %H:%M:%S"
      pattern: '([\w"]*Time[\w"]*\s*:\s*"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
      group: 2
      # Replaces: UtcTime, EventTimeUTC, EventReceivedTimeUTC,
      #          CreationUtcTime, CreationUtcTimeQuotes
```

#### WINDOWS_DEFENDER_AV

**Current**: 13 entries (1 base_time + 10 duplicates of `%m/%d/%Y %I:%M:%S %p` + 2 other formats)

**Proposed**: 4 entries

```yaml
WINDOWS_DEFENDER_AV:
  api: unstructuredlogentries
  log_dir: /tmp/var/log/logstory
  timestamps:
    # PRESERVED: base_time and different formats
    - name: EventTime
      base_time: true
      pattern: ("EventTime":)(\d+)(,)
      dateformat: 'epoch'
      group: 2

    - name: syslog_timestamp
      dateformat: "%b %d %H:%M:%S"
      pattern: '(<\d+>)([a-zA-Z]{3}\s+\d+\s+\d\d:\d\d:\d\d)'
      group: 2

    - name: EventReceivedTime
      pattern: ("EventReceivedTime":)(\d+)(,)
      dateformat: 'epoch'
      group: 2

    # NEW: Consolidated generic pattern
    - name: WINDOWS_DEFENDER_AV_generic_timestamp
      dateformat: "%m/%d/%Y %I:%M:%S %p"
      pattern: '([^:]+(?:time|Timestamp)(?:[^:]*)?:\s*"?)(\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}:\d{2} [AP]M)'
      group: 2
      # Replaces all 10 security intelligence and scan time entries
```

## Summary of Reductions

### logtypes_entities_timestamps.yaml

- AZURE_AD_CONTEXT: 7 → 2 entries (5 removed)
- GCP_DLP_CONTEXT: 5 → 2 entries (3 removed)
- **Total**: 8 entries removed

### logtypes_events_timestamps.yaml

- AWS_CLOUDTRAIL: 3 → 2 entries (1 removed)
- GCP_CLOUDAUDIT: 3 → 2 entries (1 removed)
- GCP_SECURITYCENTER_THREAT: 3 → 2 entries (1 removed)
- GCP_SECURITYCENTER_MISCONFIGURATION: 3 → 2 entries (1 removed)
- GCP_VPC_FLOW: 4 → 2 entries (2 removed)
- GUARDDUTY: 4 → 2 entries (2 removed)
- MICROSOFT_DEFENDER_ENDPOINT: 4 → 2 entries (2 removed)
- OFFICE_365: 3 → 2 entries (1 removed)
- OKTA: 4 → 2 entries (2 removed)
- WINDOWS_DEFENDER_ATP: 4 → 2 entries (2 removed)
- WINDOWS_DEFENDER_AV: 13 → 4 entries (9 removed)
- WINDOWS_SYSMON: 9 → 5 entries (4 removed)
- WINEVTLOG: 5 → 4 entries (1 removed)
- **Total**: 26 entries removed

**Grand Total**: 34 entries removed across both files

## Implementation Notes

1. The generic patterns use character classes like `[^"]+` or `[\w"]+` to match various field names
2. The patterns are designed to be broad enough to catch all instances but specific enough to avoid false matches
3. All `base_time: true` entries remain unchanged
4. All `epoch` and `windowsfiletime` entries remain unchanged
5. Comments in the YAML should indicate which entries were replaced by each generic pattern

## Testing Recommendations

After implementing these changes:

1. Run the existing tests to ensure timestamps are still matched correctly
2. Use `test_timestamp_patterns.py` to verify coverage
3. Test with actual log files to ensure no timestamps are missed
4. Verify that the change map correctly deduplicates multiple matches
