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
"""Tests for UDM search integration."""

import json
from unittest import mock

import pytest

# Import the main module functions
import sys
sys.path.insert(0, '../src')
from logstory import main


def test_search_udm_formats_results_as_jsonl():
  """Test that _search_udm converts API results to JSON lines format."""
  mock_http_client = mock.MagicMock()

  # Mock the API response with JSON lines format (one per line)
  udm_results = [
      {"event": {"created_time": "2024-01-01T10:00:00Z"}, "metadata": {"event_id": "1"}},
      {"event": {"created_time": "2024-01-01T10:01:00Z"}, "metadata": {"event_id": "2"}},
  ]
  response_text = '\n'.join(json.dumps(r) for r in udm_results)
  mock_http_client.post.return_value.text = response_text
  mock_http_client.post.return_value.raise_for_status = mock.MagicMock()

  result = main._search_udm(
      mock_http_client,
      "test-customer-id",
      "metadata.event_type='PROCESS_EXECUTION'",
      region="US"
  )

  # Verify result is JSON lines format
  lines = result.strip().split('\n')
  assert len(lines) == 2

  # Verify each line is valid JSON
  for line in lines:
    event = json.loads(line)
    assert "event" in event
    assert "metadata" in event


def test_get_log_content_with_udm_query():
  """Test that _get_log_content works with UDM queries."""
  mock_http_client = mock.MagicMock()

  udm_result = '{"event": {"created_time": "2024-01-01T10:00:00Z"}}'
  mock_http_client.post.return_value.text = udm_result
  mock_http_client.post.return_value.raise_for_status = mock.MagicMock()

  with mock.patch.object(main, '_search_udm') as mock_search:
    mock_search.return_value = udm_result

    result = main._get_log_content(
        "UDM_SEARCH",
        "UDM_EVENTS",
        entities=False,
        udm_query="metadata.event_type='PROCESS_EXECUTION'",
        http_client=mock_http_client,
        customer_id="test-customer-id",
        region="US"
    )

    assert result == udm_result
    mock_search.assert_called_once()


def test_get_log_content_without_udm_query():
  """Test that _get_log_content still works for file-based logs."""
  # Mock the storage client to return None (local file case)
  with mock.patch.object(main, 'storage_client', None):
    with mock.patch('builtins.open', mock.mock_open(read_data='test log content')):
      result = main._get_log_content(
          "TEST_USECASE",
          "TEST_LOGTYPE",
          entities=False
      )

      assert result == 'test log content'


def test_udm_query_requires_http_client():
  """Test that UDM query without HTTP client raises error."""
  with pytest.raises(ValueError) as exc_info:
    main._get_log_content(
        "UDM_SEARCH",
        "UDM_EVENTS",
        entities=False,
        udm_query="metadata.event_type='PROCESS_EXECUTION'",
        http_client=None,
        customer_id="test-customer-id"
    )

  assert "http_client and customer_id required" in str(exc_info.value)


if __name__ == '__main__':
  pytest.main([__file__, '-v'])
