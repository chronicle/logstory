import re

# Your actual log line content
test_string = 'e":0,"Created":"\/Date(1705615749000)\/","createTimeStamp":"\/Date(1705615749000)\/","Deleted"'

# Test patterns
patterns = [
    r'("Created":"\/Date\()(\d{10})(\d{3})',  # Your current pattern (missing the trailing \/)
    r'("Created":"\\/Date\()(\d{10})(\d{3})',  # With trailing \/
    r'("Created":"\/Date\()(\d{10})(\d{3})',  # With trailing \/","
]

for i, pattern in enumerate(patterns):
  match = re.search(pattern, test_string)
  if match:
    print(f"Pattern {i}: ✓ MATCH")
    print(f"  Full match: {match.group(0)}")
    print(f"  Group 2 (seconds): {match.group(2)}")
    print(f"  Group 3 (milliseconds): {match.group(3)}")
  else:
    print(f"Pattern {i}: ✗ NO MATCH")
