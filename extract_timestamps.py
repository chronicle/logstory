#!/usr/bin/env python3

import argparse
import re


def extract_timestamps_from_last_line(file_path):
  """Extract all epoch timestamps from the last line of a file."""
  try:
    with open(file_path, "r") as f:
      # Read all lines and get the last one
      lines = f.readlines()
      if not lines:
        print("File is empty")
        return

      last_line = lines[-1].strip()

      # Pattern to match epoch timestamps (10-13 digits)
      timestamp_pattern = r"\b\d{10,13}\b"

      # Find all matches
      timestamps = re.findall(timestamp_pattern, last_line)

      # Filter out Windows FILETIME timestamps
      filtered_timestamps = []
      for timestamp in timestamps:
        ts_int = int(timestamp)
        # Windows FILETIME: typically 17-18 digits, starts with 13xxx
        # Unix epoch seconds: 10 digits (1970-2038)
        # Unix epoch milliseconds: 13 digits (1970-2038)
        if len(timestamp) >= 17 or (
            len(timestamp) == 13
            and str(ts_int).startswith("13")
            and ts_int > 133000000000000
        ):
          # Skip Windows FILETIME format
          continue
        filtered_timestamps.append(timestamp)

      # Print each timestamp on a separate line
      for timestamp in filtered_timestamps:
        print(timestamp)

  except FileNotFoundError:
    print(f"File not found: {file_path}")
  except Exception as e:
    print(f"Error reading file: {e}")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description="Extract epoch timestamps from the last line of a file"
  )
  parser.add_argument(
      "--input-file",
      default="/tmp/var/log/logstory/WINDOWS_AD.log",
      help="Path to the input file (default: /tmp/var/log/logstory/WINDOWS_AD.log)",
  )

  args = parser.parse_args()
  extract_timestamps_from_last_line(args.input_file)
