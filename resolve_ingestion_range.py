#!/usr/bin/env python3
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
"""Standalone utility to resolve time range and log types for an Ingestion Label.

Queries Google SecOps UDM Search for events matching a specific ingestion label,
parses the JSON response, and calculates the earliest/latest event timestamps and
unique log types.
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Tuple

from secops import SecOpsClient
from secops.cli.utils.config_utils import load_config
from secops.exceptions import APIError


def _resolve_secops_config(args: argparse.Namespace) -> Dict[str, Any]:
  """Resolve API parameters with precedence: CLI flags > config > defaults."""
  config = load_config()
  resolved = {
      "customer_id": args.customer_id or config.get("customer_id"),
      "project_id": args.project_id or config.get("project_id"),
      "region": args.region or config.get("region", "us"),
      "default_api_version": args.api_version or config.get(
          "api_version", "v1alpha"
      ),
  }

  missing = [
      k
      for k, v in resolved.items()
      if not v and k in ["customer_id", "project_id"]
  ]
  if missing:
    raise ValueError(
        f"Missing required configurations: {', '.join(missing)}. "
        "Run 'secops config set' or pass them as parameters."
    )
  return resolved


def main() -> None:
  """Run the main resolution logic."""
  parser = argparse.ArgumentParser(
      description="Resolve time range and log types for an Ingestion Label."
  )
  parser.add_argument(
      "--label",
      "-l",
      required=True,
      help="The ingestion label value to search for (e.g. TI_ISAC_4)",
  )
  parser.add_argument(
      "--window-days",
      "-w",
      type=int,
      default=7,
      help="Number of days in the past to search UDM (default: 7)",
  )
  parser.add_argument(
      "--start-time",
      help="Explicit search start time in YYYY-MM-DDTHH:MM:SS format",
  )
  parser.add_argument(
      "--end-time",
      help="Explicit search end time in YYYY-MM-DDTHH:MM:SS format",
  )

  # Tenant overrides
  parser.add_argument("--customer-id", help="Chronicle customer instance ID")
  parser.add_argument("--project-id", help="GCP project ID")
  parser.add_argument("--region", help="Chronicle region")
  parser.add_argument(
      "--api-version", choices=["v1", "v1beta", "v1alpha"], help="API version"
  )

  args = parser.parse_args()

  try:
    config_kwargs = _resolve_secops_config(args)
  except ValueError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

  # Initialize SecOps client
  client = SecOpsClient()
  chronicle = client.chronicle(**config_kwargs)

  # Set up UDM Search time range
  if args.start_time:
    try:
      start_time = datetime.fromisoformat(args.start_time)
      if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    except ValueError:
      print(
          f"Error: Invalid start-time format '{args.start_time}'. "
          "Use YYYY-MM-DDTHH:MM:SS",
          file=sys.stderr,
      )
      sys.exit(1)

    if args.end_time:
      try:
        end_time = datetime.fromisoformat(args.end_time)
        if end_time.tzinfo is None:
          end_time = end_time.replace(tzinfo=timezone.utc)
      except ValueError:
        print(
            f"Error: Invalid end-time format '{args.end_time}'. "
            "Use YYYY-MM-DDTHH:MM:SS",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
      end_time = datetime.now(timezone.utc)
  else:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=args.window_days)

  query = f'metadata.ingestion_labels.value = "{args.label}"'

  print(f"Searching UDM events matching query: {query}")
  print(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}")

  try:
    events = chronicle.search_udm(
        query=query,
        start_time=start_time,
        end_time=end_time,
        max_events=10000,
        as_list=True,
    )
  except APIError as e:
    print(f"API Error: {e}", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print(f"Unexpected error calling UDM Search: {e}", file=sys.stderr)
    sys.exit(1)

  if not events:
    print(
        f"\nNo events found with ingestion label '{args.label}' "
        f"in the last {args.window_days} days."
    )
    sys.exit(0)

  timestamps: List[datetime] = []
  log_types: set[str] = set()

  for ev in events:
    # Standard UDM Search API wraps UDM fields inside "udm" key
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
    print("\nCould not parse any event timestamps from the UDM Search results.")
    sys.exit(0)

  # Resolve bounding box
  min_ts = min(timestamps)
  max_ts = max(timestamps)
  unique_log_types = sorted(list(log_types))

  # Format output
  print("\n=== Ingestion Scope Resolved ===")
  print(f"Total events found: {len(events)}")
  print(f"Earliest event (min_ts): {min_ts.isoformat()}")
  print(f"Latest event (max_ts):   {max_ts.isoformat()}")
  print(f"Unique log types:        {', '.join(unique_log_types)}")
  print("================================\n")

  # Print suggested command for Stage 2
  log_types_param = ",".join(unique_log_types)
  # Apply 1-minute safety buffers
  buffered_start = (min_ts - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")
  buffered_end = (max_ts + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")

  print("Suggested command for Stage 2 (scraped usecase validation):")
  print("-----------------------------------------------------------")
  print(
      f"uv run logstory usecases scrape \\\n"
      f"  -q \"*\" \\\n"
      f"  --start-time \"{buffered_start}\" \\\n"
      f"  --end-time \"{buffered_end}\" \\\n"
      f"  --log-types \"{log_types_param}\" \\\n"
      f"  -n ingestion_{args.label.lower()} \\\n"
      f"  --dry-run"
  )
  print("-----------------------------------------------------------")


if __name__ == "__main__":
  main()
