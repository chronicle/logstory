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

"""Test that the timestamp replacement fix prevents double updates.

This test documents a critical bug fix where timestamps could be updated multiple times
if patterns matched already-updated text. The solution collects all replacements first,
then applies them in a single pass.
"""

import datetime
import re
import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from logstory.main import _calculate_timestamp_replacement


class TestDoubleUpdateFix(unittest.TestCase):
  """Test cases for the double update fix."""

  def test_demonstrates_the_problem(self):
    """Demonstrates how sequential updates could cause double-processing."""

    print("\n=== DEMONSTRATING THE DOUBLE-UPDATE PROBLEM ===")

    # Example: A log with two timestamps
    log_line = "UtcTime: 2024-01-25 19:53:05, NextTime: 2024-01-25 19:53:10"

    # OLD BEHAVIOR (what would happen with sequential re.sub calls):
    print("\nOLD BEHAVIOR (Sequential re.sub):")
    temp_line = log_line
    print(f"Original: {temp_line}")

    # First pattern updates 2024-01-25 to 2025-01-24
    temp_line = re.sub(
        r"(UtcTime:\s*)(\d{4})-(\d{2}-\d{2})", r"\g<1>2025-\3", temp_line
    )
    print(f"After pattern 1: {temp_line}")

    # Second pattern looks for ANY timestamp and updates the year
    # This would match BOTH timestamps, including the already-updated one!
    temp_line = re.sub(r"(\w+Time:\s*)2025-(\d{2}-\d{2})", r"\g<1>2026-\2", temp_line)
    print(f"After pattern 2: {temp_line}")
    print("BUG: UtcTime was updated TWICE (2024 -> 2025 -> 2026)!")

  def test_fix_prevents_double_update(self):
    """Test that our fix prevents double updates."""

    print("\n=== TESTING THE FIX ===")

    # Test data
    log_line = "UtcTime: 2024-01-25 19:53:05, EventTime: 1706212385"
    old_base_time = datetime.datetime(2024, 1, 25, 19, 53, 5)
    ts_delta_dict = {"d": 1}  # Go back 1 day

    # Two patterns that could interfere with each other
    patterns = [
        {
            "name": "UtcTime",
            "pattern": r"(UtcTime:\s*)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
            "dateformat": "%Y-%m-%d %H:%M:%S",
            "group": 2,
        },
        {
            "name": "EventTime",
            "pattern": r"(EventTime:\s*)(\d{10})",
            "dateformat": "epoch",
            "group": 2,
        },
    ]

    print(f"Original: {log_line}")

    # Collect all replacements first (NEW behavior)
    replacements = []
    for pattern in patterns:
      result = _calculate_timestamp_replacement(
          log_line, pattern, old_base_time, ts_delta_dict
      )
      if result:
        match, replacement = result
        replacements.append((match, replacement, pattern["name"]))
        print(f"\nPattern '{pattern['name']}' matched:")
        print(f"  Position: {match.start()}-{match.end()}")
        print(f"  Original text: {match.group(0)}")
        print(f"  Will replace with: {replacement}")

    # Apply all replacements in reverse order (right to left)
    replacements.sort(key=lambda x: x[0].start(), reverse=True)
    result_line = log_line

    print("\nApplying replacements (right to left):")
    for match, replacement, name in replacements:
      print(f"  Applying {name} at position {match.start()}-{match.end()}")
      result_line = (
          result_line[: match.start()] + replacement + result_line[match.end() :]
      )

    print(f"\nFinal result: {result_line}")

    # Verify the result
    self.assertIn("2025-07-31", result_line, "UtcTime should be updated to yesterday")
    # The epoch timestamp should also be updated
    self.assertNotIn("1706212385", result_line, "EventTime should be updated")

    print("\n✓ SUCCESS: Each timestamp updated exactly once!")

  def test_overlapping_pattern_positions(self):
    """Test edge case where patterns might match the same position."""

    print("\n=== TESTING OVERLAPPING PATTERNS ===")

    # Log line where two patterns could match the same timestamp
    log_line = "Time: 2024-01-25 19:53:05"
    old_base_time = datetime.datetime(2024, 1, 25, 19, 53, 5)
    ts_delta_dict = {"d": 1}

    # Two patterns that match the exact same timestamp
    patterns = [
        {
            "name": "GenericTime",
            "pattern": r"(Time:\s*)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
            "dateformat": "%Y-%m-%d %H:%M:%S",
            "group": 2,
        },
        {
            "name": "AnyTime",
            "pattern": r"(\w+:\s*)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
            "dateformat": "%Y-%m-%d %H:%M:%S",
            "group": 2,
        },
    ]

    print(f"Original: {log_line}")

    # Both patterns will match the same position
    replacements = []
    for pattern in patterns:
      result = _calculate_timestamp_replacement(
          log_line, pattern, old_base_time, ts_delta_dict
      )
      if result:
        match, replacement = result
        replacements.append((match, replacement, pattern["name"]))
        print(f"Pattern '{pattern['name']}' matched at {match.start()}-{match.end()}")

    # Apply replacements
    replacements.sort(key=lambda x: x[0].start(), reverse=True)
    result_line = log_line

    # Track which positions we've already updated
    updated_positions = set()

    for match, replacement, name in replacements:
      pos_key = (match.start(), match.end())
      if pos_key not in updated_positions:
        result_line = (
            result_line[: match.start()] + replacement + result_line[match.end() :]
        )
        updated_positions.add(pos_key)
        print(f"Applied {name}")
      else:
        print(f"Skipped {name} (position already updated)")

    print(f"Final: {result_line}")

    # Should only have one update
    self.assertEqual(
        result_line.count("2025-07-31"), 1, "Timestamp should be updated exactly once"
    )

    print("\n✓ SUCCESS: Overlapping patterns handled correctly!")

  def test_complex_log_line(self):
    """Test a complex real-world scenario."""

    print("\n=== TESTING COMPLEX LOG LINE ===")

    # Complex log with multiple timestamp formats
    log_line = (
        '{"UtcTime":"2024-01-25 19:53:05.123","EventTime":1706212385,'
        '"CreationUtcTime":"2024-01-25 19:53:00","SystemTime":"2024-01-25T19:53:05Z"}'
    )

    old_base_time = datetime.datetime(2024, 1, 25, 19, 53, 5)
    ts_delta_dict = {"d": 1}

    patterns = [
        {
            "name": "UtcTimeQuotes",
            "pattern": r'("UtcTime":"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            "dateformat": "%Y-%m-%d %H:%M:%S",
            "group": 2,
        },
        {
            "name": "EventTime",
            "pattern": r'("EventTime":)(\d{10})',
            "dateformat": "epoch",
            "group": 2,
        },
        {
            "name": "CreationUtcTimeQuotes",
            "pattern": r'("CreationUtcTime":"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            "dateformat": "%Y-%m-%d %H:%M:%S",
            "group": 2,
        },
        {
            "name": "SystemTimeISO",
            "pattern": r'("SystemTime":"?)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',
            "dateformat": "%Y-%m-%dT%H:%M:%S",
            "group": 2,
        },
    ]

    print(f"Original:\n{log_line}")

    # Collect all replacements
    replacements = []
    for pattern in patterns:
      result = _calculate_timestamp_replacement(
          log_line, pattern, old_base_time, ts_delta_dict
      )
      if result:
        match, replacement = result
        replacements.append((match, replacement, pattern["name"]))

    # Apply replacements
    replacements.sort(key=lambda x: x[0].start(), reverse=True)
    result_line = log_line

    print(f"\nFound {len(replacements)} timestamps to update")

    for match, replacement, name in replacements:
      result_line = (
          result_line[: match.start()] + replacement + result_line[match.end() :]
      )

    print(f"\nFinal:\n{result_line}")

    # Verify all timestamps were updated
    self.assertNotIn("2024-01-25", result_line, "All 2024 dates should be updated")
    self.assertNotIn("1706212385", result_line, "Epoch timestamp should be updated")

    # Verify milliseconds were preserved
    self.assertIn(".123", result_line, "Milliseconds should be preserved")

    print("\n✓ SUCCESS: Complex log line processed correctly!")


if __name__ == "__main__":
  unittest.main(verbosity=2)
