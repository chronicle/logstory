# Timestamp Replacement Algorithm

## Overview

LogStory's timestamp replacement algorithm has evolved to handle complex scenarios where multiple timestamp patterns might match overlapping portions of log text. This document describes the current implementation using a "change map" approach.

## The Problem

When processing logs with multiple timestamp patterns, several issues can arise:

1. **Double Updates**: If patterns are applied sequentially, a pattern might match text that was already modified by a previous pattern
2. **Overlapping Matches**: Different patterns might match overlapping portions of text
3. **Duplicate Work**: Multiple patterns might want to make the same change

### Example of the Double Update Problem

```python
# Original log line
log = "UtcTime: 2024-01-25 19:53:05"

# Pattern 1: Updates 2024 → 2025
log = "UtcTime: 2025-01-25 19:53:05"

# Pattern 2: Looks for "2025" and updates to 2026
log = "UtcTime: 2026-01-25 19:53:05"  # WRONG! Double update
```

## The Solution: Change Map Algorithm

### Algorithm Steps

1. **Collection Phase**
   ```python
   change_map = {}  # (start, end, original) → replacement
   
   for pattern in timestamp_patterns:
       match = pattern.search(log_line)
       if match:
           replacement = calculate_replacement(match)
           key = (match.start(), match.end(), match.group(0))
           
           if key in change_map:
               if change_map[key] != replacement:
                   log_warning("Conflict detected")
               # else: Same change, no-op
           else:
               change_map[key] = replacement
   ```

2. **Application Phase**
   ```python
   # Sort by start position, apply right-to-left
   for (start, end, _), replacement in sorted(change_map.items(), reverse=True):
       log_line = log_line[:start] + replacement + log_line[end:]
   ```

### Key Features

#### 1. Deduplication
If two patterns want to make the same change to the same text span, it's recognized as a single operation:

```python
# Pattern A: "UtcTime: 2024-01-25" → "UtcTime: 2025-07-31"
# Pattern B: "2024-01-25" → "2025-07-31"
# Result: Both changes are compatible, text updated once
```

#### 2. Conflict Detection
If patterns want different changes to the same span, a warning is logged:

```python
# Pattern A: "2024" → "2025"
# Pattern B: "2024" → "2026"
# Result: Warning logged, first pattern wins
```

#### 3. Position Preservation
By applying changes right-to-left, we ensure that position calculations remain valid throughout the process.

## Implementation Details

### Data Structure

The change map uses a tuple key for precise tracking:
- `start`: Starting position of the match
- `end`: Ending position of the match
- `original`: The original matched text (for validation)

### Type Annotation

```python
change_map: dict[tuple[int, int, str], str] = {}
```

### Example Execution

```python
# Log line: "Time: 2024-01-25 19:53:05, Date: 2024-01-25"

# After collection phase:
change_map = {
    (6, 25, "2024-01-25 19:53:05"): "2025-07-31 19:53:05",
    (6, 16, "2024-01-25"): "2025-07-31",
    (33, 43, "2024-01-25"): "2025-07-31"
}

# After application (right to left):
# Step 1: Replace at 33-43
# Step 2: Replace at 6-25 (covers 6-16, so that change is superseded)
# Result: "Time: 2025-07-31 19:53:05, Date: 2025-07-31"
```

## Benefits

1. **Correctness**: Each piece of text is modified at most once
2. **Explicitness**: The change map makes it clear what will be modified
3. **Efficiency**: Natural deduplication through the map structure
4. **Debuggability**: Easy to log and inspect the planned changes

## Testing

The implementation is thoroughly tested in:
- `tests/test_change_map_implementation.py` - Unit tests for the algorithm
- `tests/test_double_update_fix.py` - Tests demonstrating the fix for double updates

## Future Considerations

The current implementation assumes that timestamp patterns don't produce replacements of significantly different lengths. If needed, the algorithm could be extended to handle length-changing replacements more sophisticatedly.