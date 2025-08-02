#!/usr/bin/env python3
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

"""Test that group-only replacement enables pattern simplification."""

import datetime
import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from logstory.main import _calculate_timestamp_replacement


class TestGroupOnlyReplacement(unittest.TestCase):
  """Test cases for group-only replacement behavior."""

  def test_different_patterns_same_timestamp_position(self):
    """Test that different patterns matching the same timestamp deduplicate."""

    # Log line with the Windows AD Date format
    log_line = r'"PasswordLastSet":"\/Date(1706212385000)\/"'
    old_base_time = datetime.datetime(2024, 1, 25, 19, 53, 5)
    ts_delta_dict = {"d": 1}

    # Two patterns that will find the same timestamp
    patterns = [
        {
            "name": "PasswordLastSet specific",
            "pattern": r'("PasswordLastSet":"\\\/Date\()(\d{10})(\d{3})',
            "dateformat": "epoch",
            "group": 2,
        },
        {
            "name": "Generic Date pattern",
            "pattern": r'("\\\/Date\()(\d{10})(\d{3})',
            "dateformat": "epoch",
            "group": 2,
        },
    ]

    # Process both patterns
    results = []
    for pattern in patterns:
      result = _calculate_timestamp_replacement(
          log_line, pattern, old_base_time, ts_delta_dict
      )
      if result:
        match, replacement = result
        results.append({
            "pattern": pattern["name"],
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0),
            "replacement": replacement,
        })

    # Both should find the same timestamp at the same position
    self.assertEqual(len(results), 2, "Both patterns should match")

    # Check that they match the same position
    self.assertEqual(
        results[0]["start"],
        results[1]["start"],
        "Should match at the same start position",
    )
    self.assertEqual(
        results[0]["end"], results[1]["end"], "Should match at the same end position"
    )
    self.assertEqual(
        results[0]["text"], results[1]["text"], "Should match the same text"
    )
    self.assertEqual(
        results[0]["replacement"],
        results[1]["replacement"],
        "Should produce the same replacement",
    )

    print(f"\nBoth patterns found the same timestamp:")
    print(f"  Position: {results[0]['start']}-{results[0]['end']}")
    print(f"  Text: '{results[0]['text']}'")
    print(f"  Replacement: '{results[0]['replacement']}'")

  def test_group_only_change_map(self):
    """Test that the change map correctly handles group-only replacements."""

    log_line = (
        r'"Created":"\/Date(1706212385000)\/","Modified":"\/Date(1706212385000)\/"'
    )
    old_base_time = datetime.datetime(2024, 1, 25, 19, 53, 5)
    ts_delta_dict = {"d": 1}

    patterns = [
        {
            "name": "Created",
            "pattern": r'("Created":"\\\/Date\()(\d{10})(\d{3})',
            "dateformat": "epoch",
            "group": 2,
        },
        {
            "name": "Modified",
            "pattern": r'("Modified":"\\\/Date\()(\d{10})(\d{3})',
            "dateformat": "epoch",
            "group": 2,
        },
        {
            "name": "Generic",
            "pattern": r'("\\\/Date\()(\d{10})(\d{3})',
            "dateformat": "epoch",
            "group": 2,
        },
    ]

    # Build a change map like the main code does
    change_map = {}

    for pattern in patterns:
      result = _calculate_timestamp_replacement(
          log_line, pattern, old_base_time, ts_delta_dict
      )

      if result:
        match, replacement = result
        # This is what the main code does
        change_key = (match.start(), match.end(), match.group(0))

        if change_key not in change_map:
          change_map[change_key] = replacement
          print(f"\n{pattern['name']}: Added to change map")
          print(f"  Key: {change_key}")
        else:
          print(f"\n{pattern['name']}: Already in change map (deduped)")

    # Should have exactly 2 entries (one for each distinct timestamp position)
    self.assertEqual(
        len(change_map), 2, "Should have 2 unique timestamps even with 3 patterns"
    )

  def test_replacement_only_affects_group(self):
    """Test that only the specified group is replaced, not the entire match."""

    log_line = r'"LastLogon":"\/Date(1706212385000)\/"'
    old_base_time = datetime.datetime(2024, 1, 25, 19, 53, 5)
    ts_delta_dict = {"d": 1}

    pattern = {
        "name": "LastLogon",
        "pattern": r'("LastLogon":"\\\/Date\()(\d{10})(\d{3})',
        "dateformat": "epoch",
        "group": 2,
    }

    result = _calculate_timestamp_replacement(
        log_line, pattern, old_base_time, ts_delta_dict
    )

    self.assertIsNotNone(result)
    match, replacement = result

    # The match should be for ONLY the timestamp group
    self.assertEqual(
        match.group(0),
        "1706212385",
        "Should match only the timestamp, not the full pattern",
    )

    # Apply the replacement like the main code would
    result_line = log_line[: match.start()] + replacement + log_line[match.end() :]

    # Verify the field name and structure are preserved
    self.assertIn(r'"LastLogon":"\/Date(', result_line)
    self.assertIn(r'000)\/"', result_line)
    self.assertNotIn("1706212385", result_line)

    print(f"\nGroup-only replacement:")
    print(f"  Original: {log_line}")
    print(f"  Result:   {result_line}")


if __name__ == "__main__":
  unittest.main(verbosity=2)
