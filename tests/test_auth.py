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

"""Tests for authentication validation in logstory."""

import json
import tempfile
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from src.logstory.auth import (
    create_auth_handler,
    validate_credentials_match_api_type,
)


class TestCredentialValidation:
  """Test credential validation for API type matching."""

  def test_rest_api_with_malachite_credentials_raises_error(self):
    """Test that REST API with malachite credentials raises ValueError."""
    malachite_creds = {
        "type": "service_account",
        "client_email": "test@malachite-ltstr740.iam.gserviceaccount.com",
        "private_key": "fake-key",
    }

    with pytest.raises(ValueError) as exc_info:
      validate_credentials_match_api_type("rest", service_account_info=malachite_creds)

    assert "Invalid credentials for REST API" in str(exc_info.value)
    assert "Found legacy malachite credentials" in str(exc_info.value)
    assert "@malachite-ltstr740" in str(exc_info.value)

  def test_rest_api_with_regular_credentials_succeeds(self):
    """Test that REST API with regular credentials works."""
    regular_creds = {
        "type": "service_account",
        "client_email": "test@my-project.iam.gserviceaccount.com",
        "private_key": "fake-key",
    }

    # Should not raise
    validate_credentials_match_api_type("rest", service_account_info=regular_creds)

  def test_legacy_api_with_malachite_credentials_succeeds(self):
    """Test that legacy API with malachite credentials works."""
    malachite_creds = {
        "type": "service_account",
        "client_email": "test@malachite-ltstr740.iam.gserviceaccount.com",
        "private_key": "fake-key",
    }

    # Should not raise
    validate_credentials_match_api_type("legacy", service_account_info=malachite_creds)

  def test_legacy_api_with_regular_credentials_warns(self):
    """Test that legacy API with regular credentials issues warning."""
    regular_creds = {
        "type": "service_account",
        "client_email": "test@my-project.iam.gserviceaccount.com",
        "private_key": "fake-key",
    }

    with warnings.catch_warnings(record=True) as w:
      warnings.simplefilter("always")
      validate_credentials_match_api_type("legacy", service_account_info=regular_creds)

      assert len(w) == 1
      assert "Using non-malachite credentials with legacy API" in str(w[0].message)
      assert "test@my-project.iam.gserviceaccount.com" in str(w[0].message)

  def test_validation_with_credentials_path(self):
    """Test validation when credentials are provided via file path."""
    malachite_creds = {
        "type": "service_account",
        "client_email": "test@malachite-ltstr740.iam.gserviceaccount.com",
        "private_key": "fake-key",
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as temp_file:
      json.dump(malachite_creds, temp_file)
      temp_path = temp_file.name

    try:
      # Should raise error for REST API with malachite credentials
      with pytest.raises(ValueError) as exc_info:
        validate_credentials_match_api_type("rest", credentials_path=temp_path)

      assert "Invalid credentials for REST API" in str(exc_info.value)
    finally:
      Path(temp_path).unlink()

  def test_validation_with_missing_client_email(self):
    """Test validation when client_email is missing from credentials."""
    incomplete_creds = {
        "type": "service_account",
        "private_key": "fake-key",
    }

    # Should not raise (gracefully handles missing client_email)
    validate_credentials_match_api_type("rest", service_account_info=incomplete_creds)

  def test_validation_with_no_credentials(self):
    """Test validation when no credentials are provided."""
    # Should not raise
    validate_credentials_match_api_type("rest")
    validate_credentials_match_api_type("legacy")

  def test_validation_with_invalid_file_path(self):
    """Test validation when credentials file doesn't exist."""
    # Should not raise (lets auth handler deal with missing file)
    validate_credentials_match_api_type(
        "rest", credentials_path="/nonexistent/path.json"
    )

  @patch("src.logstory.auth.detect_auth_type")
  def test_create_auth_handler_validates_credentials(self, mock_detect):
    """Test that create_auth_handler calls validation."""
    mock_detect.return_value = "rest"

    malachite_creds = {
        "type": "service_account",
        "client_email": "test@malachite-ltstr740.iam.gserviceaccount.com",
        "private_key": "fake-key",
        "private_key_id": "fake-id",
        "project_id": "malachite-ltstr740",
    }

    with pytest.raises(ValueError) as exc_info:
      create_auth_handler(api_type="rest", service_account_info=malachite_creds)

    assert "Invalid credentials for REST API" in str(exc_info.value)

  def test_various_malachite_patterns(self):
    """Test detection of various malachite credential patterns."""
    malachite_patterns = [
        "ing-0@malachite-ltstr740.iam.gserviceaccount.com",
        "ltstr740-ing-1710193410@malachite-ltstr740.iam.gserviceaccount.com",
        "test@malachite-prod.iam.gserviceaccount.com",
        "service@malachite-test123.iam.gserviceaccount.com",
    ]

    for email in malachite_patterns:
      creds = {
          "type": "service_account",
          "client_email": email,
          "private_key": "fake-key",
      }

      with pytest.raises(ValueError) as exc_info:
        validate_credentials_match_api_type("rest", service_account_info=creds)

      assert "Invalid credentials for REST API" in str(exc_info.value)
      assert email in str(exc_info.value)
