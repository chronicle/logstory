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

"""Comprehensive tests for Logstory Typer CLI interface and helper functions."""

import json
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from logstory.logstory import (
    _download_all_usecases,
    _download_usecase,
    _FileBlob,
    _get_all_source_directories,
    _get_blobs,
    _get_file_blobs,
    _get_gcs_blobs,
    _get_logtypes,
    _get_source_directories,
    _load_and_validate_params,
    _set_environment_vars,
    app,
    entry_point,
    get_auto_get_default,
    get_credentials_default,
    get_customer_id_default,
    get_region_default,
    get_timestamp_delta_default,
    get_usecases,
    get_usecases_buckets,
    list_bucket_directories,
    load_env_file,
    parse_usecase_source,
    validate_credentials_file,
    validate_uuid4,
    version_callback,
)

runner = CliRunner()


class TestCliValidators:
  """Test parameter validation functions in CLI module."""

  def test_version_callback_true_raises_exit(self):
    """Test version_callback displays version and exits."""
    with pytest.raises(typer.Exit):
      version_callback(True)

  def test_version_callback_false_noop(self):
    """Test version_callback does nothing when False."""
    version_callback(False)

  def test_validate_uuid4_valid(self):
    """Test valid UUID4 strings."""
    valid_uuid = str(uuid.uuid4())
    assert validate_uuid4(valid_uuid) == valid_uuid

  def test_validate_uuid4_invalid_raises(self):
    """Test invalid UUID raises BadParameter."""
    with pytest.raises(typer.BadParameter, match="is not a valid UUID4"):
      validate_uuid4("not-a-uuid")

  @patch("google.oauth2.service_account.Credentials.from_service_account_file")
  def test_validate_credentials_file_valid(self, mock_creds):
    """Test valid credentials file path."""
    mock_creds.return_value = MagicMock()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
      temp_path = f.name

    try:
      assert validate_credentials_file(temp_path) == temp_path
    finally:
      Path(temp_path).unlink()

  def test_validate_credentials_file_missing_raises(self):
    """Test non-existent file raises BadParameter."""
    with pytest.raises(typer.BadParameter, match="File does not exist"):
      validate_credentials_file("/nonexistent/file.json")

  def test_validate_credentials_file_invalid_json_raises(self):
    """Test corrupted JSON file raises BadParameter."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
      f.write("corrupted content")
      temp_path = f.name

    try:
      with pytest.raises(typer.BadParameter, match="The JSON file is invalid"):
        validate_credentials_file(temp_path)
    finally:
      Path(temp_path).unlink()


class TestCliDefaultsAndEnv:
  """Test default value resolution and environment loading."""

  def test_get_credentials_default_from_json(self):
    """Test extracting credentials from LOGSTORY_CREDENTIALS json string."""
    valid_json = json.dumps({"type": "service_account", "client_email": "a@b.com"})
    with patch.dict(os.environ, {"LOGSTORY_CREDENTIALS": valid_json}):
      temp_path = get_credentials_default()
      assert temp_path is not None
      assert os.path.exists(temp_path)
      Path(temp_path).unlink()

  def test_get_credentials_default_from_path(self):
    """Test fallback to LOGSTORY_CREDENTIALS_PATH."""
    with patch.dict(
        os.environ, {"LOGSTORY_CREDENTIALS_PATH": "/custom/path.json"}, clear=True
    ):
      assert get_credentials_default() == "/custom/path.json"

  def test_get_customer_id_default(self):
    """Test customer ID default getter."""
    with patch.dict(os.environ, {"LOGSTORY_CUSTOMER_ID": "cust-123"}):
      assert get_customer_id_default() == "cust-123"

  def test_get_region_default(self):
    """Test region default getter."""
    with patch.dict(os.environ, {"LOGSTORY_REGION": "europe"}):
      assert get_region_default() == "europe"
    with patch.dict(os.environ, {}, clear=True):
      assert get_region_default() == "US"

  def test_get_timestamp_delta_default(self):
    """Test timestamp delta default getter."""
    with patch.dict(os.environ, {"LOGSTORY_TIMESTAMP_DELTA": "3d"}):
      assert get_timestamp_delta_default() == "3d"
    with patch.dict(os.environ, {}, clear=True):
      assert get_timestamp_delta_default() == "1d"

  def test_get_auto_get_default(self):
    """Test auto get default getter."""
    with patch.dict(os.environ, {"LOGSTORY_AUTO_GET": "true"}):
      assert get_auto_get_default() is True
    with patch.dict(os.environ, {"LOGSTORY_AUTO_GET": "0"}):
      assert get_auto_get_default() is False

  def test_load_env_file(self):
    """Test load_env_file behavior."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
      f.write("TEST_KEY_123=value_123\n")
      env_path = f.name

    try:
      load_env_file(env_path)
      assert os.environ.get("TEST_KEY_123") == "value_123"
    finally:
      Path(env_path).unlink()

    load_env_file("/nonexistent/file.env")


class TestSourceParsingAndBlobMocking:
  """Test parsing GCS/file sources and blob collections."""

  def test_parse_usecase_source(self):
    """Test source URI parsing."""
    assert parse_usecase_source("gs://my-bucket/usecases") == (
        "gcs",
        "my-bucket/usecases",
    )
    assert parse_usecase_source("git@github.com:repo.git") == (
        "git",
        "git@github.com:repo.git",
    )
    assert parse_usecase_source("s3://my-s3-bucket") == ("s3", "my-s3-bucket")
    assert parse_usecase_source("file:///local/dir") == ("file", "/local/dir")
    assert parse_usecase_source("bare-bucket-name") == ("gcs", "bare-bucket-name")

  def test_get_usecases_buckets(self):
    """Test parsing multiple usecases bucket URIs from env."""
    with patch.dict(os.environ, {"LOGSTORY_USECASES_BUCKETS": "gs://b1, gs://b2"}):
      buckets = get_usecases_buckets()
      assert buckets == ["gs://b1", "gs://b2"]

  def test_file_blob_and_collection(self):
    """Test _FileBlob, _FileBlobPage, and _FileBlobCollection emulation."""
    with tempfile.TemporaryDirectory() as tmpdir:
      sub_dir = Path(tmpdir) / "MY_UC"
      sub_dir.mkdir(parents=True, exist_ok=True)
      (sub_dir / "test.log").write_text("sample content", encoding="utf-8")

      blobs = _get_file_blobs(tmpdir)
      assert len(blobs.pages) == 1
      assert "MY_UC/" in blobs.pages[0].prefixes

      # Test _FileBlob download
      fb = _FileBlob("test.log", str(sub_dir / "test.log"))
      dest = Path(tmpdir) / "dest.log"
      fb.download_to_filename(str(dest))
      assert dest.read_text(encoding="utf-8") == "sample content"

  @patch("logstory.logstory.storage.Client")
  def test_get_gcs_blobs(self, mock_storage_client):
    """Test _get_gcs_blobs with GCS client."""
    mock_client = MagicMock()
    mock_storage_client.return_value = mock_client
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_blobs = [MagicMock()]
    mock_bucket.list_blobs.return_value = mock_blobs

    res = _get_gcs_blobs("test-bucket", usecase="UC1")
    assert res == mock_blobs
    mock_bucket.list_blobs.assert_called_once_with(prefix="UC1")

  def test_get_blobs_dispatcher(self):
    """Test _get_blobs dispatching to GCS or file."""
    with patch("logstory.logstory._get_gcs_blobs", return_value=["gcs_blob"]):
      assert _get_blobs("gs://bucket1") == ["gcs_blob"]

    with patch("logstory.logstory._get_file_blobs", return_value=["file_blob"]):
      assert _get_blobs("file:///tmp/path") == ["file_blob"]


class TestDiscoveryAndDownloads:
  """Test discovering use cases and downloading files."""

  def test_list_bucket_directories_gcs(self):
    """Test list_bucket_directories extracting prefixes."""
    mock_blobs = MagicMock()
    mock_page = MagicMock()
    mock_page.prefixes = ["UC_A/", "UC_B/"]
    mock_blobs.pages = [mock_page]

    with patch("logstory.logstory._get_blobs", return_value=mock_blobs):
      with patch.dict(os.environ, {"LOGSTORY_USECASES_BUCKETS": "gs://my-bucket"}):
        dirs = list_bucket_directories(env_file=None, bucket="gs://my-bucket")
        assert "UC_A" in dirs
        assert "UC_B" in dirs

  def test_get_source_directories(self):
    """Test _get_source_directories wrapper."""
    mock_blobs = MagicMock()
    mock_page = MagicMock()
    mock_page.prefixes = ["UC1/"]
    mock_blobs.pages = [mock_page]
    with patch("logstory.logstory._get_blobs", return_value=mock_blobs):
      assert _get_source_directories("gs://b1") == ["UC1"]

  def test_get_all_source_directories(self):
    """Test _get_all_source_directories aggregating directories."""
    with patch("logstory.logstory.get_usecases_buckets", return_value=["gs://b1"]):
      with patch(
          "logstory.logstory._get_source_directories", return_value=["UC1", "UC2"]
      ):
        dirs = _get_all_source_directories()
        assert "UC1" in dirs
        assert "UC2" in dirs

  def test_download_usecase(self):
    """Test _download_usecase downloading blob files."""
    mock_blob = MagicMock()
    mock_blob.name = "UC_TEST/EVENTS/sysmon.log"

    with patch("logstory.logstory._get_source_directories", return_value=["UC_TEST"]):
      with patch("logstory.logstory._get_blobs", return_value=[mock_blob]):
        with patch("logstory.logstory.storage.Client"):
          assert _download_usecase("UC_TEST", bucket="gs://bucket") is True

  def test_download_all_usecases(self):
    """Test _download_all_usecases."""
    with patch("logstory.logstory._get_source_directories", return_value=["UC1"]):
      with patch("logstory.logstory._download_usecase", return_value=True):
        assert _download_all_usecases("gs://bucket") == 1

  def test_get_logtypes_and_get_usecases(self):
    """Test discovery of local usecases and logtypes."""
    usecases = get_usecases()
    assert isinstance(usecases, list)

    logtypes = _get_logtypes("NETWORK_ANALYSIS", entities=False)
    assert isinstance(logtypes, list)


class TestParamValidationAndEnvSetup:
  """Test parameter loading, validation and environment configuration."""

  def test_load_and_validate_params_rest_missing_project_id_raises(self):
    """Test REST API without project ID raises Exit."""
    with patch.dict(os.environ, {"LOGSTORY_API_TYPE": "rest"}, clear=True):
      with pytest.raises(typer.Exit):
        _load_and_validate_params(
            env_file=None,
            credentials_path=None,
            customer_id="12345678-1234-4234-8234-123456789abc",
            region="us",
            api_type="rest",
        )

  def test_load_and_validate_params_missing_customer_id_raises(self):
    """Test missing customer ID raises Exit."""
    with patch.dict(os.environ, {}, clear=True):
      with pytest.raises(typer.Exit):
        _load_and_validate_params(
            env_file=None,
            credentials_path=None,
            customer_id=None,
            region="us",
        )

  def test_set_environment_vars(self):
    """Test setting runtime environment variables."""
    _set_environment_vars(
        credentials_path="/path/creds.json",
        customer_id="cust-123",
        region="europe",
        api_type="rest",
        project_id="proj-123",
        forwarder_name="fwd-1",
        impersonate_service_account="sa@proj.com",
    )
    assert os.environ["CUSTOMER_ID"] == "cust-123"
    assert os.environ["CREDENTIALS_PATH"] == "/path/creds.json"
    assert os.environ["REGION"] == "europe"
    assert os.environ["LOGSTORY_API_TYPE"] == "rest"
    assert os.environ["LOGSTORY_PROJECT_ID"] == "proj-123"
    assert os.environ["LOGSTORY_FORWARDER_NAME"] == "fwd-1"
    assert os.environ["LOGSTORY_IMPERSONATE_SERVICE_ACCOUNT"] == "sa@proj.com"


class TestCliCommandsExecution:
  """Test CLI command invocations via CliRunner."""

  def test_version_command(self):
    """Test --version flag output."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "logstory" in result.stdout

  def test_usecases_list_installed_command(self):
    """Test logstory usecases list-installed command."""
    result = runner.invoke(app, ["usecases", "list-installed"])
    assert result.exit_code == 0

  def test_usecases_list_installed_logtypes(self):
    """Test logstory usecases list-installed --logtypes."""
    result = runner.invoke(app, ["usecases", "list-installed", "--logtypes"])
    assert result.exit_code == 0

  def test_usecases_list_installed_details(self):
    """Test logstory usecases list-installed --details."""
    result = runner.invoke(app, ["usecases", "list-installed", "--details"])
    assert result.exit_code == 0

  def test_usecases_list_available_command(self):
    """Test logstory usecases list-available command."""
    mock_blobs = MagicMock()
    mock_page = MagicMock(prefixes=["UC_REMOTE/"])
    mock_blobs.pages = [mock_page]

    with patch("logstory.logstory._get_blobs", return_value=mock_blobs):
      result = runner.invoke(app, ["usecases", "list-available"])
      assert result.exit_code == 0
      assert "UC_REMOTE" in result.stdout

  def test_usecase_get_command(self):
    """Test logstory usecases get command."""
    with patch("logstory.logstory._download_usecase", return_value=True):
      result = runner.invoke(app, ["usecases", "get", "UC_SAMPLE"])
      assert result.exit_code == 0

  def test_replay_all_usecases_command(self):
    """Test logstory replay all command with local file output."""
    with patch(
        "logstory.logstory.imported_main.usecase_replay_logtype", return_value=None
    ):
      result = runner.invoke(
          app,
          [
              "replay",
              "all",
              "--local-file-output",
              "--no-get",
          ],
      )
      assert result.exit_code == 0

  def test_replay_usecase_command(self):
    """Test logstory replay usecase command."""
    with patch("logstory.logstory.get_usecases", return_value=["NETWORK_ANALYSIS"]):
      with patch(
          "logstory.logstory.imported_main.usecase_replay_logtype",
          return_value=None,
      ):
        result = runner.invoke(
            app,
            [
                "replay",
                "usecase",
                "NETWORK_ANALYSIS",
                "--local-file-output",
                "--no-get",
            ],
        )
        assert result.exit_code == 0

  def test_replay_usecase_logtype_command(self):
    """Test logstory replay logtype command."""
    with patch("logstory.logstory.get_usecases", return_value=["NETWORK_ANALYSIS"]):
      with patch(
          "logstory.logstory.imported_main.usecase_replay_logtype",
          return_value=None,
      ):
        result = runner.invoke(
            app,
            [
                "replay",
                "logtype",
                "NETWORK_ANALYSIS",
                "BRO_JSON",
                "--local-file-output",
            ],
        )
        assert result.exit_code == 0

  def test_entry_point(self):
    """Test entry_point function calls app()."""
    with patch("logstory.logstory.app") as mock_app:
      entry_point()
      mock_app.assert_called_once()


class TestCliAdvancedBranches:
  """Test edge cases and advanced branches in CLI module."""

  def test_usecases_list_open_nonexistent(self):
    """Test --open with nonexistent usecase returns non-zero code."""
    result = runner.invoke(
        app, ["usecases", "list-installed", "--open", "NONEXISTENT_UC"]
    )
    assert result.exit_code != 0

  @patch("subprocess.run")
  def test_usecases_list_open_success(self, mock_subprocess):
    """Test --open with existing usecase runs code command."""
    with patch("glob.glob") as mock_glob:
      mock_glob.side_effect = [
          ["/path/usecases/NETWORK_ANALYSIS"],
          ["/path/usecases/NETWORK_ANALYSIS/README.md"],
      ]
      result = runner.invoke(
          app, ["usecases", "list-installed", "--open", "NETWORK_ANALYSIS"]
      )
      assert result.exit_code == 0
      mock_subprocess.assert_called_once()

  @patch("subprocess.run", side_effect=FileNotFoundError)
  def test_usecases_list_open_no_code_cli_raises(self, mock_subprocess):
    """Test --open when code CLI not found returns non-zero code."""
    with patch("glob.glob") as mock_glob:
      mock_glob.side_effect = [
          ["/path/usecases/NETWORK_ANALYSIS"],
          ["/path/usecases/NETWORK_ANALYSIS/README.md"],
      ]
      result = runner.invoke(
          app, ["usecases", "list-installed", "--open", "NETWORK_ANALYSIS"]
      )
      assert result.exit_code != 0

  def test_replay_usecase_not_found_raises(self):
    """Test replaying non-existent usecase raises Exit."""
    with patch("logstory.logstory.get_usecases", return_value=["OTHER_UC"]):
      with patch("logstory.logstory._download_usecase", return_value=False):
        result = runner.invoke(app, ["replay", "usecase", "MISSING_UC", "--no-get"])
        assert result.exit_code != 0

  @patch("google.oauth2.service_account.Credentials.from_service_account_file")
  def test_replay_all_with_credentials(self, mock_from_file):
    """Test replay all with credentials path and customer ID."""
    mock_from_file.return_value = MagicMock()
    valid_uuid = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
      cred_path = f.name

    try:
      with patch(
          "logstory.logstory.imported_main.usecase_replay_logtype",
          return_value=None,
      ):
        result = runner.invoke(
            app,
            [
                "replay",
                "all",
                "--credentials-path",
                cred_path,
                "--customer-id",
                valid_uuid,
                "--no-get",
            ],
        )
        assert result.exit_code == 0
    finally:
      Path(cred_path).unlink()

  @patch("google.oauth2.service_account.Credentials.from_service_account_file")
  def test_replay_usecase_with_credentials(self, mock_from_file):
    """Test replay usecase with credentials path and customer ID."""
    mock_from_file.return_value = MagicMock()
    valid_uuid = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
      cred_path = f.name

    try:
      with patch("logstory.logstory.get_usecases", return_value=["NETWORK_ANALYSIS"]):
        with patch(
            "logstory.logstory.imported_main.usecase_replay_logtype",
            return_value=None,
        ):
          result = runner.invoke(
              app,
              [
                  "replay",
                  "usecase",
                  "NETWORK_ANALYSIS",
                  "--credentials-path",
                  cred_path,
                  "--customer-id",
                  valid_uuid,
                  "--no-get",
              ],
          )
          assert result.exit_code == 0
    finally:
      Path(cred_path).unlink()

  @patch("google.oauth2.service_account.Credentials.from_service_account_file")
  def test_replay_logtype_with_credentials(self, mock_from_file):
    """Test replay logtype with credentials path and customer ID."""
    mock_from_file.return_value = MagicMock()
    valid_uuid = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
      cred_path = f.name

    try:
      with patch(
          "logstory.logstory.imported_main.usecase_replay_logtype",
          return_value=None,
      ):
        result = runner.invoke(
            app,
            [
                "replay",
                "logtype",
                "NETWORK_ANALYSIS",
                "BRO_JSON",
                "--credentials-path",
                cred_path,
                "--customer-id",
                valid_uuid,
            ],
        )
        assert result.exit_code == 0
    finally:
      Path(cred_path).unlink()


class TestPackageInit:
  """Test package __init__.py version resolution."""

  def test_package_not_found_version_fallback(self):
    """Test version fallback when package metadata not found."""
    import importlib
    import importlib.metadata
    from unittest.mock import patch

    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError,
    ):
      import logstory

      importlib.reload(logstory)
      assert logstory.__version__ == "1.2.3"
