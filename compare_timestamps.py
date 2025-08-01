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

from datetime import datetime, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def read_timestamps_from_file(file_path, target_year):
  """Read epoch timestamps from a file and convert to datetime objects, filtering for target year."""
  try:
    with open(file_path) as f:
      timestamps = []
      for line in f:
        if line.strip():
          epoch = int(line.strip())
          # Handle both seconds and milliseconds timestamps
          if epoch > 1e12:  # Milliseconds
            dt = datetime.fromtimestamp(epoch / 1000)
          else:  # Seconds
            dt = datetime.fromtimestamp(epoch)
          # Only include timestamps from the target year
          if dt.year == target_year:
            timestamps.append(dt)
      return timestamps
  except FileNotFoundError:
    print(f"File not found: {file_path}")
    return []
  except ValueError as e:
    print(f"Error parsing timestamps from {file_path}: {e}")
    return []


def plot_timelines():
  """Create timeline plots comparing before.txt (2024) and after.txt (2025) datetime values."""
  # Read data from both files with different year filters
  before_data = read_timestamps_from_file("before.txt", 2024)
  after_data = read_timestamps_from_file("after.txt", 2025)

  if not before_data and not after_data:
    print(
        "Error: No 2024 timestamps found in before.txt and no 2025 timestamps found in"
        " after.txt"
    )
    return
  if not before_data:
    print("Warning: No 2024 timestamps found in before.txt")
  elif not after_data:
    print("Warning: No 2025 timestamps found in after.txt")

  # Calculate separate min-max ranges for each dataset
  def get_range_with_padding(data):
    if not data:
      return None, None
    x_min = min(data)
    x_max = max(data)

    # Add padding if min and max are the same
    if x_min == x_max:
      x_min = x_min - timedelta(hours=1)
      x_max = x_max + timedelta(hours=1)
    else:
      # Add 5% padding on each side
      time_range = x_max - x_min
      padding = time_range * 0.05
      x_min = x_min - padding
      x_max = x_max + padding
    return x_min, x_max

  before_min, before_max = get_range_with_padding(before_data)
  after_min, after_max = get_range_with_padding(after_data)

  # Create figure with two subplots
  fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 8))

  # Plot timeline for before.txt (top)
  if before_data:
    y_values = [1] * len(before_data)  # All points at y=1
    ax1.scatter(before_data, y_values, alpha=0.7, color="blue", s=50, marker="|")
    ax1.set_ylim(0.5, 1.5)
  else:
    ax1.text(
        0.5,
        0.5,
        "No 2024 timestamps found",
        transform=ax1.transAxes,
        ha="center",
        va="center",
        fontsize=14,
        color="gray",
    )

  ax1.set_title("Timeline of 2024 Timestamps in before.txt")
  if before_min and before_max:
    ax1.set_xlim(before_min, before_max)
  ax1.set_ylabel("Events")
  ax1.grid(True, alpha=0.3)
  ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
  ax1.tick_params(axis="x", rotation=45)
  ax1.set_yticks([])  # Remove y-axis ticks since they're not meaningful

  # Plot timeline for after.txt (bottom)
  if after_data:
    y_values = [1] * len(after_data)  # All points at y=1
    ax2.scatter(after_data, y_values, alpha=0.7, color="red", s=50, marker="|")
    ax2.set_ylim(0.5, 1.5)
  else:
    ax2.text(
        0.5,
        0.5,
        "No 2025 timestamps found",
        transform=ax2.transAxes,
        ha="center",
        va="center",
        fontsize=14,
        color="gray",
    )

  ax2.set_title("Timeline of 2025 Timestamps in after.txt")
  if after_min and after_max:
    ax2.set_xlim(after_min, after_max)
  ax2.set_xlabel("Date/Time")
  ax2.set_ylabel("Events")
  ax2.grid(True, alpha=0.3)
  ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
  ax2.tick_params(axis="x", rotation=45)
  ax2.set_yticks([])  # Remove y-axis ticks since they're not meaningful

  # Adjust layout and display
  plt.tight_layout()
  plt.show()

  # Print some statistics
  print(f"Before.txt (2024): {len(before_data)} values")
  print(f"After.txt (2025): {len(after_data)} values")
  if before_data:
    print(f"Before.txt (2024) range: {min(before_data)} - {max(before_data)}")
  if after_data:
    print(f"After.txt (2025) range: {min(after_data)} - {max(after_data)}")


if __name__ == "__main__":
  plot_timelines()
