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

"""Generate usecase documentation from YAML frontmatter using Jinja2 templates.

This script processes markdown files with YAML frontmatter and generates
standardized documentation using the Jinja2 template system.
"""

import argparse
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


def parse_frontmatter(file_path: Path) -> tuple[dict, str]:
  """Parse YAML frontmatter and content from a markdown file.

  Args:
    file_path: Path to the markdown file

  Returns:
    Tuple of (frontmatter_dict, content_after_frontmatter)
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
    if len(parts) < 3:
      return {}, content

    frontmatter_yaml = parts[1]
    remaining_content = parts[2]

    # Parse YAML frontmatter
    frontmatter = yaml.safe_load(frontmatter_yaml)
    return frontmatter or {}, remaining_content

  except yaml.YAMLError as e:
    print(f"Error parsing YAML frontmatter in {file_path}: {e}")
    return {}, content


def generate_usecase_doc(
    frontmatter: dict, template_path: Path, output_path: Path = None
) -> str:
  """Generate usecase documentation from frontmatter using Jinja2 template.

  Args:
    frontmatter: Dictionary containing the YAML frontmatter data
    template_path: Path to the Jinja2 template file
    output_path: Optional path to write the generated content

  Returns:
    Generated markdown content as string
  """
  # Set up Jinja2 environment
  template_dir = template_path.parent
  template_name = template_path.name

  env = Environment(
      loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
  )

  # Load and render template
  template = env.get_template(template_name)
  rendered = template.render(**frontmatter)

  # Write to output file if specified
  if output_path:
    with open(output_path, "w", encoding="utf-8") as f:
      f.write(rendered)
    print(f"Generated documentation written to: {output_path}")

  return rendered


def process_usecase_directory(
    usecase_dir: Path, template_path: Path, output_dir: Path = None
):
  """Process a usecase directory, finding markdown files and generating docs.

  Args:
    usecase_dir: Path to usecase directory
    template_path: Path to Jinja2 template
    output_dir: Optional output directory (defaults to usecase_dir)
  """
  if output_dir is None:
    output_dir = usecase_dir

  # Find the main usecase markdown file
  usecase_name = usecase_dir.name
  markdown_file = usecase_dir / f"{usecase_name}.md"

  if not markdown_file.exists():
    print(f"Warning: No markdown file found at {markdown_file}")
    return None

  print(f"Processing usecase: {usecase_name}")

  # Parse frontmatter
  frontmatter, content = parse_frontmatter(markdown_file)

  if not frontmatter:
    print(f"Warning: No frontmatter found in {markdown_file}")
    return None

  # Generate documentation
  output_file = output_dir / f"{usecase_name}_generated.md"
  generated_content = generate_usecase_doc(frontmatter, template_path, output_file)

  return generated_content


def main():
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

  # Resolve paths
  usecase_path = Path(args.usecase_path).resolve()
  template_path = Path(args.template).resolve()

  # Handle relative template path
  if not template_path.exists():
    # Try relative to script directory
    script_dir = Path(__file__).parent
    template_path = script_dir / args.template

  if not template_path.exists():
    print(f"Error: Template file not found: {args.template}")
    sys.exit(1)

  # Process input
  if usecase_path.is_file():
    # Single markdown file
    frontmatter, content = parse_frontmatter(usecase_path)
    if not frontmatter:
      print(f"Error: No frontmatter found in {usecase_path}")
      sys.exit(1)

    if args.dry_run:
      generated = generate_usecase_doc(frontmatter, template_path)
      print(generated)
    else:
      output_path = (
          Path(args.output)
          if args.output
          else usecase_path.parent / f"{usecase_path.stem}_generated.md"
      )
      generate_usecase_doc(frontmatter, template_path, output_path)

  elif usecase_path.is_dir():
    # Usecase directory
    output_dir = Path(args.output) if args.output else usecase_path

    if args.dry_run:
      generated = process_usecase_directory(usecase_path, template_path)
      if generated:
        print(generated)
    else:
      process_usecase_directory(usecase_path, template_path, output_dir)

  else:
    print(f"Error: Path not found: {usecase_path}")
    sys.exit(1)


if __name__ == "__main__":
  main()
