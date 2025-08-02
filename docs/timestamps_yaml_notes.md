# Timestamp YAML Configuration Notes

## Overview

This document explains how timestamp patterns work in the LogStory timestamp configuration YAML files (`logtypes_entities_timestamps.yaml` and `logtypes_events_timestamps.yaml`).

## Key Concepts

### 1. Pattern Matching vs. Timestamp Mutation

The timestamp patterns are designed to:
- **Extract** specific portions of timestamps for processing
- **Update** only the captured portions (days/hours/minutes)
- **Preserve** any uncaptured precision (milliseconds, microseconds, etc.)

**Important**: The regex patterns do NOT delete or modify parts of the timestamp they don't capture. Uncaptured portions remain unchanged in the log.

### 2. Pattern and Dateformat Alignment

Each timestamp configuration requires these fields:

```yaml
- name: UtcTimeQuotes            # Unique identifier for this pattern
  pattern: '("UtcTime"\s*:\s*"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
  dateformat: "%Y-%m-%d %H:%M:%S"  # REQUIRED: Must be 'epoch', 'windowsfiletime', or strftime format
  group: 2                       # Which capture group contains the timestamp
  base_time: false               # Optional: true for the primary timestamp (only one per log type)
```

#### Pattern
- The regex pattern that finds and captures the timestamp
- Uses capture groups (parentheses) to extract specific parts
- The `group` parameter specifies which capture group contains the timestamp value

#### Dateformat (REQUIRED)
- Must be one of:
  - `'epoch'` for Unix timestamps
  - `'windowsfiletime'` for Windows FileTime
  - A strftime format string for human-readable timestamps
- For strftime formats: Must match EXACTLY what the pattern captures
- Used to parse the captured string into a datetime object

### 3. Common Pattern Examples

#### Example 1: Basic timestamp without milliseconds
```yaml
# Log: "UtcTime":"2024-01-25 19:53:06.967"
pattern: '("UtcTime"\s*:\s*"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
dateformat: "%Y-%m-%d %H:%M:%S"
group: 2

# Captures: "2024-01-25 19:53:06"
# Leaves untouched: ".967"
```

#### Example 2: Windows FileTime format
```yaml
# Log: "lastLogon":133504425386052066
pattern: '("lastLogon":)(\d{18})'
dateformat: "windowsfiletime"  # Special format
group: 2
```

#### Example 3: Unix epoch timestamp
```yaml
# Log: "EventTime":1706212385
pattern: '("EventTime":)(\d{10})'
dateformat: "epoch"  # Unix epoch format
group: 2
```

#### Example 4: ISO format with T separator
```yaml
# Log: "createdDateTime":"2022-11-22T19:02:06Z"
pattern: '("createdDateTime":")(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(Z)'
dateformat: "%Y-%m-%dT%H:%M:%S"
group: 2
```

## Dateformat Types

The `dateformat` field is **required** and accepts three types of values:

1. **`'epoch'`** - For Unix epoch timestamps
   - Use when pattern captures 10-digit (seconds) or 13-digit (milliseconds) numbers
   - Example: `"EventTime":1706212385`

2. **`'windowsfiletime'`** - For Windows FileTime format
   - Use when pattern captures 18-digit numbers
   - Represents 100-nanosecond intervals since January 1, 1601
   - Example: `"lastLogon":133504425386052066`

3. **strftime format string** - For human-readable timestamps
   - Use Python strftime format codes (e.g., `%Y`, `%m`, `%d`)
   - Must exactly match what the pattern captures
   - Example: `"%Y-%m-%d %H:%M:%S"` for `"2024-01-25 19:53:06"`

## Critical Rules

### 1. Dateformat MUST Match Pattern Capture

For strftime formats, the format string must exactly match what the pattern captures:
- If pattern captures `2024-01-25 19:53:06`, use `%Y-%m-%d %H:%M:%S`
- If pattern captures `2024-01-25T19:53:06`, use `%Y-%m-%dT%H:%M:%S`

**Common mistakes:**
- Pattern captures with space separator but dateformat uses 'T'
- Pattern captures without milliseconds but dateformat includes `%f`
- Pattern captures date only but dateformat includes time

### 2. Group Number Alignment

The `group` parameter specifies which regex capture group contains the timestamp:
- Group 0: The entire match
- Group 1: First parentheses
- Group 2: Second parentheses, etc.

Example:
```yaml
pattern: '("UtcTime"\s*:\s*"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
#         ^---- Group 1 ----^  ^----------- Group 2 ------------^
group: 2  # Extract the timestamp, not the field name
```

### 3. Precision Preservation

When updating timestamps, LogStory:
1. Uses the pattern to find the timestamp in the log
2. Extracts the captured portion using the specified group
3. Parses it using the dateformat
4. Applies time transformations
5. Formats it back using the same dateformat
6. Replaces ONLY the captured portion in the original log

**Result**: Milliseconds, timezone indicators, and other uncaptured parts remain unchanged.

## Special Formats

### Windows FileTime
- 18-digit number representing 100-nanosecond intervals since 1601-01-01
- Use `dateformat: "windowsfiletime"`
- Pattern should capture exactly 18 digits: `\d{18}`

### Unix Epoch
- 10-digit number representing seconds since 1970-01-01
- Use `dateformat: "epoch"`
- Pattern should capture exactly 10 digits: `\d{10}`
- The code automatically detects whether it's seconds (10 digits) or milliseconds (13 digits)

### Millisecond Timestamps
- 13-digit number representing milliseconds since 1970-01-01
- Also use `dateformat: "epoch"` (same as 10-digit timestamps)
- Pattern should capture exactly 13 digits: `\d{13}`
- LogStory automatically handles the conversion from milliseconds

## Best Practices

1. **Test Your Patterns**: Use the test_timestamp_patterns.py tool to verify patterns match correctly

2. **Be Specific**: Make patterns specific to avoid false matches
   - Good: `("UtcTime"\s*:\s*"?)`
   - Bad: `(Time.*:)`

3. **Handle Format Variations**: Consider JSON vs XML formats
   ```yaml
   # JSON format
   pattern: '("CreationUtcTime":")(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'

   # XML format
   pattern: '(CreationUtcTime:\s*)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
   ```

4. **Document Edge Cases**: Use the `examples` field to document variations:
   ```yaml
   examples:
     - '"UtcTime":"2024-01-25 19:53:06'
     - '"UtcTime" : "2024-01-25 19:53:06'
     - '"UtcTime":2024-01-25 19:53:06'  # No quotes around value
   ```

5. **Mark Base Time**: Exactly one pattern per log type should have `base_time: true`

## Debugging Tips

1. **Pattern Not Matching?**
   - Check for extra whitespace in the pattern
   - Verify quotes are escaped properly in YAML
   - Test with the exact log line using regex tools

2. **Time Parse Errors?**
   - Ensure dateformat exactly matches what the pattern captures
   - Check for timezone indicators (Z, +00:00) not handled by dateformat
   - Verify group number extracts the correct capture group

3. **Wrong Time Updates?**
   - Confirm the correct pattern is marked as `base_time: true`
   - Check if multiple patterns are matching the same timestamp
   - Verify dateformat matches the captured timestamp format

## Testing Patterns

Use the provided test tools:

```bash
# Test single file
python tests/test_timestamp_patterns.py \
  src/logstory/logtypes_events_timestamps.yaml \
  path/to/logfile.log \
  --log-type WINDOWS_SYSMON

# Test all files in directory
python tests/analyze_all_timestamps.py \
  src/logstory/logtypes_events_timestamps.yaml \
  path/to/logs/
```

This will show:
- Which patterns match
- Exact character positions
- Overlapping patterns
- Match counts

## How LogStory Handles Overlapping Patterns

### The Change Map Approach

LogStory uses a sophisticated "change map" approach to handle cases where multiple timestamp patterns might match the same or overlapping text. This prevents corruption and ensures each timestamp is updated exactly once.

#### How It Works

1. **Collection Phase**: For each log line, all timestamp patterns are evaluated and their replacements are collected into a change map
2. **Change Map Structure**: `(start_position, end_position, original_text) → replacement_text`
3. **Deduplication**: If multiple patterns want to make the same change to the same text, it's treated as a single operation
4. **Conflict Detection**: If patterns want different changes to the same text span, a warning is logged
5. **Application Phase**: All unique changes are applied in reverse order (right to left) to preserve positions

#### Example

```yaml
# Log line: "UtcTime: 2024-01-25 19:53:05, Data: 2024-01-25"

# Pattern 1: Matches "UtcTime: 2024-01-25 19:53:05"
# Pattern 2: Matches "2024-01-25 19:53:05" 
# Pattern 3: Matches "2024-01-25" (both occurrences)

# Change map after processing:
# (0, 28, "UtcTime: 2024-01-25 19:53:05") → "UtcTime: 2025-07-31 19:53:05"
# (9, 28, "2024-01-25 19:53:05") → "2025-07-31 19:53:05"
# (9, 19, "2024-01-25") → "2025-07-31"
# (36, 46, "2024-01-25") → "2025-07-31"

# Result: Each unique span is updated exactly once
```

#### Benefits

- **Prevents Double Updates**: Text is never updated multiple times by different patterns
- **Intelligent Deduplication**: Same changes to the same text are recognized and deduplicated
- **Explicit Conflict Handling**: Different changes to the same text are detected and logged
- **Maintains Correctness**: Preserves log integrity by ensuring consistent updates

## Migration from Legacy Format

If you're updating from the old format that used `epoch: true/false`:

| Old Format | New Format |
|------------|------------|
| `epoch: true` | `dateformat: "epoch"` |
| `epoch: false` with `dateformat: "%s"` | `dateformat: "epoch"` |
| `epoch: false` with `dateformat: "<strftime>"` | `dateformat: "<strftime>"` |
| `epoch: false` for Windows FileTime | `dateformat: "windowsfiletime"` |

The `epoch:` field is no longer used and should be removed from all configurations.