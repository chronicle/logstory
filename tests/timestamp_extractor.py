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
Timestamp Extractor Module

Reads the last line of a log file, extracts timestamps using regex patterns from
logtypes_entities_timestamps.yaml, converts them to Python datetimes, and visualizes them.
"""

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def load_timestamp_patterns(yaml_file: str) -> dict[str, Any]:
  """Load timestamp patterns from YAML configuration file."""
  with open(yaml_file) as f:
    return yaml.safe_load(f)


def read_last_line(filepath: str) -> str:
  """Read the last line of a file."""
  try:
    with open(filepath, encoding="utf-8") as f:
      lines = f.readlines()

      # Return the last non-empty line
      for line in reversed(lines):
        if line.strip():
          return line.strip()

      return ""
  except Exception as e:
    print(f"Error reading file {filepath}: {e}")
    return ""


def windows_filetime_to_datetime(filetime: int) -> datetime:
  """Convert Windows FILETIME to datetime."""
  # Windows FILETIME epoch starts at 1601-01-01
  # It's in 100-nanosecond intervals since then
  epoch_start = datetime(1601, 1, 1, tzinfo=UTC)
  delta_seconds = filetime / 10_000_000  # Convert to seconds
  from datetime import timedelta

  return epoch_start + timedelta(seconds=delta_seconds)


def extract_timestamps_from_log_type(
    line: str, log_type: str, patterns_config: dict[str, Any]
) -> list[tuple[str, datetime]]:
  """Extract timestamps from a line using patterns for a specific log type."""
  extracted_timestamps = []

  # Get the specific log type configuration
  if log_type not in patterns_config or "timestamps" not in patterns_config[log_type]:
    print(f"No timestamp patterns found for log type: {log_type}")
    return extracted_timestamps

  config = patterns_config[log_type]

  for timestamp_pattern in config["timestamps"]:
    pattern = timestamp_pattern["pattern"]
    group = timestamp_pattern.get("group", 1)
    dateformat = timestamp_pattern["dateformat"]
    name = timestamp_pattern["name"]

    # Find all matches for this pattern
    matches = re.finditer(pattern, line)
    match_count = 0

    for match in matches:
      match_count += 1
      try:
        timestamp_str = match.group(group)

        # Convert based on format type
        if dateformat == "epoch":
          # Unix epoch timestamp
          timestamp = datetime.fromtimestamp(int(timestamp_str), tz=UTC)
        elif dateformat == "filetime":
          # Windows FILETIME
          timestamp = windows_filetime_to_datetime(int(timestamp_str))
        else:
          # Standard datetime format
          timestamp = datetime.strptime(timestamp_str, dateformat)
          # Add UTC timezone if not present
          if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        extracted_timestamps.append((name, timestamp))

      except (ValueError, IndexError) as e:
        # Skip invalid timestamps
        print(f"Failed to parse timestamp for {name}: {e}")
        continue

    # Optional: uncomment for debugging pattern matching issues
    # if match_count == 0:
    #   print(f"No matches found for pattern {name}: {pattern}")

  return extracted_timestamps


def visualize_timestamps(timestamps: list[tuple[str, datetime]], log_type: str = ""):
  """Create a text-based visualization of the extracted timestamps."""
  if not timestamps:
    print("No timestamps found to visualize.")
    return

  log_label = f" from {log_type} log" if log_type else ""
  print(f"\nExtracted {len(timestamps)} timestamps{log_label}:")
  print("=" * 60)

  # Sort timestamps by datetime
  sorted_timestamps = sorted(timestamps, key=lambda x: x[1])

  # Find the earliest and latest timestamps for range visualization
  if len(sorted_timestamps) > 1:
    earliest = sorted_timestamps[0][1]
    latest = sorted_timestamps[-1][1]
    time_range = latest - earliest
    print(f"Time range: {time_range}")
    print()

  # Find the longest name for proper column alignment
  max_name_length = max(len(name) for name, _ in sorted_timestamps)

  # Display each timestamp with proper alignment
  for i, (name, dt) in enumerate(sorted_timestamps, 1):
    print(f"{i:2d}. {name:<{max_name_length}} | {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")

  print("=" * 60)


def main():
  """Main function to run the timestamp extractor."""
  parser = argparse.ArgumentParser(
      description="Extract and visualize timestamps from log files using YAML patterns"
  )
  parser.add_argument(
      "--file",
      "-f",
      default="/tmp/var/log/logstory/WINDOWS_AD.log",
      help="Path to log file (default: /tmp/var/log/logstory/WINDOWS_AD.log)",
  )
  parser.add_argument(
      "--config",
      "-c",
      default="src/logstory/logtypes_entities_timestamps.yaml",
      help="Path to timestamp patterns YAML file",
  )

  args = parser.parse_args()

  # Check if files exist
  if not Path(args.file).exists():
    print(f"Log file not found: {args.file}")
    return

  if not Path(args.config).exists():
    print(f"Config file not found: {args.config}")
    return

  # Load configuration
  patterns_config = load_timestamp_patterns(args.config)

  # Read last line
  last_line = read_last_line(args.file)
  if not last_line:
    print(f"No content found in {args.file}")
    return

  print(f"Processing last line from {args.file}:")
  print(f"Line length: {len(last_line)} characters")
  print(f"Line: {last_line[:200]}..." if len(last_line) > 200 else f"Line: {last_line}")
  print()

  # Extract log type from filename
  log_filename = Path(args.file).stem  # Gets filename without extension
  log_type = log_filename.upper()  # Convert to uppercase to match YAML keys

  print(f"Detected log type: {log_type}")

  # Extract timestamps using detected log type
  timestamps = extract_timestamps_from_log_type(last_line, log_type, patterns_config)

  if not timestamps:
    print(f"No {log_type} timestamps found in the last line.")
    return

  # Visualize timestamps
  visualize_timestamps(timestamps, log_type)


if __name__ == "__main__":
  main()
