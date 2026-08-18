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

"""Comprehensive tests for authentication and credential validation in logstory."""

import json
import os
import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import DefaultCredentialsError

from logstory.auth import (
    LegacyAuthHandler,
    RestAuthHandler,
    create_auth_handler,
    detect_auth_type,
    has_application_default_credentials,
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

    with pytest.raises(
        ValueError, match="Invalid credentials for REST API"
    ) as exc_info:
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
      with pytest.raises(
          ValueError, match="Invalid credentials for REST API"
      ) as exc_info:
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

    validate_credentials_match_api_type("rest", service_account_info=incomplete_creds)

  def test_validation_with_no_credentials(self):
    """Test validation when no credentials are provided."""
    validate_credentials_match_api_type("rest")
    validate_credentials_match_api_type("legacy")

  def test_validation_with_invalid_file_path(self):
    """Test validation when credentials file doesn't exist."""
    validate_credentials_match_api_type(
        "rest", credentials_path="/nonexistent/path.json"
    )

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

      with pytest.raises(
          ValueError, match="Invalid credentials for REST API"
      ) as exc_info:
        validate_credentials_match_api_type("rest", service_account_info=creds)

      assert "Invalid credentials for REST API" in str(exc_info.value)
      assert email in str(exc_info.value)


class TestLegacyAuthHandler:
  """Test LegacyAuthHandler credential resolution and HTTP client."""

  def test_get_scopes(self):
    """Test scope definition for legacy auth."""
    handler = LegacyAuthHandler()
    assert "https://www.googleapis.com/auth/malachite-ingestion" in handler.get_scopes()

  @patch("google.oauth2.service_account.Credentials.from_service_account_info")
  def test_get_credentials_from_service_account_info(self, mock_from_info):
    """Test loading credentials from dictionary."""
    mock_creds = MagicMock()
    mock_from_info.return_value = mock_creds

    handler = LegacyAuthHandler(
        service_account_info={"client_email": "test@google.com"}
    )
    creds1 = handler.get_credentials()
    creds2 = handler.get_credentials()  # Cached call

    assert creds1 == mock_creds
    assert creds2 == mock_creds
    mock_from_info.assert_called_once()

  @patch("google.oauth2.service_account.Credentials.from_service_account_info")
  def test_get_credentials_from_path(self, mock_from_info):
    """Test loading credentials from file path."""
    mock_creds = MagicMock()
    mock_from_info.return_value = mock_creds

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
      json.dump({"client_email": "path@google.com"}, f)
      temp_path = f.name

    try:
      handler = LegacyAuthHandler(credentials_path=temp_path)
      creds = handler.get_credentials()
      assert creds == mock_creds
      mock_from_info.assert_called_once()
    finally:
      Path(temp_path).unlink()

  @patch("google.cloud.secretmanager.SecretManagerServiceClient")
  @patch("google.oauth2.service_account.Credentials.from_service_account_info")
  def test_get_credentials_from_secret_manager(self, mock_from_info, mock_sm_client):
    """Test loading credentials from Secret Manager."""
    mock_creds = MagicMock()
    mock_from_info.return_value = mock_creds

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.payload.data.decode.return_value = json.dumps(
        {"client_email": "sm@google.com"}
    )
    mock_client_instance.access_secret_version.return_value = mock_response
    mock_sm_client.return_value = mock_client_instance

    handler = LegacyAuthHandler(
        secret_manager_credentials="projects/123/secrets/my-secret"
    )
    creds = handler.get_credentials()
    assert creds == mock_creds
    mock_client_instance.access_secret_version.assert_called_once_with(
        {"name": "projects/123/secrets/my-secret/versions/latest"}
    )

  def test_get_credentials_no_source_raises(self):
    """Test that missing credentials raises ValueError."""
    handler = LegacyAuthHandler()
    with pytest.raises(ValueError, match="No credentials provided"):
      handler.get_credentials()

  @patch("google.auth.transport.requests.AuthorizedSession")
  def test_get_http_client(self, mock_session_class):
    """Test getting authorized HTTP client."""
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session

    handler = LegacyAuthHandler(
        service_account_info={"client_email": "test@google.com"}
    )
    handler._credentials = MagicMock()

    client1 = handler.get_http_client()
    client2 = handler.get_http_client()  # Cached call

    assert client1 == mock_session
    assert client2 == mock_session
    mock_session_class.assert_called_once()


class TestRestAuthHandler:
  """Test RestAuthHandler credential resolution and HTTP client."""

  def test_get_scopes(self):
    """Test scope definition for REST auth."""
    handler = RestAuthHandler()
    assert "https://www.googleapis.com/auth/cloud-platform" in handler.get_scopes()

  @patch("google.oauth2.service_account.Credentials.from_service_account_info")
  def test_get_credentials_from_info(self, mock_from_info):
    """Test REST credentials from dictionary."""
    mock_creds = MagicMock()
    mock_from_info.return_value = mock_creds

    handler = RestAuthHandler(service_account_info={"client_email": "test@google.com"})
    creds = handler.get_credentials()
    assert creds == mock_creds

  @patch("google.oauth2.service_account.Credentials.from_service_account_file")
  def test_get_credentials_from_file(self, mock_from_file):
    """Test REST credentials from file path."""
    mock_creds = MagicMock()
    mock_from_file.return_value = mock_creds

    handler = RestAuthHandler(credentials_path="/path/to/creds.json")
    creds = handler.get_credentials()
    assert creds == mock_creds
    mock_from_file.assert_called_once_with(
        "/path/to/creds.json", scopes=RestAuthHandler.SCOPES
    )

  @patch("google.auth.default")
  def test_get_credentials_from_adc(self, mock_default):
    """Test REST credentials from ADC fallback."""
    mock_creds = MagicMock()
    mock_default.return_value = (mock_creds, "test-project")

    handler = RestAuthHandler()
    creds = handler.get_credentials()
    assert creds == mock_creds
    mock_default.assert_called_once_with(scopes=RestAuthHandler.SCOPES)

  @patch("google.auth.default")
  @patch("google.auth.impersonated_credentials.Credentials")
  def test_get_credentials_with_impersonation(self, mock_impersonate, mock_default):
    """Test REST credentials with service account impersonation."""
    mock_base_creds = MagicMock()
    mock_default.return_value = (mock_base_creds, "test-project")
    mock_imp_creds = MagicMock()
    mock_impersonate.return_value = mock_imp_creds

    handler = RestAuthHandler(
        impersonate_service_account="target@project.iam.gserviceaccount.com"
    )
    creds = handler.get_credentials()
    assert creds == mock_imp_creds
    mock_impersonate.assert_called_once_with(
        source_credentials=mock_base_creds,
        target_principal="target@project.iam.gserviceaccount.com",
        target_scopes=RestAuthHandler.SCOPES,
        lifetime=600,
    )

  @patch("google.auth.transport.requests.AuthorizedSession")
  def test_get_http_client(self, mock_session_class):
    """Test REST HTTP client configuration with User-Agent header."""
    mock_session = MagicMock()
    mock_session.headers = {}
    mock_session_class.return_value = mock_session

    handler = RestAuthHandler(service_account_info={"client_email": "test@google.com"})
    handler._credentials = MagicMock()

    client1 = handler.get_http_client()
    client2 = handler.get_http_client()

    assert client1 == mock_session
    assert client2 == mock_session
    assert mock_session.headers["User-Agent"] == "logstory-rest-api"


class TestHelperFunctions:
  """Test helper and factory functions in auth module."""

  @patch("google.auth.default")
  def test_has_adc_true(self, mock_default):
    """Test has_application_default_credentials when credentials exist."""
    mock_default.return_value = (MagicMock(), "proj")
    assert has_application_default_credentials() is True

  @patch("google.auth.default")
  def test_has_adc_default_credentials_error(self, mock_default):
    """Test has_application_default_credentials when DefaultCredentialsError is raised."""
    mock_default.side_effect = DefaultCredentialsError("No ADC")
    assert has_application_default_credentials() is False

  @patch("google.auth.default")
  def test_has_adc_generic_exception(self, mock_default):
    """Test has_application_default_credentials when generic exception occurs."""
    mock_default.side_effect = RuntimeError("Generic error")
    assert has_application_default_credentials() is False

  def test_detect_auth_type_valid(self):
    """Test detect_auth_type with valid environment variables."""
    with patch.dict(os.environ, {"LOGSTORY_API_TYPE": "REST"}):
      assert detect_auth_type() == "rest"

    with patch.dict(os.environ, {"LOGSTORY_API_TYPE": "legacy"}):
      assert detect_auth_type() == "legacy"

  def test_detect_auth_type_missing_raises(self):
    """Test detect_auth_type when LOGSTORY_API_TYPE is unset."""
    with patch.dict(os.environ, {}, clear=True):
      with pytest.raises(
          ValueError, match="LOGSTORY_API_TYPE environment variable must be set"
      ):
        detect_auth_type()

  def test_detect_auth_type_invalid_raises(self):
    """Test detect_auth_type when LOGSTORY_API_TYPE is invalid."""
    with patch.dict(os.environ, {"LOGSTORY_API_TYPE": "invalid_type"}):
      with pytest.raises(ValueError, match="Must be 'rest' or 'legacy'"):
        detect_auth_type()

  @patch("logstory.auth.detect_auth_type")
  def test_create_auth_handler_auto_detect(self, mock_detect):
    """Test create_auth_handler auto-detects API type when None provided."""
    mock_detect.return_value = "legacy"
    handler = create_auth_handler(
        service_account_info={
            "client_email": "test@malachite-ltstr740.iam.gserviceaccount.com"
        }
    )
    assert isinstance(handler, LegacyAuthHandler)

  def test_create_auth_handler_rest_with_secret_manager_raises(self):
    """Test create_auth_handler raises ValueError for REST with Secret Manager."""
    with pytest.raises(
        ValueError, match="Secret Manager credentials are not supported with REST API"
    ):
      create_auth_handler(
          api_type="rest", secret_manager_credentials="projects/123/secrets/x"
      )

  def test_create_auth_handler_legacy_with_impersonation_raises(self):
    """Test create_auth_handler raises ValueError for Legacy with impersonation."""
    with pytest.raises(
        ValueError,
        match="Service account impersonation is not supported with legacy API",
    ):
      create_auth_handler(
          api_type="legacy", impersonate_service_account="sa@project.com"
      )

  def test_create_auth_handler_unknown_type_raises(self):
    """Test create_auth_handler raises ValueError for unknown API type."""
    with pytest.raises(ValueError, match="Unknown API type: invalid"):
      create_auth_handler(api_type="invalid")

  @patch("google.auth.default")
  def test_create_auth_handler_rest_defaults(self, mock_default):
    """Test create_auth_handler with REST API defaults."""
    mock_default.return_value = (MagicMock(), "proj")
    handler = create_auth_handler(api_type="rest")
    assert isinstance(handler, RestAuthHandler)
