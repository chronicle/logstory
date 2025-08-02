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
Analyze all timestamp patterns across multiple log files.

This script provides a comprehensive analysis of timestamp patterns,
including overlap detection and selectivity recommendations.
"""

import argparse
import json
from pathlib import Path

from test_timestamp_patterns import analyze_pattern_matches, load_timestamp_patterns


def analyze_log_directory(
    yaml_file: Path, log_dir: Path, file_pattern: str = "*.log"
) -> dict[str, dict]:
  """Analyze all log files in a directory against timestamp patterns.

  Args:
    yaml_file: Path to YAML file with timestamp patterns
    log_dir: Directory containing log files
    file_pattern: Glob pattern for log files

  Returns:
    Dictionary mapping log files to their analysis results
  """
  patterns_data = load_timestamp_patterns(yaml_file)
  results = {}

  # Find all log files
  log_files = list(log_dir.glob(file_pattern))

  for log_file in log_files:
    print(f"Analyzing: {log_file.name}")

    # Read first line
    try:
      with open(log_file) as f:
        first_line = f.readline().strip()

      if not first_line:
        continue

      # Analyze against all log types
      file_results = {}
      for log_type, type_data in patterns_data.items():
        timestamps = type_data.get("timestamps", [])
        if timestamps:
          matches = analyze_pattern_matches(first_line, timestamps)
          file_results[log_type] = {"matches": matches, "line_length": len(first_line)}

      results[str(log_file)] = file_results

    except Exception as e:
      print(f"  Error reading {log_file}: {e}")

  return results


def find_best_patterns(results: dict[str, dict]) -> dict[str, list[dict]]:
  """Identify the best matching patterns for each log file.

  Args:
    results: Analysis results from analyze_log_directory

  Returns:
    Dictionary mapping log files to recommended patterns
  """
  recommendations = {}

  for log_file, file_results in results.items():
    best_matches = []
    max_matches = 0
    best_log_type = None

    # Find log type with most matches
    for log_type, type_results in file_results.items():
      total_matches = sum(m["match_count"] for m in type_results["matches"])

      if total_matches > max_matches:
        max_matches = total_matches
        best_log_type = log_type

    if best_log_type and max_matches > 0:
      # Get patterns that matched
      matching_patterns = [
          m for m in file_results[best_log_type]["matches"] if m["match_count"] > 0
      ]

      # Sort by selectivity (fewer matches = more selective)
      matching_patterns.sort(key=lambda x: x["match_count"])

      recommendations[log_file] = {
          "log_type": best_log_type,
          "total_matches": max_matches,
          "patterns": matching_patterns,
      }

  return recommendations


def generate_summary_report(
    results: dict[str, dict], recommendations: dict[str, list[dict]]
) -> str:
  """Generate a comprehensive summary report.

  Args:
    results: Raw analysis results
    recommendations: Pattern recommendations

  Returns:
    Formatted report string
  """
  report = []
  report.append("=" * 80)
  report.append("TIMESTAMP PATTERN ANALYSIS SUMMARY")
  report.append("=" * 80)
  report.append("")

  # Summary statistics
  total_files = len(results)
  files_with_matches = len(recommendations)

  report.append(f"Total log files analyzed: {total_files}")
  report.append(f"Files with timestamp matches: {files_with_matches}")
  report.append("")

  # Detailed recommendations
  report.append("-" * 80)
  report.append("PATTERN RECOMMENDATIONS BY FILE:")
  report.append("-" * 80)

  for log_file, rec in recommendations.items():
    file_name = Path(log_file).name
    report.append(f"\n{file_name}")
    report.append(f"  Recommended log type: {rec['log_type']}")
    report.append(f"  Total timestamp matches: {rec['total_matches']}")
    report.append("  Most selective patterns:")

    # Show top 3 most selective patterns
    for i, pattern in enumerate(rec["patterns"][:3], 1):
      report.append(f"    {i}. {pattern['name']} (matches: {pattern['match_count']})")

  # Pattern overlap analysis
  report.append("\n" + "=" * 80)
  report.append("PATTERN OVERLAP ANALYSIS:")
  report.append("=" * 80)

  for log_file, file_results in results.items():
    file_name = Path(log_file).name
    has_overlaps = False

    for log_type, type_results in file_results.items():
      # Check for overlaps within this log type
      all_matches = []
      for pattern_result in type_results["matches"]:
        if pattern_result["match_count"] > 0:
          for match in pattern_result["matches"]:
            all_matches.append({
                "pattern": pattern_result["name"],
                "start": match["start"],
                "end": match["end"],
            })

      # Sort by start position
      all_matches.sort(key=lambda x: x["start"])

      # Find overlaps
      for i in range(len(all_matches)):
        for j in range(i + 1, len(all_matches)):
          if all_matches[i]["end"] > all_matches[j]["start"]:
            if not has_overlaps:
              report.append(f"\n{file_name} ({log_type}):")
              has_overlaps = True
            report.append(
                f"  {all_matches[i]['pattern']} [{all_matches[i]['start']}:{all_matches[i]['end']}] "
                "overlaps"
                f" {all_matches[j]['pattern']} [{all_matches[j]['start']}:{all_matches[j]['end']}]"
            )

  return "\n".join(report)


def main():
  """Main entry point."""
  parser = argparse.ArgumentParser(
      description="Analyze timestamp patterns across multiple log files"
  )
  parser.add_argument(
      "yaml_file", type=Path, help="Path to YAML file containing timestamp patterns"
  )
  parser.add_argument(
      "log_dir", type=Path, help="Directory containing log files to analyze"
  )
  parser.add_argument(
      "--pattern", default="*.log", help="File pattern for log files (default: *.log)"
  )
  parser.add_argument(
      "--output", type=Path, help="Output file for report (default: stdout)"
  )
  parser.add_argument(
      "--json", action="store_true", help="Also output raw results as JSON"
  )

  args = parser.parse_args()

  # Validate inputs
  if not args.yaml_file.exists():
    print(f"Error: YAML file not found: {args.yaml_file}")
    return 1

  if not args.log_dir.exists() or not args.log_dir.is_dir():
    print(f"Error: Log directory not found: {args.log_dir}")
    return 1

  # Analyze all log files
  print(f"Analyzing log files in: {args.log_dir}")
  results = analyze_log_directory(args.yaml_file, args.log_dir, args.pattern)

  # Generate recommendations
  recommendations = find_best_patterns(results)

  # Generate report
  report = generate_summary_report(results, recommendations)

  # Output results
  if args.output:
    with open(args.output, "w") as f:
      f.write(report)
    print(f"\nReport written to: {args.output}")

    if args.json:
      json_file = args.output.with_suffix(".json")
      with open(json_file, "w") as f:
        json.dump({"results": results, "recommendations": recommendations}, f, indent=2)
      print(f"JSON results written to: {json_file}")
  else:
    print(report)

    if args.json:
      print("\n\nJSON OUTPUT:")
      print(
          json.dumps({"results": results, "recommendations": recommendations}, indent=2)
      )

  return 0


if __name__ == "__main__":
  exit(main())
