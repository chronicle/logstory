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

# Your actual log line content
test_string = r'e":0,"Created":"\/Date(1705615749000)\/","createTimeStamp":"\/Date(1705615749000)\/","Deleted"'

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
