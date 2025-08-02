# Pattern Simplification with Group-Only Replacement

With the new group-only replacement implementation, we can significantly simplify timestamp patterns by taking advantage of automatic deduplication.

## Example: Windows AD Date Format

### Current Approach (8 separate patterns)

```yaml
WINDOWS_AD:
  timestamps:
    - name: Created
      pattern: '("Created":"\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
    - name: whenCreatedDate
      pattern: '("whenCreated":"\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
    - name: LastLogonDate
      pattern: '("LastLogonDate":"\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
    - name: createTimeStamp
      pattern: '("createTimeStamp":"\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
    - name: Modified
      pattern: '("Modified":"\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
    - name: modifyTimeStamp
      pattern: '("modifyTimeStamp":"\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
    - name: PasswordLastSet
      pattern: '("PasswordLastSet":"\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
    - name: whenChanged
      pattern: '("whenChanged":"\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
```

### Simplified Approach (1 generic pattern)

```yaml
WINDOWS_AD:
  timestamps:
    - name: WindowsADDateFormat
      pattern: '("\\\/Date\()(\d{10})(\d{3})'
      dateformat: 'epoch'
      group: 2
      base_time: true  # If this is the primary timestamp
```

## How It Works

1. **Pattern Matching**: The generic pattern `("\\\/Date\()(\d{10})(\d{3})` matches ALL occurrences of the Windows AD date format

2. **Group Extraction**: Only group 2 (the 10-digit timestamp) is extracted for replacement

3. **Change Map Deduplication**: 
   - Each unique timestamp position creates one change map entry
   - Multiple matches of the same timestamp are automatically deduplicated
   - The field name prefix is preserved because we only replace the timestamp group

4. **Result**: All timestamps are updated correctly with just one pattern definition

## Benefits

1. **Maintainability**: One pattern to maintain instead of 8+
2. **Flexibility**: Automatically handles new fields without YAML changes
3. **Clarity**: Makes it clear that all these fields use the same timestamp format
4. **Performance**: Fewer pattern definitions to process

## Considerations

### When to Use Generic Patterns

Generic patterns work best when:
- Multiple fields use the exact same timestamp format
- Field names don't affect how timestamps should be processed
- You don't need field-specific logging or behavior

### When to Keep Specific Patterns

Keep field-specific patterns when:
- Different fields need different date transformations
- You need detailed logging of which fields were updated
- Some fields should be excluded from updates
- Different fields have different base_time settings

## Migration Strategy

To migrate to simplified patterns:

1. **Identify Common Formats**: Group patterns that use the same timestamp format
2. **Create Generic Pattern**: Extract the common part, keeping only what's needed to find the timestamp
3. **Test Thoroughly**: Ensure the generic pattern doesn't match unintended timestamps
4. **Update Documentation**: Note which fields are covered by each generic pattern

## Example Test

```python
# Both patterns will create the same change map entry
specific_pattern = '("PasswordLastSet":"\\\/Date\()(\d{10})(\d{3})'
generic_pattern = '("\\\/Date\()(\d{10})(\d{3})'

# For timestamp at position X:
# Change map key: (X, X+10, "1706212385")
# Both patterns → same key → automatic deduplication
```