import yaml

def validate_base_time(filepath):
    """
    Reads a YAML file, checks each entry, and ensures it has exactly one
    base_time: true timestamp in its timestamps list.

    Args:
        filepath: The path to the YAML file.

    Raises:
        ValueError: If an entry has zero or more than one base_time: true timestamp.
    """
    try:
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filepath}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")

    if not isinstance(data, dict):
        raise ValueError("YAML file should contain a dictionary at the root level.")

    for entry_name, entry_data in data.items():
        if 'timestamps' not in entry_data:
            print(f"Warning: Entry '{entry_name}' has no 'timestamps' list. Skipping.")
            continue

        timestamps = entry_data['timestamps']
        base_time_count = 0

        for timestamp in timestamps:
            if 'base_time' in timestamp and timestamp['base_time']:
                base_time_count += 1

        if base_time_count == 0:
            raise ValueError(f"Entry '{entry_name}' has no base_time: true timestamp.")
        elif base_time_count > 1:
            raise ValueError(f"Entry '{entry_name}' has multiple base_time: true timestamps ({base_time_count}).")
        else:
            print(f"Entry '{entry_name}' has exactly one base_time: true timestamp. OK")


# Example usage (replace with the actual file path):
filepaths = [
    "../src/logstory/logtypes_entities_timestamps.yaml",
    "../src/logstory/logtypes_events_timestamps.yaml",
]
for filepath in filepaths:
  try:
      validate_base_time(filepath)
  except (ValueError, FileNotFoundError) as e:
      print(f"Error: {e}")
