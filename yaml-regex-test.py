# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

import yaml

# Create a test YAML configuration
yaml_content = r"""
WINDOWS_AD:
  api: unstructuredlogentries
  timestamps:
    - name: CreatedDate
      base_time: true
      epoch: true
      group: 2
      pattern: '("Created":"\/Date\()(\d{10})(\d{3})'
    - name: CreateTimeStamp
      epoch: true
      group: 2
      pattern: '("createTimeStamp":"\/Date\()(\d{10})(\d{3})'
"""

# Load the YAML
config = yaml.safe_load(yaml_content)

# Your actual log line content
test_string = r'e":0,"Created":"\/Date(1705615749000)\/","createTimeStamp":"\/Date(1705615749000)\/","Deleted"'

print("Testing patterns from YAML:")
print("=" * 60)

# Test each timestamp pattern
for ts_config in config["WINDOWS_AD"]["timestamps"]:
  print(f"\nTesting: {ts_config['name']}")
  pattern = ts_config["pattern"]

  # Show what's actually in the pattern
  print(f"Pattern from YAML: {repr(pattern)}")
  print(f"Pattern escaped: {pattern.encode('unicode_escape').decode('utf-8')}")

  # Test the pattern
  match = re.search(pattern, test_string)
  if match:
    print("✓ MATCH!")
    print(f"  Full match: {match.group(0)}")
    print(
        f"  Group {ts_config['group']} (timestamp): {match.group(ts_config['group'])}"
    )
    if ts_config["group"] < len(match.groups()):
      print(
          f"  Group {ts_config['group']+1} (milliseconds):"
          f" {match.group(ts_config['group']+1)}"
      )
  else:
    print("✗ NO MATCH")

# Now let's test with different YAML escaping options
print("\n" + "=" * 60)
print("Testing different YAML escaping options:")
print("=" * 60)

yaml_variations = [
    # Option 1: Single quotes with escaped backslash
    """pattern: '("Created":"\\/Date\\()(\\d{10})(\\d{3})' """,
    # Option 2: Single quotes without escape
    r"""pattern: '("Created":"\/Date\()(\d{10})(\d{3})' """,
    # Option 3: Double quotes with proper escaping
    '''pattern: "(\\"Created\\":\\"\\\\/Date\\\\()(\\\\d{10})(\\\\d{3})"''',
    # Option 4: Literal scalar
    r"""pattern: |-
  ("Created":"\/Date\()(\d{10})(\d{3})""",
]

for i, yaml_str in enumerate(yaml_variations):
  print(f"\nOption {i+1}: {yaml_str.strip()}")
  try:
    # Parse just the pattern line
    parsed = yaml.safe_load(yaml_str)
    pattern = parsed["pattern"]
    print(f"  Parsed as: {repr(pattern)}")

    # Test it
    match = re.search(pattern, test_string)
    if match:
      print(f"  ✓ MATCH! Group 2: {match.group(2)}")
    else:
      print("  ✗ NO MATCH")
  except Exception as e:
    print(f"  ERROR: {e}")

# Also test what you're seeing in your debugger
print("\n" + "=" * 60)
print("Testing your debugger pattern:")
print("=" * 60)

debugger_pattern = r'(Created":"\\/Date\()(\d{10})(\d{3})'
print(f"Pattern: {repr(debugger_pattern)}")
print(f"Escaped: {debugger_pattern.encode('unicode_escape').decode('utf-8')}")

match = re.search(debugger_pattern, test_string)
if match:
  print(f"✓ MATCH! Group 2: {match.group(2)}")
else:
  print("✗ NO MATCH")
