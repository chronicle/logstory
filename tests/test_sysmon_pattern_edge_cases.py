# Copyright 2026 Google LLC
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

"""Additional edge case tests for WINDOWS_SYSMON patterns.

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
    assert match is not None, "Pattern should match"

    # Check what was actually captured
    group_num = utc_pattern.get("group", 1)
    captured = match.group(group_num)

    assert (
        captured == "2024-01-25 19:53:06"
    ), "Pattern captures only date/time, truncating milliseconds"

  def test_improved_pattern_with_milliseconds(self):
    """Test an improved pattern that handles milliseconds."""
    test_cases = [
        ('"UtcTime":"2024-01-25 19:53:06.967"', "2024-01-25 19:53:06.967"),
        ('"UtcTime":"2024-01-25 19:53:06"', "2024-01-25 19:53:06"),
        ('"UtcTime": "2024-01-25 19:53:06.123"', "2024-01-25 19:53:06.123"),
        ('"UtcTime" : "2024-01-25 19:53:06"', "2024-01-25 19:53:06"),
    ]

    improved_pattern = (
        r'("UtcTime"\s*:\s*"?)(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{3})?)'
    )
    regex = re.compile(improved_pattern)

    for test_string, expected in test_cases:
      match = regex.search(test_string)
      assert match is not None, f"Should match: {test_string}"
      captured = match.group(2)
      assert captured == expected, "Should capture full timestamp"

  def test_epoch_vs_datetime_distinction(self):
    """Test distinguishing between epoch and datetime timestamps."""
    test_line = (
        '{"EventTime":1706212385,"UtcTime":"2024-01-25'
        ' 19:53:05.701","EventReceivedTime":1706212387,"Next":1}'
    )

    epoch_fields = []
    datetime_fields = []

    for pattern in self.sysmon_patterns:
      regex = re.compile(pattern["pattern"])
      match = regex.search(test_line)

      if match:
        if pattern.get("dateformat") == "epoch":
          epoch_fields.append(pattern["name"])
        else:
          datetime_fields.append(pattern["name"])

    # EventTime and EventReceivedTime should be epoch
    assert "EventReceivedTime" in epoch_fields, "EventReceivedTime should be epoch"
    assert "EventTime" in epoch_fields, "EventTime should be epoch"

  def test_overlapping_field_names(self):
    """Test handling of fields with specific pattern names."""
    test_line = (
        '{"UtcTime":"2024-01-25'
        ' 19:53:05.701","Image":"C:\\Windows\\system32\\wbem\\wmiprvse.exe","CreationUtcTime":"2022-09-20'
        ' 19:51:50.859"}'
    )

    # Filter to specific patterns (excluding the generic fallback)
    specific_patterns = [
        p for p in self.sysmon_patterns if "generic" not in p["name"].lower()
    ]

    matches = []
    for pattern in specific_patterns:
      regex = re.compile(pattern["pattern"])
      for match in regex.finditer(test_line):
        matches.append({
            "pattern": pattern["name"],
            "start": match.start(),
            "end": match.end(),
            "text": match.group(0),
            "value": match.group(pattern.get("group", 1)),
        })

    # Group by extracted value to check specific patterns do not conflict
    values = {}
    for match in matches:
      value = match["value"]
      if value not in values:
        values[value] = []
      values[value].append(match["pattern"])

    for value, patterns in values.items():
      assert (
          len(patterns) == 1
      ), f"Value '{value}' matched by multiple specific patterns: {patterns}"

  def test_json_vs_xml_format_handling(self):
    """Test that patterns handle both JSON and XML Sysmon formats."""
    json_patterns = [p for p in self.sysmon_patterns if '"' in p["pattern"]]
    xml_patterns = [
        p
        for p in self.sysmon_patterns
        if '"' not in p["pattern"] or "optional" in p.get("description", "")
    ]

    assert len(json_patterns) > 0, "Should have JSON format patterns"
    assert len(xml_patterns) > 0, "Should have XML format patterns"

  def test_pattern_specificity(self):
    """Test that specific patterns are specific enough to avoid false matches."""
    false_positive_cases = [
        '"NotATimeField":"2024-01-25 19:53:06"',
        '"TimeZone":"UTC"',
        '"Runtime":"120 seconds"',
    ]

    specific_patterns = [
        p for p in self.sysmon_patterns if "generic" not in p["name"].lower()
    ]

    for test_string in false_positive_cases:
      matched = False
      for pattern in specific_patterns:
        regex = re.compile(pattern["pattern"])
        if regex.search(test_string):
          matched = True
          break

      assert (
          not matched
      ), f"Specific pattern incorrectly matched non-timestamp field: {test_string}"


if __name__ == "__main__":
  unittest.main(verbosity=2)
