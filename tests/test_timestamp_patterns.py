#!/usr/bin/env python3
"""
Test module to analyze timestamp patterns from YAML files against log lines.

This module reads timestamp patterns from YAML configuration files and tests them
against individual log lines to determine which patterns match, their column positions,
and match counts.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def load_timestamp_patterns(yaml_file: Path) -> Dict[str, List[Dict]]:
  """Load timestamp patterns from a YAML file.
  
  Args:
    yaml_file: Path to the YAML file containing timestamp patterns
    
  Returns:
    Dictionary mapping log types to their timestamp patterns
  """
  with open(yaml_file, 'r') as f:
    data = yaml.safe_load(f)
  
  return data


def analyze_pattern_matches(
    log_line: str, 
    patterns: List[Dict]
) -> List[Dict[str, any]]:
  """Analyze which patterns match a log line and where.
  
  Args:
    log_line: Single line from a log file
    patterns: List of pattern dictionaries from YAML
    
  Returns:
    List of match results with pattern info and positions
  """
  results = []
  
  for pattern_def in patterns:
    pattern_name = pattern_def.get('name', 'unnamed')
    pattern_str = pattern_def.get('pattern', '')
    
    if not pattern_str:
      continue
    
    try:
      # Compile the regex pattern
      regex = re.compile(pattern_str)
      
      # Find all matches
      matches = list(regex.finditer(log_line))
      
      match_info = {
        'name': pattern_name,
        'pattern': pattern_str,
        'match_count': len(matches),
        'matches': []
      }
      
      # Record position info for each match
      for match in matches:
        match_detail = {
          'start': match.start(),
          'end': match.end(),
          'matched_text': match.group(0),
          'groups': match.groups()
        }
        
        # If there's a specific group specified, extract it
        if 'group' in pattern_def:
          group_num = pattern_def['group']
          if group_num <= len(match.groups()):
            match_detail['extracted_group'] = match.group(group_num)
        
        match_info['matches'].append(match_detail)
      
      results.append(match_info)
      
    except re.error as e:
      # Record regex compilation errors
      results.append({
        'name': pattern_name,
        'pattern': pattern_str,
        'error': f'Regex compilation error: {str(e)}',
        'match_count': 0,
        'matches': []
      })
  
  return results


def format_report(
    log_line: str,
    log_type: str,
    results: List[Dict[str, any]]
) -> str:
  """Format the analysis results into a readable report.
  
  Args:
    log_line: The analyzed log line
    log_type: The log type being analyzed
    results: List of match results
    
  Returns:
    Formatted report string
  """
  report = []
  report.append("=" * 80)
  report.append(f"TIMESTAMP PATTERN ANALYSIS REPORT")
  report.append("=" * 80)
  report.append(f"\nLog Type: {log_type}")
  report.append(f"\nLog Line (first 200 chars):")
  report.append(f"{log_line[:200]}{'...' if len(log_line) > 200 else ''}")
  report.append(f"\nLog Line Length: {len(log_line)} characters")
  report.append("\n" + "-" * 80)
  report.append("PATTERN MATCHES:")
  report.append("-" * 80)
  
  # Sort results by pattern name
  sorted_results = sorted(results, key=lambda x: x['name'])
  
  for result in sorted_results:
    report.append(f"\nPattern Name: {result['name']}")
    report.append(f"Pattern: {result['pattern'][:100]}{'...' if len(result['pattern']) > 100 else ''}")
    
    if 'error' in result:
      report.append(f"Status: ERROR - {result['error']}")
      report.append(f"Match Count: 0")
    else:
      report.append(f"Match Count: {result['match_count']}")
      
      if result['match_count'] > 0:
        report.append("Matches:")
        for i, match in enumerate(result['matches'], 1):
          report.append(f"  Match {i}:")
          report.append(f"    Position: {match['start']}:{match['end']}")
          report.append(f"    Matched Text: {match['matched_text'][:50]}{'...' if len(match['matched_text']) > 50 else ''}")
          if 'extracted_group' in match:
            report.append(f"    Extracted Group: {match['extracted_group']}")
    
    report.append("-" * 40)
  
  # Add overlap analysis
  report.append("\n" + "=" * 80)
  report.append("OVERLAP ANALYSIS:")
  report.append("=" * 80)
  
  # Find overlapping matches
  all_matches = []
  for result in results:
    if result['match_count'] > 0:
      for match in result['matches']:
        all_matches.append({
          'pattern_name': result['name'],
          'start': match['start'],
          'end': match['end'],
          'text': match['matched_text']
        })
  
  # Sort by start position
  all_matches.sort(key=lambda x: x['start'])
  
  # Check for overlaps
  overlaps = []
  for i in range(len(all_matches)):
    for j in range(i + 1, len(all_matches)):
      if all_matches[i]['end'] > all_matches[j]['start']:
        overlaps.append((all_matches[i], all_matches[j]))
  
  if overlaps:
    report.append(f"\nFound {len(overlaps)} overlapping matches:")
    for match1, match2 in overlaps:
      report.append(f"\n  {match1['pattern_name']} [{match1['start']}:{match1['end']}]")
      report.append(f"  overlaps with")
      report.append(f"  {match2['pattern_name']} [{match2['start']}:{match2['end']}]")
  else:
    report.append("\nNo overlapping matches found.")
  
  return "\n".join(report)


def main():
  """Main entry point for the timestamp pattern analyzer."""
  parser = argparse.ArgumentParser(
    description='Analyze timestamp patterns against log lines'
  )
  parser.add_argument(
    'yaml_file',
    type=Path,
    help='Path to YAML file containing timestamp patterns'
  )
  parser.add_argument(
    'log_file',
    type=Path,
    help='Path to log file to analyze'
  )
  parser.add_argument(
    '--log-type',
    help='Specific log type to analyze (default: analyze all types in YAML)'
  )
  parser.add_argument(
    '--output',
    type=Path,
    help='Output file for report (default: stdout)'
  )
  
  args = parser.parse_args()
  
  # Validate input files
  if not args.yaml_file.exists():
    print(f"Error: YAML file not found: {args.yaml_file}", file=sys.stderr)
    sys.exit(1)
  
  if not args.log_file.exists():
    print(f"Error: Log file not found: {args.log_file}", file=sys.stderr)
    sys.exit(1)
  
  # Load patterns
  try:
    patterns_data = load_timestamp_patterns(args.yaml_file)
  except Exception as e:
    print(f"Error loading YAML file: {e}", file=sys.stderr)
    sys.exit(1)
  
  # Read first line of log file
  with open(args.log_file, 'r') as f:
    log_line = f.readline().strip()
  
  if not log_line:
    print("Error: Log file is empty", file=sys.stderr)
    sys.exit(1)
  
  # Determine which log types to analyze
  if args.log_type:
    if args.log_type not in patterns_data:
      print(f"Error: Log type '{args.log_type}' not found in YAML", file=sys.stderr)
      print(f"Available types: {', '.join(patterns_data.keys())}", file=sys.stderr)
      sys.exit(1)
    log_types = [args.log_type]
  else:
    log_types = list(patterns_data.keys())
  
  # Analyze each log type
  all_reports = []
  for log_type in log_types:
    type_data = patterns_data[log_type]
    
    # Extract timestamp patterns
    timestamps = type_data.get('timestamps', [])
    
    if not timestamps:
      continue
    
    # Analyze patterns
    results = analyze_pattern_matches(log_line, timestamps)
    
    # Generate report
    report = format_report(log_line, log_type, results)
    all_reports.append(report)
  
  # Output results
  final_report = "\n\n".join(all_reports)
  
  if args.output:
    with open(args.output, 'w') as f:
      f.write(final_report)
    print(f"Report written to: {args.output}")
  else:
    print(final_report)


if __name__ == '__main__':
  main()