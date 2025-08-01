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

"""
Corrected unit tests for WINDOWS_SYSMON timestamp patterns.

This module tests the actual behavior where patterns capture only what they need
and leave the rest (like milliseconds) untouched.
"""

import re
import unittest
from pathlib import Path

import yaml


class TestWindowsSysmonPatternsCorrected(unittest.TestCase):
  """Corrected test cases for WINDOWS_SYSMON timestamp patterns."""

  @classmethod
  def setUpClass(cls):
    """Load test data once for all tests."""
    yaml_path = (
        Path(__file__).parent.parent / "src/logstory/logtypes_events_timestamps.yaml"
    )
    with open(yaml_path) as f:
      cls.patterns_data = yaml.safe_load(f)

    cls.sysmon_config = cls.patterns_data.get("WINDOWS_SYSMON", {})
    cls.sysmon_patterns = cls.sysmon_config.get("timestamps", [])

    log_path = (
        Path(__file__).parent.parent
        / "src/logstory/usecases/THW2/EVENTS/WINDOWS_SYSMON.log"
    )
    with open(log_path) as f:
      cls.sample_log_line = f.readline().strip()

  def test_utc_time_pattern_captures_correctly(self):
    """Test that UtcTime pattern captures date/time, leaving milliseconds untouched."""
    # The log contains "UtcTime":"2024-01-25 19:53:06.967"
    # Pattern should match and capture "2024-01-25 19:53:06"

    utc_time_pattern = None
    for pattern in self.sysmon_patterns:
      if pattern["name"] == "UtcTimeQuotes":
        utc_time_pattern = pattern
        break

    self.assertIsNotNone(utc_time_pattern, "UtcTimeQuotes pattern not found")

    # Test with a timestamp that has milliseconds
    test_string = '"UtcTime":"2024-01-25 19:53:06.967"'
    regex = re.compile(utc_time_pattern["pattern"])
    match = regex.search(test_string)

    self.assertIsNotNone(match, "Pattern should match timestamps with milliseconds")

    # Check what was captured
    group_num = utc_time_pattern.get("group", 1)
    captured_timestamp = match.group(group_num)

    print(f"\nOriginal: {test_string}")
    print(f"Pattern captured: {captured_timestamp}")
    print(f"Milliseconds '.967' remain untouched in original")

    # Verify it captures only up to seconds
    self.assertEqual(
        captured_timestamp,
        "2024-01-25 19:53:06",
        "Should capture only date and time up to seconds",
    )

  def test_dateformat_matches_capture(self):
    """Test that dateformat aligns with what the pattern captures."""
    for pattern in self.sysmon_patterns:
      # Skip non-strftime dateformats
      if pattern.get("dateformat") in ["epoch", "windowsfiletime"]:
        continue

      # Check if dateformat exists
      dateformat = pattern.get("dateformat")
      self.assertIsNotNone(
          dateformat, f"Pattern '{pattern['name']}' missing dateformat"
      )

      # For patterns capturing YYYY-MM-DD HH:MM:SS
      if "UtcTime" in pattern["name"] and "Quotes" in pattern["name"]:
        expected_format = "%Y-%m-%d %H:%M:%S"
        self.assertEqual(
            dateformat,
            expected_format,
            f"Pattern '{pattern['name']}' dateformat should match captured format",
        )

  def test_millisecond_preservation_behavior(self):
    """Test that patterns work correctly with timestamps containing milliseconds."""
    test_cases = [
        {
            "input": '"UtcTime":"2024-01-25 19:53:06.967"',
            "pattern_name": "UtcTimeQuotes",
            "expected_capture": "2024-01-25 19:53:06",
            "preserved": '.967"',
        },
        {
            "input": '"CreationUtcTime":"2022-09-20 19:51:50.450"',
            "pattern_name": "CreationUtcTimeQuotes",
            "expected_capture": "2022-09-20 19:51:50",
            "preserved": '.450"',
        },
    ]

    for test_case in test_cases:
      pattern = next(
          (p for p in self.sysmon_patterns if p["name"] == test_case["pattern_name"]),
          None,
      )

      if not pattern:
        continue

      regex = re.compile(pattern["pattern"])
      match = regex.search(test_case["input"])

      self.assertIsNotNone(
          match,
          f"Pattern {test_case['pattern_name']} should match {test_case['input']}",
      )

      group_num = pattern.get("group", 1)
      captured = match.group(group_num)

      self.assertEqual(
          captured,
          test_case["expected_capture"],
          f"Should capture only the date/time portion",
      )

      # Verify the pattern doesn't capture the milliseconds
      self.assertNotIn(
          ".", captured, "Captured portion should not include milliseconds"
      )

  def test_timestamp_dateformat_types(self):
    """Test that timestamps use appropriate dateformat types."""
    # Check different timestamp types
    for pattern in self.sysmon_patterns:
      dateformat = pattern.get("dateformat", "")
      pattern_regex = pattern.get("pattern", "")

      # Epoch timestamps (10 or 13 digits)
      if (
          re.search(r"\\d\{10\}|\\d\{13\}", pattern_regex)
          and "EventTime" in pattern["name"]
      ):
        self.assertEqual(
            dateformat,
            "epoch",
            f"{pattern['name']} capturing 10/13 digits should use dateformat: 'epoch'",
        )

      # Windows FileTime (18 digits)
      elif re.search(r"\\d\{18\}", pattern_regex):
        self.assertEqual(
            dateformat,
            "windowsfiletime",
            f"{pattern['name']} capturing 18 digits should use dateformat:"
            " 'windowsfiletime'",
        )

      # Human-readable timestamps should use strftime format
      elif re.search(r"\\d\{4\}-\\d\{2\}-\\d\{2\}", pattern_regex):
        self.assertTrue(
            dateformat.startswith("%") or dateformat in ["epoch", "windowsfiletime"],
            f"{pattern['name']} should have a valid dateformat",
        )

    # Specific checks for known epoch fields
    epoch_fields = ["EventTime", "EventReceivedTime"]
    for field_name in epoch_fields:
      patterns = [
          p
          for p in self.sysmon_patterns
          if field_name in p["name"] and "UTC" not in p["name"]
      ]
      self.assertTrue(len(patterns) > 0, f"No pattern found for {field_name}")

      for pattern in patterns:
        if re.search(r"\\d\{10\}", pattern["pattern"]):
          self.assertEqual(
              pattern.get("dateformat"),
              "epoch",
              f"{pattern['name']} should have dateformat: 'epoch'",
          )

  def test_pattern_specificity_real_log(self):
    """Test patterns against the actual log line."""
    # Count matches for each pattern
    match_counts = {}

    for pattern in self.sysmon_patterns:
      regex = re.compile(pattern["pattern"])
      matches = list(regex.finditer(self.sample_log_line))
      match_counts[pattern["name"]] = len(matches)

      if matches:
        print(f"\nPattern '{pattern['name']}' found {len(matches)} match(es):")
        for match in matches[:2]:  # Show first 2 matches
          group_num = pattern.get("group", 1)
          if group_num <= len(match.groups()):
            print(f"  Captured: {match.group(group_num)}")

    # Each pattern should match at most once (except for certain cases)
    for pattern_name, count in match_counts.items():
      if count > 1 and "syslog" not in pattern_name.lower():
        self.fail(
            f"Pattern '{pattern_name}' matched {count} times - may be too generic"
        )

  def test_base_time_and_dateformat_alignment(self):
    """Test that base_time pattern has correct dateformat."""
    base_time_patterns = [p for p in self.sysmon_patterns if p.get("base_time", False)]

    self.assertEqual(
        len(base_time_patterns), 1, "Should have exactly one base_time pattern"
    )

    if base_time_patterns:
      base_pattern = base_time_patterns[0]

      # Test against actual log
      regex = re.compile(base_pattern["pattern"])
      match = regex.search(self.sample_log_line)

      if match:
        group_num = base_pattern.get("group", 1)
        captured = match.group(group_num)
        dateformat = base_pattern.get("dateformat", "")

        print(f"\nBase time pattern '{base_pattern['name']}':")
        print(f"  Captured: {captured}")
        print(f"  Dateformat: {dateformat}")

        # Verify dateformat matches the captured format
        if " " in captured and "T" not in captured:
          self.assertIn(
              " ",
              dateformat.replace("%", ""),
              "Dateformat should use space separator like captured value",
          )

        if "T" in captured:
          self.assertIn(
              "T",
              dateformat,
              "Dateformat should include T separator like captured value",
          )


if __name__ == "__main__":
  unittest.main(verbosity=2)
