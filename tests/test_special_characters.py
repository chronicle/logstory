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
"""Tests for special characters and encoding sanitization (Issue #24)."""

import base64
import json
from unittest.mock import MagicMock

from src.logstory.auth import LegacyAuthHandler, RestAuthHandler
from src.logstory.ingestion import (
    LegacyIngestionBackend,
    RestIngestionBackend,
    sanitize_log_text,
)


class TestSpecialCharactersSanitization:
  """Test suite for special character sanitization and safe API transport."""

  def test_sanitize_registered_trademark(self):
    """Test removing registered trademark symbol."""
    raw = "Product: Microsoft\u00ae Windows\u00ae Operating System"
    sanitized = sanitize_log_text(raw)
    assert sanitized == "Product: Microsoft Windows Operating System"
    assert "\u00ae" not in sanitized

  def test_sanitize_copyright_and_trademark(self):
    """Test removing copyright and trademark symbols."""
    raw = "\u00a9 2026 Google LLC\u2122 - All Rights Reserved\u00ae"
    sanitized = sanitize_log_text(raw)
    assert sanitized == " 2026 Google LLC - All Rights Reserved"
    assert "\u00a9" not in sanitized
    assert "\u2122" not in sanitized
    assert "\u00ae" not in sanitized

  def test_sanitize_empty_and_plain_strings(self):
    """Test handling of empty and standard ASCII strings."""
    assert sanitize_log_text("") == ""
    assert sanitize_log_text("Standard log message 123") == "Standard log message 123"

  def test_legacy_backend_sanitizes_unstructured_logs(self):
    """Test that LegacyIngestionBackend sanitizes logText and uses ASCII-safe transport."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_session.post.return_value = mock_response
    mock_auth.get_http_client.return_value = mock_session

    backend = LegacyIngestionBackend(
        auth_handler=mock_auth, customer_id="test-customer-id"
    )

    sample_log = "Product: Microsoft\u00ae Windows\u00ae Operating System"
    entries = [{"logText": sample_log}]
    backend.post_unstructured_logs("WINDOWS_SYSMON", entries, labels=[])

    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args

    # Check payload is passed as ASCII-safe JSON data
    data_payload = call_args.kwargs.get("data")
    assert data_payload is not None

    parsed_body = json.loads(data_payload)
    assert parsed_body["customer_id"] == "test-customer-id"
    assert parsed_body["log_type"] == "WINDOWS_SYSMON"

    posted_log_text = parsed_body["entries"][0]["logText"]
    assert "\u00ae" not in posted_log_text
    assert "Microsoft Windows Operating System" in posted_log_text

    # Verify every character in the wire payload is pure 7-bit ASCII
    assert all(ord(c) < 128 for c in data_payload)

  def test_rest_backend_sanitizes_and_base64_encodes(self):
    """Test that RestIngestionBackend sanitizes logText before base64 encoding."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    mock_session = MagicMock()

    # Forwarder check mock
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        "forwarders": [{
            "displayName": "Logstory-REST-Forwarder",
            "name": "projects/p/locations/us/instances/i/forwarders/fwd123",
        }]
    }
    mock_post_response = MagicMock()
    mock_post_response.status_code = 200

    mock_session.get.return_value = mock_get_response
    mock_session.post.return_value = mock_post_response
    mock_auth.get_http_client.return_value = mock_session

    backend = RestIngestionBackend(
        auth_handler=mock_auth,
        customer_id="test-cust",
        project_id="test-proj",
        region="us",
    )

    sample_log = "Product: Microsoft\u00ae Windows\u00ae Operating System"
    entries = [{"logText": sample_log}]
    backend.post_unstructured_logs("WINDOWS_SYSMON", entries, labels=[])

    # Find the import call
    post_calls = mock_session.post.call_args_list
    import_call = post_calls[-1]
    payload = import_call.kwargs.get("json")

    b64_data = payload["inline_source"]["logs"][0]["data"]
    decoded_log = base64.b64decode(b64_data).decode("utf-8")

    assert "\u00ae" not in decoded_log
    assert "Microsoft Windows Operating System" in decoded_log
