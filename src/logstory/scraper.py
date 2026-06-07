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

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""SecOps Log Scraper for Logstory.

Automatically queries a Google SecOps tenant for raw logs, normalizes and groups
them by type, saves them into the correct Logstory folder layout, and generates
proper documentation.
"""

import base64
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def _import_secops() -> tuple[Any, Any, Any]:
  """Import secops modules dynamically to avoid hard dependency.

  Returns:
    Tuple containing (SecOpsClient, load_config, APIError).

  Raises:
    ImportError: If the 'secops' package is not installed.
  """
  try:
    from secops import SecOpsClient
    from secops.cli.utils.config_utils import load_config
    from secops.exceptions import APIError

    return SecOpsClient, load_config, APIError
  except ImportError as e:
    raise ImportError(
        "The 'secops' package (Google SecOps SDK / secops-wrapper) is required "
        "to run the scrape command. Please install it or make sure it is "
        "available in your python environment."
    ) from e


def _get_nested_field(data: dict, path: list[str]) -> Any:
  """Safely retrieve nested dictionary fields supporting camel/snake case."""
  current = data
  for part in path:
    if not isinstance(current, dict):
      return None
    val = current.get(part)
    if val is None:
      # Convert snake_case to camelCase
      camel_part = "".join(x.capitalize() or "_" for x in part.split("_"))
      camel_part = camel_part[0].lower() + camel_part[1:]
      val = current.get(camel_part)
    if val is None:
      return None
    current = val
  return current


def _unflatten_dict(flat_dict: dict) -> dict:
  """Converts a flat dictionary with dot-notation keys into a nested dictionary."""
  nested: dict[str, Any] = {}
  for key, value in flat_dict.items():
    parts = key.split(".")
    current = nested
    for i, part in enumerate(parts):
      if "[" in part and part.endswith("]"):
        array_name, index_str = part.split("[", 1)
        index = int(index_str[:-1])

        if array_name not in current:
          current[array_name] = []

        while len(current[array_name]) <= index:
          current[array_name].append({})

        if i == len(parts) - 1:
          current[array_name][index] = value
        else:
          if not isinstance(current[array_name][index], dict):
            current[array_name][index] = {}
          current = current[array_name][index]
      elif i == len(parts) - 1:
        current[part] = value
      else:
        if part not in current or not isinstance(current[part], dict):
          current[part] = {}
        current = current[part]
  return nested


def _extract_raw_log(match: dict) -> str | None:
  """Extract standard raw log message string from match priority list."""
  log_text = match.get("logText")
  if log_text:
    return log_text.strip()

  raw_record = match.get("rawRecord")
  if raw_record:
    try:
      if isinstance(raw_record, str):
        decoded = base64.b64decode(raw_record.encode()).decode("utf-8", errors="ignore")
      else:
        decoded = base64.b64decode(raw_record).decode("utf-8", errors="ignore")
      return decoded.strip()
    except Exception:
      pass

  msg = _get_nested_field(match, ["event", "udm", "additional", "Message"])
  if msg:
    return msg.strip()

  # Fallback to parsed extracted fields if available (common for structured raw logs)
  extracted = _get_nested_field(match, ["event", "udm", "extracted"])
  if extracted:
    return json.dumps(extracted)

  # Final fallback to full UDM JSON representation
  udm = _get_nested_field(match, ["event", "udm"])
  if udm:
    if any("." in k or "[" in k for k in udm.keys()):
      udm = _unflatten_dict(udm)
    return json.dumps(udm)

  return None


def _resolve_secops_config(
    customer_id: str | None,
    project_id: str | None,
    region: str | None,
    api_version: str | None,
    load_config_fn: Any,
) -> dict[str, Any]:
  """Resolve API parameters with precedence: CLI flags > config > defaults."""
  config = load_config_fn()
  resolved = {
      "customer_id": customer_id or config.get("customer_id"),
      "project_id": project_id or config.get("project_id"),
      "region": region or config.get("region", "us"),
      "default_api_version": api_version or config.get("api_version", "v1alpha"),
  }

  missing = [
      k for k, v in resolved.items() if not v and k in ["customer_id", "project_id"]
  ]
  if missing:
    raise ValueError(
        f"Missing required configurations: {', '.join(missing)}. "
        "Run 'secops config set' or pass them as parameters."
    )
  return resolved


def _resolve_time_range(
    time_window: int,
    start_time_str: str | None,
    end_time_str: str | None,
) -> tuple[datetime, datetime]:
  """Resolve start and end time parameters."""
  end_time = datetime.now(UTC)
  if end_time_str:
    end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))

  if start_time_str:
    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
  else:
    start_time = end_time - timedelta(hours=time_window)

  return start_time, end_time


def _generate_time_slices(
    start_time: datetime, end_time: datetime, chunk_size_minutes: int
) -> list[tuple[datetime, datetime]]:
  """Generate consecutive time slices of the target chunk size."""
  slices = []
  chunk_delta = timedelta(minutes=chunk_size_minutes)

  current_start = start_time
  while current_start < end_time:
    current_end = min(current_start + chunk_delta, end_time)
    slices.append((current_start, current_end))
    current_start = current_end

  return slices


def _resolve_ingestion_scope(
    chronicle: Any,
    label: str,
    start_time: datetime,
    end_time: datetime,
) -> tuple[datetime, datetime, list[str]]:
  """Resolves the time range boundaries and log types for an ingestion label."""
  query = f'metadata.ingestion_labels.value = "{label}"'
  print(f"Resolving ingestion scope for label '{label}'...")
  print(f"UDM Search query: {query}")
  print(f"UDM Search window: {start_time.isoformat()} to {end_time.isoformat()}")

  try:
    events = chronicle.search_udm(
        query=query,
        start_time=start_time,
        end_time=end_time,
        max_events=10000,
        as_list=True,
    )
  except Exception as e:
    raise RuntimeError(f"Failed to query UDM Search for ingestion label: {e}")

  if not events:
    raise ValueError(
        f"No UDM events found matching ingestion label '{label}' "
        "within the search window."
    )

  timestamps = []
  log_types = set()

  for ev in events:
    udm_data = ev.get("udm", ev)
    if not isinstance(udm_data, dict):
      continue
    metadata = udm_data.get("metadata", {})

    ts_val = metadata.get("eventTimestamp") or metadata.get("event_timestamp")
    lt_val = metadata.get("logType") or metadata.get("log_type")

    if ts_val:
      try:
        clean_ts = ts_val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        timestamps.append(dt)
      except ValueError:
        pass

    if lt_val:
      log_types.add(lt_val.strip())

  if not timestamps:
    raise ValueError(
        "UDM Search returned events, but none had parsable eventTimestamp values."
    )

  min_ts = min(timestamps)
  max_ts = max(timestamps)
  unique_log_types = sorted(list(log_types))

  # Add 1-minute safety buffers
  buffered_start = min_ts - timedelta(minutes=1)
  buffered_end = max_ts + timedelta(minutes=1)

  print("=== Resolved Ingestion Scope ===")
  print(f"Total events found: {len(events)}")
  print(f"Earliest event:     {min_ts.isoformat()}")
  print(f"Latest event:       {max_ts.isoformat()}")
  print(f"Buffered start:     {buffered_start.isoformat()}")
  print(f"Buffered end:       {buffered_end.isoformat()}")
  print(f"Log types:          {', '.join(unique_log_types)}")
  print("================================")

  return buffered_start, buffered_end, unique_log_types


def scrape_to_usecase_logic(
    query: str | None = None,
    name: str | None = None,
    time_window: int = 24,
    start_time: str | None = None,
    end_time: str | None = None,
    page_size: int = 100,
    log_types: str | None = None,
    max_events: int = 10000,
    chunk_size: int = 2,
    dry_run: bool = False,
    customer_id: str | None = None,
    project_id: str | None = None,
    region: str | None = None,
    api_version: str | None = None,
    ingestion_label: str | None = None,
) -> None:
  """Scrapes raw logs and builds a Logstory usecase structure."""
  if not query and not ingestion_label:
    print(
        "Error: Either --query (-q) or --ingestion-label (-l) must be specified.",
        file=sys.stderr,
    )
    sys.exit(1)

  # 1. Dynamic imports of secops SDK
  SecOpsClient, load_config_fn, APIError = _import_secops()

  # 2. Determine usecase name
  if name:
    usecase_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
  else:
    usecase_name = datetime.now(UTC).strftime("%Y%m%d_%H%M")

  print(f"Target usecase name: {usecase_name}")

  # 3. Resolve target directory in root usecases folder
  package_dir = Path(os.path.dirname(os.path.abspath(__file__)))
  usecase_dir = (package_dir / "../../usecases" / usecase_name).resolve()
  events_dir = usecase_dir / "EVENTS"
  entities_dir = usecase_dir / "ENTITIES"
  rules_dir = usecase_dir / "RULES"
  search_dir = usecase_dir / "SEARCH"
  extensions_dir = usecase_dir / "PARSER_EXTENSIONS"

  print(f"Target directory path: {usecase_dir}")

  try:
    config_kwargs = _resolve_secops_config(
        customer_id, project_id, region, api_version, load_config_fn
    )
  except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

  # Initialize SecOps client
  client = SecOpsClient()
  chronicle = client.chronicle(**config_kwargs)

  if ingestion_label:
    search_start, search_end = _resolve_time_range(time_window, start_time, end_time)
    try:
      resolved_start, resolved_end, resolved_log_types = _resolve_ingestion_scope(
          chronicle, ingestion_label, search_start, search_end
      )
    except Exception as e:
      print(f"Error: {e}", file=sys.stderr)
      sys.exit(1)

    active_log_types = (
        log_types if log_types is not None else ",".join(resolved_log_types)
    )
    active_query = query if query is not None else "raw = /.*/"
  else:
    active_log_types = log_types
    active_query = query
    resolved_start, resolved_end = _resolve_time_range(
        time_window, start_time, end_time
    )

  if dry_run:
    print("\n--- Dry Run Information ---")
    print(f"Would create directory structure under: {usecase_dir}")
    print(f"Query parameters: {active_query}")
    print(f"Resolved start time: {resolved_start.isoformat()}")
    print(f"Resolved end time:   {resolved_end.isoformat()}")
    print(f"Resolved log types:  {active_log_types}")
    print("Dry run complete. No API calls or files created.")
    return

  print(
      f"Searching raw logs from {resolved_start.isoformat()} to"
      f" {resolved_end.isoformat()}..."
  )

  matches = []
  time_slices = _generate_time_slices(resolved_start, resolved_end, chunk_size)
  print(
      f"Dividing target range into {len(time_slices)} stateful time-chunk "
      f"slices (each {chunk_size} minutes)."
  )
  print(f"Safety ceiling limit: {max_events} events.")

  for idx, (slice_start, slice_end) in enumerate(time_slices):
    print(
        f"\n[Slice {idx + 1}/{len(time_slices)}] Querying "
        f"{slice_start.isoformat()} to {slice_end.isoformat()}..."
    )

    search_kwargs = {
        "query": active_query,
        "start_time": slice_start,
        "end_time": slice_end,
        "page_size": page_size,
    }

    if active_log_types:
      search_kwargs["log_types"] = [lt.strip() for lt in active_log_types.split(",")]

    try:
      response = chronicle.search_raw_logs(**search_kwargs)
    except APIError as e:
      print(
          f"API Error during scraping slice {idx + 1}: {e}",
          file=sys.stderr,
      )
      continue
    except Exception as e:
      print(f"Unexpected error: {e}", file=sys.stderr)
      continue

    # Extract matches
    slice_matches = []
    if isinstance(response, list):
      for block in response:
        if isinstance(block, dict) and "matches" in block:
          slice_matches.extend(block["matches"])
    elif isinstance(response, dict):
      slice_matches = response.get("matches", [])

    matches.extend(slice_matches)
    total_scraped = len(matches)
    print(
        f"  Retrieved {len(slice_matches)} events. "
        f"Total accumulated overall: {total_scraped}"
    )

    if total_scraped >= max_events:
      print(
          f"  Safety ceiling limit of {max_events} events reached. Stopping loop early."
      )
      matches = matches[:max_events]
      break

  print(f"Found {len(matches)} raw log entries in total.")

  if not matches:
    print("No raw logs found for target parameters. Exiting.")
    return

  # Create directories
  events_dir.mkdir(parents=True, exist_ok=True)
  entities_dir.mkdir(parents=True, exist_ok=True)
  rules_dir.mkdir(parents=True, exist_ok=True)
  search_dir.mkdir(parents=True, exist_ok=True)
  extensions_dir.mkdir(parents=True, exist_ok=True)

  # Create a symbolic link inside the package so that Logstory CLI detects it as installed
  package_usecase_link = package_dir / "usecases" / usecase_name
  if not package_usecase_link.exists():
    try:
      os.symlink(f"../../../usecases/{usecase_name}", package_usecase_link)
      print(
          f"Created package symlink: {package_usecase_link} ->"
          f" ../../../usecases/{usecase_name}"
      )
    except Exception as e:
      print(f"Warning: Failed to create package symlink: {e}")

  # Group and extract logs
  grouped_logs: dict[str, list[str]] = {}
  log_types_metadata: dict[str, dict[str, str]] = {}

  for match in matches:
    udm = _get_nested_field(match, ["event", "udm"]) or {}
    meta = udm.get("metadata") or {}

    log_type = meta.get("logType")
    if not log_type:
      log_type = _get_nested_field(match, ["logType", "displayName"])
    if not log_type:
      log_type = meta.get("productName")
    if not log_type:
      log_type = "UNKNOWN"

    # Sanitize uppercase filename
    log_file = f"{re.sub(r'[^a-zA-Z0-9]', '_', log_type).upper()}.log"

    # Safe extract content string
    content = _extract_raw_log(match)
    if not content:
      continue

    if log_file not in grouped_logs:
      grouped_logs[log_file] = []
      log_types_metadata[log_file] = {
          "vendor": meta.get("vendorName") or "Unknown",
          "product": meta.get("productName") or log_type,
      }

    grouped_logs[log_file].append(content)

  # Write log files
  for filename, lines in grouped_logs.items():
    file_path = events_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
      f.write("\n".join(lines) + "\n")
    print(f"Saved {len(lines)} log lines to: {file_path}")

  # Generate metadata frontmatter template
  escaped_query = active_query.replace('"', '\\"')
  yaml_lines = [
      "---",
      f"title: {usecase_name}",
      f'description: "Usecase for raw logs scraped using query: {escaped_query}"',
      "tags:",
      "  - scraped-logs",
      "  - secops-scraper",
      f"created: {datetime.now(UTC).strftime('%Y-%m-%d')}",
      f"updated: {datetime.now(UTC).strftime('%Y-%m-%d')}",
      "run_frequency:",
      '  events: "Manual Scrape"',
      "events:",
  ]

  for filename, info in log_types_metadata.items():
    count = len(grouped_logs[filename])
    yaml_lines.extend([
        f"  - log_type: {filename}",
        f"    product_name: {info['product']}",
        f"    vendor_name: {info['vendor']}",
        (
            "    notes: "
            f'"Auto-scraped from SecOps query: {escaped_query} '
            f'(Contains {count} events)"'
        ),
    ])
  yaml_lines.append("---")

  body_lines = [
      "",
      f"# {usecase_name}",
      "",
      "## Introduction",
      "This usecase was automatically generated by the SecOps Log Scraper utility.",
      f"Query: `{active_query}`",
      f"Time window: {time_window} hours",
      "",
      "## Events",
      "| Log Type | Product Name | Vendor Name | Notes |",
      "|---|---|---|---|",
  ]

  for filename, info in log_types_metadata.items():
    count = len(grouped_logs[filename])
    body_lines.append(
        f"| {filename} | {info['product']} | {info['vendor']} | "
        f"Auto-scraped ({count} events) |"
    )

  metadata_content = "\n".join(yaml_lines) + "\n" + "\n".join(body_lines) + "\n"
  metadata_file_path = usecase_dir / f"{usecase_name}.md"

  with open(metadata_file_path, "w", encoding="utf-8") as f:
    f.write(metadata_content)
  print(f"Saved usecase metadata to: {metadata_file_path}")

  # Run the documentation compiler tool
  compiler_script = (package_dir / "../../usecases/generate_usecase_docs.py").resolve()
  if not compiler_script.exists():
    # Fallback to check in current directory
    compiler_script = Path("usecases/generate_usecase_docs.py").resolve()

  if compiler_script.exists():
    print("Compiling usecase documentation with Logstory generator...")
    try:
      subprocess.run(
          [sys.executable, str(compiler_script), str(usecase_dir)],
          check=True,
      )
      print("Usecase documentation successfully compiled!")
    except subprocess.CalledProcessError as e:
      print(f"Warning: generate_usecase_docs.py failed: {e}")
  else:
    print(
        "Warning: generate_usecase_docs.py utility not found. "
        "Skipping compilation step."
    )

  print("\nLogstory Usecase setup complete!")
