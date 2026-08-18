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

"""Property-based tests using Hypothesis for core logstory calculations."""

import datetime
import uuid
from datetime import UTC

from hypothesis import given
from hypothesis import strategies as st

from logstory.ingestion import sanitize_log_text
from logstory.logstory import validate_uuid4
from logstory.main import (
    _get_timestamp_delta_dict,
    datetime_to_filetime,
    filetime_to_datetime,
)


@given(
    days=st.integers(min_value=0, max_value=365),
    hours=st.integers(min_value=0, max_value=23),
    minutes=st.integers(min_value=0, max_value=59),
)
def test_hypothesis_timestamp_delta_roundtrip(days: int, hours: int, minutes: int):
  """Property: Valid delta strings format and parse back to identical component values."""
  parts = []
  expected = {}
  if days > 0:
    parts.append(f"{days}d")
    expected["d"] = days
  if hours > 0:
    parts.append(f"{hours}h")
    expected["h"] = hours
  if minutes > 0:
    parts.append(f"{minutes}m")
    expected["m"] = minutes

  delta_str = "".join(parts)
  if not delta_str:
    delta_str = "0d"
    expected["d"] = 0

  result = _get_timestamp_delta_dict(delta_str)
  assert result == expected


@given(
    dt=st.datetimes(
        min_value=datetime.datetime(1970, 1, 1, tzinfo=UTC),
        max_value=datetime.datetime(2999, 12, 31, tzinfo=UTC),
        timezones=st.just(UTC),
    )
)
def test_hypothesis_filetime_datetime_roundtrip(dt: datetime.datetime):
  """Property: datetime -> filetime -> datetime roundtrip preserves timestamp within microsecond precision."""
  ft = datetime_to_filetime(dt)
  reconstructed = filetime_to_datetime(ft)
  assert abs((dt - reconstructed).total_seconds()) < 1e-4


@given(text=st.text())
def test_hypothesis_sanitize_log_text_invariants(text: str):
  """Property: sanitize_log_text removes all registered problematic symbols for any input text."""
  sanitized = sanitize_log_text(text)
  assert "®" not in sanitized
  assert "©" not in sanitized
  assert "™" not in sanitized


@given(u=st.uuids(version=4))
def test_hypothesis_validate_uuid4_always_valid(u: uuid.UUID):
  """Property: Any UUID4 object string representation passes validate_uuid4."""
  u_str = str(u)
  assert validate_uuid4(u_str) == u_str
