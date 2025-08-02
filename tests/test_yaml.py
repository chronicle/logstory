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

import yaml


def validate_base_time(filepath, data=None):
  """
  Reads a YAML file, checks each entry, and ensures it has exactly one
  base_time: true timestamp in its timestamps list.

  Args:
      filepath: The path to the YAML file.
      data: Optional pre-loaded data (for internal use).

  Raises:
      ValueError: If an entry has zero or more than one base_time: true timestamp.
  """
  if data is None:
    try:
      with open(filepath) as f:
        data = yaml.safe_load(f)
    except FileNotFoundError:
      raise FileNotFoundError(f"File not found: {filepath}")
    except yaml.YAMLError as e:
      raise ValueError(f"Error parsing YAML file: {e}")

  if not isinstance(data, dict):
    raise ValueError("YAML file should contain a dictionary at the root level.")

  for entry_name, entry_data in data.items():
    if "timestamps" not in entry_data:
      print(f"Warning: Entry '{entry_name}' has no 'timestamps' list. Skipping.")
      continue

    timestamps = entry_data["timestamps"]
    base_time_count = 0

    for timestamp in timestamps:
      if "base_time" in timestamp and timestamp["base_time"]:
        base_time_count += 1

    if base_time_count == 0:
      raise ValueError(f"Entry '{entry_name}' has no base_time: true timestamp.")
    if base_time_count > 1:
      raise ValueError(
          f"Entry '{entry_name}' has multiple base_time: true timestamps"
          f" ({base_time_count})."
      )
    print(f"Entry '{entry_name}' has exactly one base_time: true timestamp. OK")


def validate_base_time_format(filepath):
  """
  Reads a YAML file, checks each entry, and ensures that timestamps with
  base_time: true have the required dateformat field.

  Args:
      filepath: The path to the YAML file.

  Raises:
      ValueError: If a base_time: true timestamp has missing or invalid dateformat.
  """
  try:
    with open(filepath) as f:
      data = yaml.safe_load(f)
  except FileNotFoundError:
    raise FileNotFoundError(f"File not found: {filepath}")
  except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML file: {e}")

  if not isinstance(data, dict):
    raise ValueError("YAML file should contain a dictionary at the root level.")

  for entry_name, entry_data in data.items():
    if "timestamps" not in entry_data:
      print(f"Warning: Entry '{entry_name}' has no 'timestamps' list. Skipping.")
      continue

    timestamps = entry_data["timestamps"]

    for timestamp in timestamps:
      if "base_time" in timestamp and timestamp["base_time"]:
        has_dateformat = "dateformat" in timestamp

        if not has_dateformat:
          raise ValueError(
              f"Entry '{entry_name}' has base_time: true timestamp without 'dateformat'"
              " field."
          )

        dateformat = timestamp["dateformat"]
        if dateformat == 'epoch':
          format_type = "epoch"
        elif dateformat == 'windowsfiletime':
          format_type = "windowsfiletime"
        else:
          format_type = "dateformat"
        print(f"Entry '{entry_name}' base_time timestamp uses '{format_type}'. OK")


def validate_timestamp_required_fields(filepath):
  """
  Validates that each timestamp entry has all required fields.

  Args:
      filepath: The path to the YAML file.

  Raises:
      ValueError: If any timestamp is missing required fields.
  """
  try:
    with open(filepath) as f:
      data = yaml.safe_load(f)
  except FileNotFoundError:
    raise FileNotFoundError(f"File not found: {filepath}")
  except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML file: {e}")

  if not isinstance(data, dict):
    raise ValueError("YAML file should contain a dictionary at the root level.")

  base_required_fields = ["name", "pattern", "dateformat", "group"]

  for entry_name, entry_data in data.items():
    if "timestamps" not in entry_data:
      continue

    timestamps = entry_data["timestamps"]
    for i, timestamp in enumerate(timestamps):
      # Check base required fields
      for field in base_required_fields:
        if field not in timestamp:
          raise ValueError(
              f"Entry '{entry_name}' timestamp {i} missing required field: '{field}'"
          )

      # Check dateformat requirements
      dateformat = timestamp.get("dateformat")
      if not dateformat:
        raise ValueError(
            f"Entry '{entry_name}' timestamp {i}: missing required dateformat field"
        )

      print(f"Entry '{entry_name}' timestamp {i} has all required fields. OK")


def validate_epoch_dateformat_consistency(filepath):
  """
  Validates that dateformat fields are valid.
  All timestamps should have a dateformat field with valid values.

  Args:
      filepath: The path to the YAML file.

  Raises:
      ValueError: If dateformat is invalid.
  """
  try:
    with open(filepath) as f:
      data = yaml.safe_load(f)
  except FileNotFoundError:
    raise FileNotFoundError(f"File not found: {filepath}")
  except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML file: {e}")

  if not isinstance(data, dict):
    raise ValueError("YAML file should contain a dictionary at the root level.")

  for entry_name, entry_data in data.items():
    if "timestamps" not in entry_data:
      continue

    timestamps = entry_data["timestamps"]
    for i, timestamp in enumerate(timestamps):
      dateformat = timestamp.get("dateformat")
      if not dateformat:
        raise ValueError(
            f"Entry '{entry_name}' timestamp {i}: missing dateformat field"
        )

      # Validate dateformat values
      valid_magic_formats = ['epoch', 'windowsfiletime']
      if dateformat not in valid_magic_formats and not isinstance(dateformat, str):
        raise ValueError(
            f"Entry '{entry_name}' timestamp {i}: dateformat must be a string"
        )

      print(f"Entry '{entry_name}' timestamp {i} dateformat is valid. OK")


def validate_field_types(filepath):
  """
  Validates that fields have correct data types.

  Args:
      filepath: The path to the YAML file.

  Raises:
      ValueError: If any field has incorrect type.
  """
  try:
    with open(filepath) as f:
      data = yaml.safe_load(f)
  except FileNotFoundError:
    raise FileNotFoundError(f"File not found: {filepath}")
  except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML file: {e}")

  if not isinstance(data, dict):
    raise ValueError("YAML file should contain a dictionary at the root level.")

  for entry_name, entry_data in data.items():
    if "timestamps" not in entry_data:
      continue

    timestamps = entry_data["timestamps"]
    for i, timestamp in enumerate(timestamps):
      # Check string fields
      for field in ["name", "dateformat", "pattern"]:
        if field in timestamp and not isinstance(timestamp[field], str):
          raise ValueError(
              f"Entry '{entry_name}' timestamp {i}: '{field}' should be string, got"
              f" {type(timestamp[field])}"
          )

      # Check boolean fields
      for field in ["base_time"]:
        if field in timestamp and not isinstance(timestamp[field], bool):
          raise ValueError(
              f"Entry '{entry_name}' timestamp {i}: '{field}' should be boolean, got"
              f" {type(timestamp[field])}"
          )

      # Check integer fields
      for field in ["group"]:
        if field in timestamp and not isinstance(timestamp[field], int):
          raise ValueError(
              f"Entry '{entry_name}' timestamp {i}: '{field}' should be integer, got"
              f" {type(timestamp[field])}"
          )
        if field in timestamp and timestamp[field] < 0:
          raise ValueError(
              f"Entry '{entry_name}' timestamp {i}: '{field}' should be positive"
              f" integer, got {timestamp[field]}"
          )

      print(f"Entry '{entry_name}' timestamp {i} field types are correct. OK")


def _validate_single_log_type(log_type: str, entry_data: dict) -> None:
  """
  Validates a single log type entry for all consistency rules.

  Args:
      log_type: The log type name.
      entry_data: The log type's configuration data.

  Raises:
      ValueError: If any validation fails.
  """
  if "timestamps" not in entry_data:
    raise ValueError(f"Log type '{log_type}' missing 'timestamps' configuration")

  timestamps = entry_data["timestamps"]
  base_time_count = 0

  for i, timestamp in enumerate(timestamps):
    # Check required fields
    required_fields = ["name", "pattern", "dateformat", "group"]
    for field in required_fields:
      if field not in timestamp:
        raise ValueError(f"timestamp {i} missing required field: '{field}'")

    # Check base_time count
    if timestamp.get("base_time"):
      base_time_count += 1

    # Check dateformat is valid
    dateformat = timestamp.get("dateformat")
    if not dateformat:
      raise ValueError(f"timestamp {i} ({timestamp['name']}): missing dateformat field")

    # Check field types
    if not isinstance(timestamp.get("name"), str):
      raise ValueError(f"timestamp {i}: 'name' must be string")
    if not isinstance(timestamp.get("pattern"), str):
      raise ValueError(f"timestamp {i}: 'pattern' must be string")
    if not isinstance(timestamp.get("dateformat"), str):
      raise ValueError(f"timestamp {i}: 'dateformat' must be string")
    if not isinstance(timestamp.get("group"), int) or timestamp.get("group") < 1:
      raise ValueError(f"timestamp {i}: 'group' must be positive integer")

  # Check base_time count
  if base_time_count == 0:
    raise ValueError("has no base_time: true timestamp")
  if base_time_count > 1:
    raise ValueError(f"has multiple base_time: true timestamps ({base_time_count})")


def validate_all_log_types(filepath):
  """
  Validates ALL log types in the YAML file for comprehensive testing.
  This ensures the entire configuration file is clean and consistent.

  Args:
      filepath: The path to the YAML file.

  Raises:
      ValueError: If any log type has configuration issues.
  """
  try:
    with open(filepath) as f:
      data = yaml.safe_load(f)
  except FileNotFoundError:
    raise FileNotFoundError(f"File not found: {filepath}")
  except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML file: {e}")

  if not isinstance(data, dict):
    raise ValueError("YAML file should contain a dictionary at the root level.")

  total_log_types = len(data)
  validated_count = 0

  for log_type, entry_data in data.items():
    if "timestamps" not in entry_data:
      print(f"Warning: Log type '{log_type}' has no 'timestamps' list. Skipping.")
      continue

    # Run all the individual validation functions for this log type
    single_entry_data = {log_type: entry_data}

    try:
      # Validate this single log type
      _validate_single_log_type(log_type, entry_data)
      validated_count += 1
      print(f"Log type '{log_type}' passed all validations. OK")
    except ValueError as e:
      raise ValueError(f"Log type '{log_type}' failed validation: {e}")

  print(
      f"All {validated_count}/{total_log_types} log types passed comprehensive"
      " validation!"
  )


# Example usage (replace with the actual file path):
filepaths = [
    "../src/logstory/logtypes_entities_timestamps.yaml",
    "../src/logstory/logtypes_events_timestamps.yaml",
]
for filepath in filepaths:
  try:
    print(f"\n=== Validating {filepath} ===")

    # Individual validation functions for detailed output
    validate_base_time(filepath)
    validate_base_time_format(filepath)
    validate_timestamp_required_fields(filepath)
    validate_epoch_dateformat_consistency(filepath)
    validate_field_types(filepath)

    # Comprehensive validation for all log types
    print("\n--- Comprehensive validation for all log types ---")
    validate_all_log_types(filepath)

    print(f"\n✅ All validations passed for {filepath}")
  except (ValueError, FileNotFoundError) as e:
    print(f"\n❌ Error in {filepath}: {e}")
