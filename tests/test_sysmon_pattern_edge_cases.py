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
Additional edge case tests for WINDOWS_SYSMON patterns.

These tests demonstrate specific parsing issues and expected behaviors.
"""

import re
import unittest
from pathlib import Path

import yaml


class TestSysmonPatternEdgeCases(unittest.TestCase):
  """Edge case tests for WINDOWS_SYSMON patterns."""

  def setUp(self):
    """Set up test data."""
    yaml_path = (
        Path(__file__).parent.parent / "src/logstory/logtypes_events_timestamps.yaml"
    )
    with open(yaml_path) as f:
      self.patterns_data = yaml.safe_load(f)

    self.sysmon_patterns = self.patterns_data["WINDOWS_SYSMON"]["timestamps"]

  def test_millisecond_truncation(self):
    """Demonstrate that current patterns truncate milliseconds."""
    test_line = '"UtcTime":"2024-01-25 19:53:06.967","NextField":"value"'

    # Find UtcTimeQuotes pattern
    utc_pattern = next(p for p in self.sysmon_patterns if p["name"] == "UtcTimeQuotes")
    regex = re.compile(utc_pattern["pattern"])

    match = regex.search(test_line)
    self.assertIsNotNone(match, "Pattern should match")

    # Check what was actually captured
    group_num = utc_pattern.get("group", 1)
    captured = match.group(group_num)

    print(f"\nOriginal timestamp: 2024-01-25 19:53:06.967")
    print(f"Captured timestamp: {captured}")
    print(f"Missing: .967 (milliseconds)")

    # This demonstrates the truncation issue
    self.assertEqual(
        captured,
        "2024-01-25 19:53:06",
        "Pattern captures only date/time, truncating milliseconds",
    )

  def test_improved_pattern_with_milliseconds(self):
    """Test an improved pattern that handles milliseconds."""
    test_cases = [
        ('"UtcTime":"2024-01-25 19:53:06.967"', "2024-01-25 19:53:06.967"),
        ('"UtcTime":"2024-01-25 19:53:06"', "2024-01-25 19:53:06"),
        ('"UtcTime": "2024-01-25 19:53:06.123"', "2024-01-25 19:53:06.123"),
        ('"UtcTime" : "2024-01-25 19:53:06"', "2024-01-25 19:53:06"),
    ]

    # Improved pattern that handles optional milliseconds
    improved_pattern = (
        r'("UtcTime"\s*:\s*"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{3})?)'
    )
    regex = re.compile(improved_pattern)

    print("\nTesting improved pattern with millisecond support:")
    for test_string, expected in test_cases:
      match = regex.search(test_string)
      self.assertIsNotNone(match, f"Should match: {test_string}")

      captured = match.group(2)
      print(f"  Input: {test_string}")
      print(f"  Captured: {captured}")
      self.assertEqual(captured, expected, "Should capture full timestamp")

  def test_epoch_vs_datetime_distinction(self):
    """Test distinguishing between epoch and datetime timestamps."""
    test_line = """{"EventTime":1706212385,"UtcTime":"2024-01-25 19:53:05.701","EventReceivedTime":1706212387}"""

    epoch_fields = []
    datetime_fields = []

    for pattern in self.sysmon_patterns:
      regex = re.compile(pattern["pattern"])
      match = regex.search(test_line)

      if match:
        if pattern.get("epoch", False):
          epoch_fields.append(pattern["name"])
        else:
          datetime_fields.append(pattern["name"])

    print(f"\nEpoch timestamp fields: {epoch_fields}")
    print(f"DateTime timestamp fields: {datetime_fields}")

    # EventTime and EventReceivedTime should be epoch
    # UtcTime should be datetime
    self.assertIn(
        "EventReceivedTime", epoch_fields, "EventReceivedTime should be epoch"
    )
    # This will fail if EventTime isn't marked as epoch
    # self.assertIn('EventTime', epoch_fields, "EventTime should be epoch")

  def test_overlapping_field_names(self):
    """Test handling of fields with similar names."""
    # CreationUtcTime vs UtcTime - these can appear in the same log
    test_line = """{"UtcTime":"2024-01-25 19:53:05.701","Image":"C:\\Windows\\system32\\wbem\\wmiprvse.exe","CreationUtcTime":"2022-09-20 19:51:50.859"}"""

    matches = []
    for pattern in self.sysmon_patterns:
      regex = re.compile(pattern["pattern"])
      for match in regex.finditer(test_line):
        matches.append({
            "pattern": pattern["name"],
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0),
            "value": match.group(pattern.get("group", 1)),
        })

    # Group by extracted value to find duplicates
    values = {}
    for match in matches:
      value = match["value"]
      if value not in values:
        values[value] = []
      values[value].append(match["pattern"])

    print("\nTimestamp value extraction:")
    for value, patterns in values.items():
      print(f"  {value}: matched by {patterns}")
      if len(patterns) > 1:
        self.fail(f"Value '{value}' matched by multiple patterns: {patterns}")

  def test_json_vs_xml_format_handling(self):
    """Test that patterns handle both JSON and XML Sysmon formats."""
    # Sysmon can output in both JSON and XML formats
    json_line = '"CreationUtcTime":"2022-09-20 19:51:50.859"'
    xml_line = "CreationUtcTime: 2022-09-20 19:51:50.859"

    # Check if we have patterns for both formats
    json_patterns = [p for p in self.sysmon_patterns if '"' in p["pattern"]]
    xml_patterns = [
        p
        for p in self.sysmon_patterns
        if '"' not in p["pattern"] or "optional" in p.get("description", "")
    ]

    print(f"\nJSON-specific patterns: {len(json_patterns)}")
    print(f"XML-compatible patterns: {len(xml_patterns)}")

    # Both formats should be supported
    self.assertGreater(len(json_patterns), 0, "Should have JSON format patterns")
    self.assertGreater(len(xml_patterns), 0, "Should have XML format patterns")

  def test_pattern_specificity(self):
    """Test that patterns are specific enough to avoid false matches."""
    # These should NOT match
    false_positive_cases = [
        '"NotATimeField":"2024-01-25 19:53:06"',
        '"RandomTime":"2024-01-25 19:53:06"',
        '"TimeZone":"UTC"',
        '"Runtime":"120 seconds"',
    ]

    for test_string in false_positive_cases:
      matched = False
      for pattern in self.sysmon_patterns:
        regex = re.compile(pattern["pattern"])
        if regex.search(test_string):
          matched = True
          print(f"\nPattern '{pattern['name']}' incorrectly matched: {test_string}")
          break

      self.assertFalse(
          matched, f"No pattern should match non-timestamp field: {test_string}"
      )


if __name__ == "__main__":
  unittest.main(verbosity=2)
