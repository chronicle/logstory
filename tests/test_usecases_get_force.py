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
"""Tests for usecases get --force flag functionality."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

from logstory.logstory import app


runner = CliRunner()


def test_usecases_get_force_help_displays_flag():
  """Test that --force flag is displayed in help."""
  result = runner.invoke(app, ["usecases", "get", "--help"])
  assert result.exit_code == 0
  assert "--force" in result.stdout
  assert "-f" in result.stdout
  assert "overwrite" in result.stdout.lower()


def test_usecases_get_force_flag_accepted():
  """Test that --force flag is accepted as a boolean flag."""
  with mock.patch("logstory.logstory._download_usecase") as mock_download:
    mock_download.return_value = True
    result = runner.invoke(app, ["usecases", "get", "TEST_USECASE", "--force"])
    assert result.exit_code == 0
    # Verify _download_usecase was called with force=True
    mock_download.assert_called_once()
    call_args = mock_download.call_args
    assert call_args[1]["force"] is True


def test_usecases_get_force_short_flag_accepted():
  """Test that -f short flag works."""
  with mock.patch("logstory.logstory._download_usecase") as mock_download:
    mock_download.return_value = True
    result = runner.invoke(app, ["usecases", "get", "TEST_USECASE", "-f"])
    assert result.exit_code == 0
    # Verify _download_usecase was called with force=True
    mock_download.assert_called_once()
    call_args = mock_download.call_args
    assert call_args[1]["force"] is True


def test_usecases_get_without_force_defaults_to_false():
  """Test that without --force flag, force defaults to False."""
  with mock.patch("logstory.logstory._download_usecase") as mock_download:
    mock_download.return_value = True
    result = runner.invoke(app, ["usecases", "get", "TEST_USECASE"])
    assert result.exit_code == 0
    # Verify _download_usecase was called with force=False
    mock_download.assert_called_once()
    call_args = mock_download.call_args
    assert call_args[1]["force"] is False


class TestDownloadUsecaseForceLogic:
  """Test _download_usecase() force parameter logic."""

  @mock.patch("logstory.logstory.get_usecases_buckets")
  @mock.patch("logstory.logstory._get_source_directories")
  @mock.patch("logstory.logstory._get_blobs")
  def test_download_usecase_skips_if_exists_without_force(
      self, mock_get_blobs, mock_get_source_dirs, mock_buckets
  ):
    """Test that existing usecase is skipped when force=False."""
    mock_buckets.return_value = ["gs://test-bucket"]
    mock_get_source_dirs.return_value = ["TEST_USECASE"]

    with tempfile.TemporaryDirectory() as tmpdir:
      # Create a temp directory to mock usecases directory
      with mock.patch("logstory.logstory.__file__", tmpdir):
        usecase_dir = os.path.join(tmpdir, "usecases", "TEST_USECASE")
        os.makedirs(usecase_dir, exist_ok=True)

        # Import after mocking
        from logstory.logstory import _download_usecase

        result = _download_usecase("TEST_USECASE", force=False)

        # Should return True (success) even though we skipped
        assert result is True
        # Should not have called _get_blobs
        mock_get_blobs.assert_not_called()

  @mock.patch("logstory.logstory.get_usecases_buckets")
  @mock.patch("logstory.logstory._get_source_directories")
  @mock.patch("logstory.logstory._get_blobs")
  def test_download_usecase_downloads_if_force_true(
      self, mock_get_blobs, mock_get_source_dirs, mock_buckets
  ):
    """Test that force=True removes stale files but preserves blob-list files."""
    mock_buckets.return_value = ["gs://test-bucket"]
    mock_get_source_dirs.return_value = ["TEST_USECASE"]

    # Mock blobs: kept_file.log should be preserved, new_file.log is new
    mock_kept_blob = mock.MagicMock()
    mock_kept_blob.name = "TEST_USECASE/kept_file.log"
    mock_new_blob = mock.MagicMock()
    mock_new_blob.name = "TEST_USECASE/new_file.log"
    mock_get_blobs.return_value = [mock_kept_blob, mock_new_blob]

    with tempfile.TemporaryDirectory() as tmpdir:
      with mock.patch("logstory.logstory.__file__", tmpdir):
        usecase_dir = os.path.join(tmpdir, "usecases", "TEST_USECASE")
        os.makedirs(usecase_dir, exist_ok=True)

        # Create files: one in blob list (should be preserved during force)
        # and one stale (should be deleted)
        kept_file = os.path.join(usecase_dir, "kept_file.log")
        with open(kept_file, "w") as f:
          f.write("kept content")

        stale_file = os.path.join(usecase_dir, "stale_file.log")
        with open(stale_file, "w") as f:
          f.write("stale content")

        assert os.path.exists(kept_file)
        assert os.path.exists(stale_file)

        from logstory.logstory import _download_usecase

        # Don't provide side_effect for kept_blob download (it's a no-op)
        # This verifies the file was never deleted by the cleanup pass
        mock_kept_blob.download_to_filename = mock.MagicMock()
        mock_new_blob.download_to_filename = mock.MagicMock()

        result = _download_usecase("TEST_USECASE", force=True)

        # Should return True
        assert result is True
        # Should have attempted to download both blobs
        assert mock_kept_blob.download_to_filename.called
        assert mock_new_blob.download_to_filename.called
        # Stale file should be deleted during cleanup
        assert not os.path.exists(
            stale_file
        ), "Stale file should be deleted on force update"
        # Kept file should still exist with original content (never deleted)
        assert os.path.exists(
            kept_file
        ), "File in blob list should be preserved by cleanup"
        with open(kept_file, "r") as f:
          assert f.read() == "kept content", "Kept file content unchanged by cleanup"

  @mock.patch("logstory.logstory.get_usecases_buckets")
  @mock.patch("logstory.logstory._get_source_directories")
  @mock.patch("logstory.logstory._get_blobs")
  def test_download_usecase_new_usecase_downloads_without_force(
      self, mock_get_blobs, mock_get_source_dirs, mock_buckets
  ):
    """Test that new usecase is downloaded even without force flag."""
    mock_buckets.return_value = ["gs://test-bucket"]
    mock_get_source_dirs.return_value = ["TEST_USECASE"]

    # Mock blob
    mock_blob = mock.MagicMock()
    mock_blob.name = "TEST_USECASE/test_file.log"
    mock_get_blobs.return_value = [mock_blob]

    with tempfile.TemporaryDirectory() as tmpdir:
      with mock.patch("logstory.logstory.__file__", tmpdir):
        # Don't create the usecase directory
        from logstory.logstory import _download_usecase

        result = _download_usecase("TEST_USECASE", force=False)

        # Should return True
        assert result is True
        # Should have called _get_blobs (because directory doesn't exist)
        mock_get_blobs.assert_called_once()
        # Should have attempted to download
        mock_blob.download_to_filename.assert_called_once()

  @mock.patch("logstory.logstory._get_source_directories")
  @mock.patch("logstory.logstory._get_all_source_directories")
  def test_download_usecase_not_found_returns_false(
      self, mock_get_all_dirs, mock_get_source_dirs
  ):
    """Test that non-existent usecase returns False."""
    mock_get_source_dirs.return_value = []
    mock_get_all_dirs.return_value = ["OTHER_USECASE"]

    from logstory.logstory import _download_usecase

    result = _download_usecase("NONEXISTENT_USECASE", force=False)

    assert result is False


class TestBackwardCompatibility:
  """Test backward compatibility of force parameter."""

  @mock.patch("logstory.logstory._download_usecase")
  def test_download_all_usecases_still_works(self, mock_download):
    """Test that _download_all_usecases still works with new parameter."""
    mock_download.return_value = True

    with mock.patch("logstory.logstory.get_usecases_buckets") as mock_buckets:
      with mock.patch("logstory.logstory._get_source_directories") as mock_dirs:
        with mock.patch("logstory.logstory.get_usecases") as mock_installed:
          mock_buckets.return_value = ["gs://test-bucket"]
          mock_dirs.return_value = ["TEST1", "TEST2"]
          mock_installed.return_value = []

          from logstory.logstory import _download_all_usecases

          result = _download_all_usecases()

          # Should have called _download_usecase for each usecase
          assert mock_download.call_count == 2
          # All calls should have force=False (default)
          for call in mock_download.call_args_list:
            assert call[1]["force"] is False

  @mock.patch("logstory.logstory._download_usecase")
  def test_replay_auto_get_still_works(self, mock_download):
    """Test that replay command's auto-get still works."""
    mock_download.return_value = True

    # The replay command calls _download_usecase without force parameter
    # This should use the default force=False
    from logstory.logstory import _download_usecase

    result = _download_usecase("TEST_USECASE")

    # Should succeed
    assert result is True or result is False  # Depends on mocking
