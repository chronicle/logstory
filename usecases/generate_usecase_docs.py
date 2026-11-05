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

"""Generate usecase documentation from YAML frontmatter using Jinja2 or stdlib.

This script processes markdown files with v1 or v2 YAML frontmatter and
generates standardized documentation using Jinja2 when installed or a pure
Python stdlib fallback renderer.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any

import yaml

try:
  from jinja2 import Environment, FileSystemLoader
except ImportError:
  Environment = None  # type: ignore[assignment,misc]
  FileSystemLoader = None  # type: ignore[assignment,misc]

MIN_PARTS_FOR_FRONTMATTER = 3
SCHEMA_VERSION_V2 = "2.0"


def parse_frontmatter(file_path: Path) -> tuple[dict[str, Any], str]:
  """Parse YAML frontmatter and content from a markdown file.

  Args:
    file_path: Path to the markdown file.

  Returns:
    Tuple of (frontmatter_dict, content_after_frontmatter).
  """
  with open(file_path, encoding="utf-8") as f:
    content = f.read()

  # Handle optional leading newline, then check for frontmatter
  if content.startswith("\n---\n"):
    content = content[1:]  # Remove only the leading newline
  elif not content.startswith("---\n"):
    return {}, content

  # Find the end of frontmatter
  try:
    # Split on the closing ---
    parts = content.split("---\n", 2)
    if len(parts) < MIN_PARTS_FOR_FRONTMATTER:
      return {}, content

    frontmatter_yaml = parts[1]
    remaining_content = parts[2]

    # Parse YAML frontmatter
    frontmatter = yaml.safe_load(frontmatter_yaml)
    return frontmatter or {}, remaining_content

  except yaml.YAMLError as e:
    print(f"Error parsing YAML frontmatter in {file_path}: {e}")  # noqa: T201
    return {}, content


def _normalize_stream_entry(stream: dict[str, Any]) -> dict[str, Any]:
  """Normalize a v2 telemetry stream entry for template rendering."""
  entry = dict(stream)
  entry.setdefault("stream_id", "")
  entry.setdefault("log_type", "")
  entry.setdefault("product_name", "")
  entry.setdefault("vendor_name", "")
  entry.setdefault("ocsf_category_uid", None)
  entry.setdefault("ocsf_class_uid", None)
  entry.setdefault("ocsf_class_name", None)
  entry.setdefault("notes", "")
  return entry


def normalize_frontmatter_for_template(
    frontmatter: dict[str, Any],
) -> dict[str, Any]:
  """Normalize v1 or v2 frontmatter into backwards-compatible template variables.

  When `schema_version == "2.0"`, maps `telemetry.events`, `telemetry.entities`,
  and `platforms.google_secops` into legacy template keys (`events`, `entities`,
  `rules`, `saved_searches`, `reference_lists`, `run_frequency`, `data_rbac`)
  while preserving all v2 keys (`telemetry`, `platforms`, `environment`,
  `schema_version`, `version`, `author`, `license`).

  Args:
    frontmatter: Raw v1 or v2 YAML frontmatter dictionary.

  Returns:
    Normalized dictionary ready for template or fallback rendering.
  """
  normalized = copy.deepcopy(frontmatter)
  schema_version = str(normalized.get("schema_version", "1.0"))

  if schema_version != SCHEMA_VERSION_V2:
    return normalized

  telemetry = normalized.get("telemetry") or {}
  raw_events = telemetry.get("events") or []
  raw_entities = telemetry.get("entities") or []

  normalized["events"] = [
      _normalize_stream_entry(item) for item in raw_events if isinstance(item, dict)
  ]
  normalized["entities"] = [
      _normalize_stream_entry(item) for item in raw_entities if isinstance(item, dict)
  ]

  platforms = normalized.get("platforms") or {}
  secops = platforms.get("google_secops") or {}

  if "run_frequency" not in normalized and secops.get("run_frequency"):
    normalized["run_frequency"] = copy.deepcopy(secops["run_frequency"])

  if "data_rbac" not in normalized and secops.get("data_rbac"):
    normalized["data_rbac"] = secops["data_rbac"]

  raw_detections = secops.get("detections") or []
  normalized["rules"] = [
      {
          "name": det.get("name", ""),
          "path": det.get("path"),
          "live": bool(det.get("live", False)),
          "alerting": bool(det.get("alerting", False)),
          "notes": det.get("notes", "") or "",
      }
      for det in raw_detections
      if isinstance(det, dict)
  ]

  raw_searches = secops.get("saved_searches") or []
  normalized["saved_searches"] = [
      {
          "name": s.get("name", ""),
          "creator": s.get("creator", "") or "",
          "notes": s.get("notes", "") or "",
      }
      for s in raw_searches
      if isinstance(s, dict)
  ]

  raw_ref_lists = secops.get("reference_lists") or []
  normalized["reference_lists"] = [
      {
          "name": r.get("name", ""),
          "type": r.get("type", "String") or "String",
          "notes": r.get("notes", "") or "",
      }
      for r in raw_ref_lists
      if isinstance(r, dict)
  ]

  return normalized


def _format_ocsf_cell(stream: dict[str, Any]) -> str:
  """Format OCSF class name and UID for a v2 telemetry stream table cell."""
  class_name = stream.get("ocsf_class_name") or ""
  class_uid = stream.get("ocsf_class_uid")
  if class_name and class_uid is not None:
    return f"{class_name} ({class_uid})"
  if class_uid is not None:
    return f"({class_uid})"
  return str(class_name)


def _render_stream_section(
    heading: str,
    streams: list[dict[str, Any]],
    is_v2: bool,
    empty_message: str,
) -> list[str]:
  """Render Events or Entities Markdown table lines."""
  lines = [f"## {heading}", ""]
  valid_streams = [
      s for s in streams if isinstance(s, dict) and s.get("log_type", "N/A") != "N/A"
  ]
  if not valid_streams:
    lines.append(empty_message)
    lines.append("")
    return lines

  if is_v2:
    lines.append(
        "| Stream ID | Log Type | Product Name | Vendor Name | OCSF Class | Notes |"
    )
    lines.append(
        "|-----------|----------|--------------|-------------|------------|-------|"
    )
    for stream in valid_streams:
      stream_id = stream.get("stream_id", "") or ""
      log_type = stream.get("log_type", "") or ""
      product_name = stream.get("product_name", "") or ""
      vendor_name = stream.get("vendor_name", "") or ""
      ocsf_cell = _format_ocsf_cell(stream)
      notes = stream.get("notes", "") or ""
      lines.append(
          f"| {stream_id} | {log_type} | {product_name} | {vendor_name} |"
          f" {ocsf_cell} | {notes} |"
      )
  else:
    lines.append("| Log Type | Product Name | Vendor Name | Notes |")
    lines.append("|----------|--------------|-------------|-------|")
    for stream in valid_streams:
      log_type = stream.get("log_type", "") or ""
      product_name = stream.get("product_name", "") or ""
      vendor_name = stream.get("vendor_name", "") or ""
      notes = stream.get("notes", "") or ""
      lines.append(f"| {log_type} | {product_name} | {vendor_name} | {notes} |")

  lines.append("")
  return lines


def _render_without_jinja2(normalized: dict[str, Any]) -> str:
  """Render usecase documentation in pure Python when Jinja2 is not installed.

  Args:
    normalized: Frontmatter dictionary normalized via
      `normalize_frontmatter_for_template`.

  Returns:
    Generated Markdown string matching `usecase_template.j2`.
  """
  is_v2 = str(normalized.get("schema_version", "1.0")) == SCHEMA_VERSION_V2
  title = normalized.get("title", "")
  description = normalized.get("description", "")

  lines: list[str] = [
      f"# {title}",
      "",
      "## Introduction",
      "",
      f"{description}",
      "",
  ]

  for label, key in (
      ("ID", "id"),
      ("Version", "version"),
      ("Author", "author"),
      ("License", "license"),
  ):
    val = normalized.get(key)
    if val:
      lines.extend([f"**{label}**: {val}", ""])

  tags = normalized.get("tags")
  if isinstance(tags, list) and tags:
    lines.extend([f"**Tags**: {', '.join(str(t) for t in tags)}", ""])

  for label, key in (("Created", "created"), ("Updated", "updated")):
    val = normalized.get(key)
    if val:
      lines.extend([f"**{label}**: {val}", ""])

  env = normalized.get("environment")
  if isinstance(env, dict) and env:
    lines.extend(["## Environment", ""])
    org = env.get("organization") or "cymbal-investments.org"
    scenario_type = env.get("scenario_type") or "attack"
    lines.extend([
        f"**Organization**: {org}",
        "",
        f"**Scenario Type**: {scenario_type}",
        "",
    ])
    paired = env.get("paired_baselines")
    if isinstance(paired, list) and paired:
      lines.extend([
          f"**Paired Baselines**: {', '.join(str(b) for b in paired)}",
          "",
      ])

  run_freq = normalized.get("run_frequency")
  if isinstance(run_freq, dict) and run_freq:
    lines.extend(["## Run Frequency", ""])
    if run_freq.get("events"):
      lines.extend([f"**Events**: {run_freq['events']}", ""])
    if run_freq.get("entities"):
      lines.extend([f"**Entities**: {run_freq['entities']}", ""])

  data_rbac = normalized.get("data_rbac")
  if data_rbac:
    lines.extend(["## Data RBAC", "", f"**Note**: {data_rbac}", ""])

  lines.extend(
      _render_stream_section(
          "Events",
          normalized.get("events") or [],
          is_v2=is_v2,
          empty_message="No events configured for this usecase.",
      )
  )
  lines.extend(
      _render_stream_section(
          "Entities",
          normalized.get("entities") or [],
          is_v2=is_v2,
          empty_message="No entities configured for this usecase.",
      )
  )

  # Rules
  lines.extend(["## Rules", ""])
  rules = normalized.get("rules") or []
  valid_rules = [
      r for r in rules if isinstance(r, dict) and str(r.get("name", "")).strip()
  ]
  if valid_rules:
    lines.append("| Rule Name | Live | Alerting | Notes |")
    lines.append("|-----------|------|----------|-------|")
    for rule in valid_rules:
      r_name = rule.get("name", "")
      r_live = str(rule.get("live", False)).title()
      r_alerting = str(rule.get("alerting", False)).title()
      r_notes = rule.get("notes", "") or ""
      lines.append(f"| {r_name} | {r_live} | {r_alerting} | {r_notes} |")
  else:
    lines.append("No rules configured for this usecase.")
  lines.append("")

  # Saved Searches
  searches = normalized.get("saved_searches") or []
  valid_searches = [
      s for s in searches if isinstance(s, dict) and s.get("name", "N/A") != "N/A"
  ]
  if valid_searches:
    lines.extend([
        "## Saved Searches",
        "",
        "| Search Name | Creator | Notes |",
        "|-------------|---------|-------|",
    ])
    for search in valid_searches:
      s_name = search.get("name", "")
      s_creator = search.get("creator", "") or ""
      s_notes = search.get("notes", "") or ""
      lines.append(f"| {s_name} | {s_creator} | {s_notes} |")
    lines.append("")

  # Reference Lists
  ref_lists = normalized.get("reference_lists") or []
  valid_ref_lists = [
      r for r in ref_lists if isinstance(r, dict) and r.get("name", "N/A") != "N/A"
  ]
  if valid_ref_lists:
    lines.extend([
        "## Reference Lists",
        "",
        "| List Name | Type | Notes |",
        "|-----------|------|-------|",
    ])
    for ref_list in valid_ref_lists:
      l_name = ref_list.get("name", "")
      l_type = ref_list.get("type", "") or ""
      l_notes = ref_list.get("notes", "") or ""
      lines.append(f"| {l_name} | {l_type} | {l_notes} |")
    lines.append("")

  # Platform Bindings
  platforms = normalized.get("platforms")
  if isinstance(platforms, dict) and platforms:
    lines.extend(["## Platform Bindings", ""])
    secops = platforms.get("google_secops")
    if isinstance(secops, dict) and secops:
      lines.extend(["### Google SecOps", ""])
      mappings = secops.get("log_type_mappings") or {}
      for stream_id, log_type in mappings.items():
        lines.append(f"- `{stream_id}`: `{log_type}`")
      lines.append("")

    databricks = platforms.get("databricks")
    if isinstance(databricks, dict) and databricks:
      catalog = databricks.get("catalog") or "security_lakehouse"
      schema_name = databricks.get("schema_name") or "ocsf_silver"
      lines.extend([
          "### Databricks",
          "",
          f"- **Catalog**: `{catalog}`",
          f"- **Schema**: `{schema_name}`",
      ])
      for stream_id, table_name in (databricks.get("table_mappings") or {}).items():
        lines.append(f"- `{stream_id}`: `{table_name}`")
      for det in databricks.get("detections") or []:
        lines.append(f"- Detection: `{det}`")
      lines.append("")

    sigma = platforms.get("sigma")
    if isinstance(sigma, dict) and sigma.get("rules"):
      lines.extend(["### Sigma", ""])
      for sigma_rule in sigma["rules"]:
        lines.append(f"- `{sigma_rule}`")
      lines.append("")

    splunk = platforms.get("splunk")
    if isinstance(splunk, dict) and splunk.get("sourcetypes"):
      lines.extend(["### Splunk", ""])
      for stream_id, sourcetype in splunk["sourcetypes"].items():
        lines.append(f"- `{stream_id}`: `{sourcetype}`")
      lines.append("")

  lines.extend([
      "---",
      "",
      "*This document was generated from YAML frontmatter using the usecase template.*",
  ])
  return "\n".join(lines)


def generate_usecase_doc(
    frontmatter: dict[str, Any],
    template_path: Path,
    output_path: Path | None = None,
) -> str:
  """Generate usecase documentation from frontmatter using Jinja2 or stdlib.

  Args:
    frontmatter: Dictionary containing the YAML frontmatter data.
    template_path: Path to the Jinja2 template file.
    output_path: Optional path to write the generated content.

  Returns:
    Generated markdown content as string.
  """
  normalized = normalize_frontmatter_for_template(frontmatter)

  if Environment is not None and FileSystemLoader is not None:
    template_dir = template_path.parent
    template_name = template_path.name
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    rendered = template.render(**normalized)
  else:
    rendered = _render_without_jinja2(normalized)

  if output_path:
    with open(output_path, "w", encoding="utf-8") as f:
      f.write(rendered)
    print(f"Generated documentation written to: {output_path}")  # noqa: T201

  return rendered


def process_usecase_directory(
    usecase_dir: Path, template_path: Path, output_dir: Path | None = None
) -> str | None:
  """Process a usecase directory, finding markdown files and generating docs.

  Args:
    usecase_dir: Path to usecase directory.
    template_path: Path to Jinja2 template.
    output_dir: Optional output directory (defaults to usecase_dir).

  Returns:
    Generated content string or None if markdown file not found.
  """
  if output_dir is None:
    output_dir = usecase_dir

  usecase_name = usecase_dir.name
  markdown_file = usecase_dir / f"{usecase_name}.md"

  if not markdown_file.exists():
    print(f"Warning: No markdown file found at {markdown_file}")  # noqa: T201
    return None

  print(f"Processing usecase: {usecase_name}")  # noqa: T201

  frontmatter, _content = parse_frontmatter(markdown_file)

  if not frontmatter:
    print(f"Warning: No frontmatter found in {markdown_file}")  # noqa: T201
    return None

  output_file = output_dir / f"{usecase_name}_generated.md"
  return generate_usecase_doc(frontmatter, template_path, output_file)


def main() -> None:
  """Main entry point for the script."""
  parser = argparse.ArgumentParser(
      description="Generate usecase documentation from YAML frontmatter"
  )
  parser.add_argument("usecase_path", help="Path to usecase directory or markdown file")
  parser.add_argument(
      "--template",
      default="usecase_template.j2",
      help="Path to Jinja2 template file (default: usecase_template.j2)",
  )
  parser.add_argument(
      "--output", help="Output directory or file path (default: same as input)"
  )
  parser.add_argument(
      "--dry-run",
      action="store_true",
      help="Print generated content instead of writing to file",
  )

  args = parser.parse_args()

  usecase_path = Path(args.usecase_path).resolve()
  template_path = Path(args.template).resolve()

  if not template_path.exists():
    script_dir = Path(__file__).parent
    template_path = script_dir / args.template

  if not template_path.exists():
    print(f"Error: Template file not found: {args.template}")  # noqa: T201
    sys.exit(1)

  if usecase_path.is_file():
    frontmatter, _content = parse_frontmatter(usecase_path)
    if not frontmatter:
      print(f"Error: No frontmatter found in {usecase_path}")  # noqa: T201
      sys.exit(1)

    if args.dry_run:
      generated = generate_usecase_doc(frontmatter, template_path)
      print(generated)  # noqa: T201
    else:
      output_path = (
          Path(args.output)
          if args.output
          else usecase_path.parent / f"{usecase_path.stem}_generated.md"
      )
      generate_usecase_doc(frontmatter, template_path, output_path)

  elif usecase_path.is_dir():
    output_dir = Path(args.output) if args.output else usecase_path

    if args.dry_run:
      generated = process_usecase_directory(usecase_path, template_path)
      if generated:
        print(generated)  # noqa: T201
    else:
      process_usecase_directory(usecase_path, template_path, output_dir)

  else:
    print(f"Error: Path not found: {usecase_path}")  # noqa: T201
    sys.exit(1)


if __name__ == "__main__":
  main()
