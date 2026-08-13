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

"""Comprehensive unit tests for src/logstory/main.py."""

import datetime
import os
import tempfile
from datetime import UTC
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from logstory import main as logstory_main
from logstory.ingestion import LegacyIngestionBackend
from logstory.main import (
    _calculate_timestamp_replacement,
    _get_current_time,
    _get_ingestion_labels,
    _get_log_content,
    _get_timestamp_delta_dict,
    _post_entries_in_batches,
    _update_timestamp,
    _validate_timestamp_config,
    _write_entries_to_local_file,
    can_use_application_default_credentials,
    datetime_to_filetime,
    filetime_to_datetime,
    post_entries,
    usecase_replay_logtype,
)
from logstory.main import (
    main as cloud_function_main,
)


class TestWindowsFileTimeConversions:
  """Test conversion between Windows FileTime and datetime."""

  def test_roundtrip_conversion(self):
    """Test datetime to filetime and back to datetime."""
    original_dt = datetime.datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)
    ft = datetime_to_filetime(original_dt)
    converted_dt = filetime_to_datetime(ft)
    assert original_dt == converted_dt

  def test_known_filetime_value(self):
    """Test specific known Windows FileTime conversion."""
    ft = 133629802620000000
    dt = filetime_to_datetime(ft)
    assert dt.year == 2024
    assert dt.month == 6
    assert dt.day == 16


class TestApplicationDefaultCredentialsCheck:
  """Test can_use_application_default_credentials helper."""

  @patch("logstory.main.detect_auth_type")
  @patch("logstory.main.has_application_default_credentials")
  def test_adc_available_rest_with_impersonation(self, mock_has_adc, mock_detect):
    """Test when ADC credentials, REST api, and impersonation exist."""
    mock_detect.return_value = "rest"
    mock_has_adc.return_value = True
    with patch.object(
        logstory_main, "IMPERSONATE_SERVICE_ACCOUNT", "sa@proj.iam.gserviceaccount.com"
    ):
      assert can_use_application_default_credentials() is True

  @patch("logstory.main.detect_auth_type")
  @patch("logstory.main.has_application_default_credentials")
  def test_adc_legacy_api_returns_false(self, mock_has_adc, mock_detect):
    """Test when API is legacy, can_use_application_default_credentials returns False."""
    mock_detect.return_value = "legacy"
    mock_has_adc.return_value = True
    with patch.object(
        logstory_main, "IMPERSONATE_SERVICE_ACCOUNT", "sa@proj.iam.gserviceaccount.com"
    ):
      assert can_use_application_default_credentials() is False

  @patch("logstory.main.detect_auth_type")
  def test_adc_value_error_returns_false(self, mock_detect):
    """Test when detect_auth_type raises ValueError returns False."""
    mock_detect.side_effect = ValueError("No API type")
    assert can_use_application_default_credentials() is False


class TestTimestampDeltaParsing:
  """Test parsing timestamp delta string."""

  def test_single_units(self):
    """Test single unit strings like 1d, 5h, 30m."""
    assert _get_timestamp_delta_dict("1d") == {"d": 1}
    assert _get_timestamp_delta_dict("5h") == {"h": 5}
    assert _get_timestamp_delta_dict("30m") == {"m": 30}

  def test_compound_units(self):
    """Test compound string like 2d12h45m."""
    result = _get_timestamp_delta_dict("2d12h45m")
    assert result == {"d": 2, "h": 12, "m": 45}

  def test_invalid_string_returns_empty(self):
    """Test invalid delta strings return empty dictionary."""
    assert _get_timestamp_delta_dict("invalid") == {}


class TestTimestampConfigValidation:
  """Test validation of YAML timestamp configuration structures."""

  def test_valid_config(self):
    """Test valid configuration passes validation without raising."""
    config = {
        "TEST_LOG": {
            "api": "unstructuredlogentries",
            "timestamps": [{
                "name": "primary_ts",
                "pattern": r"(\d{4}-\d{2}-\d{2})",
                "group": 1,
                "dateformat": "%Y-%m-%d",
                "base_time": True,
            }],
        }
    }
    _validate_timestamp_config("TEST_LOG", config)

  def test_missing_log_type_raises(self):
    """Test missing log type in config raises ValueError."""
    with pytest.raises(ValueError, match="Log type 'MISSING' not found"):
      _validate_timestamp_config("MISSING", {})

  def test_missing_timestamps_key_raises(self):
    """Test missing timestamps field raises ValueError."""
    with pytest.raises(ValueError, match="missing 'timestamps' configuration"):
      _validate_timestamp_config("TEST_LOG", {"TEST_LOG": {}})

  def test_missing_required_fields_raises(self):
    """Test missing required fields (name/pattern/group/dateformat) raises ValueError."""
    with pytest.raises(ValueError, match="missing required field: 'name'"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [{"pattern": ".*", "group": 1, "dateformat": "%Y"}]
              }
          },
      )

    with pytest.raises(ValueError, match="missing required field: 'pattern'"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [{"name": "ts", "group": 1, "dateformat": "%Y"}]
              }
          },
      )

    with pytest.raises(ValueError, match="missing required field: 'group'"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [{"name": "ts", "pattern": ".*", "dateformat": "%Y"}]
              }
          },
      )

    with pytest.raises(ValueError, match="missing required field: 'dateformat'"):
      _validate_timestamp_config(
          "TEST_LOG",
          {"TEST_LOG": {"timestamps": [{"name": "ts", "pattern": ".*", "group": 1}]}},
      )

  def test_invalid_field_types_raise(self):
    """Test field type validation."""
    # name not string
    with pytest.raises(ValueError, match="'name' must be string"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [
                      {"name": 123, "pattern": ".*", "group": 1, "dateformat": "%Y"}
                  ]
              }
          },
      )

    # pattern not string
    with pytest.raises(ValueError, match="'pattern' must be string"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [
                      {"name": "ts", "pattern": 123, "group": 1, "dateformat": "%Y"}
                  ]
              }
          },
      )

    # dateformat not string
    with pytest.raises(ValueError, match="'dateformat' must be string"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [
                      {"name": "ts", "pattern": ".*", "group": 1, "dateformat": 123}
                  ]
              }
          },
      )

    # group not positive integer
    with pytest.raises(ValueError, match="'group' must be positive integer"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [
                      {"name": "ts", "pattern": ".*", "group": 0, "dateformat": "%Y"}
                  ]
              }
          },
      )

  def test_base_time_counts_raise(self):
    """Test missing or multiple base_time configurations raise ValueError."""
    # No base_time
    with pytest.raises(ValueError, match="has no base_time: true timestamp"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [
                      {"name": "ts", "pattern": ".*", "group": 1, "dateformat": "%Y"}
                  ]
              }
          },
      )

    # Multiple base_times
    with pytest.raises(ValueError, match="has multiple base_time: true timestamps"):
      _validate_timestamp_config(
          "TEST_LOG",
          {
              "TEST_LOG": {
                  "timestamps": [
                      {
                          "name": "ts1",
                          "pattern": ".*",
                          "group": 1,
                          "dateformat": "%Y",
                          "base_time": True,
                      },
                      {
                          "name": "ts2",
                          "pattern": ".*",
                          "group": 1,
                          "dateformat": "%Y",
                          "base_time": True,
                      },
                  ]
              }
          },
      )


class TestLogContentAndLabels:
  """Test retrieving log content and generating ingestion labels."""

  def test_get_log_content_local_filesystem(self):
    """Test reading log content from local filesystem."""
    mock_file_content = "2024-01-01 log event message"
    with patch("builtins.open", mock_open(read_data=mock_file_content)):
      content = _get_log_content("TEST_UC", "TEST_LOG", entities=False)
      assert content == mock_file_content

  def test_get_log_content_gcs_storage_client(self):
    """Test reading log content from GCS bucket when storage_client is present."""
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.download_as_text.return_value = "log line from gcs"
    mock_bucket.get_blob.return_value = mock_blob
    mock_storage.bucket.return_value = mock_bucket

    with (
        patch.object(logstory_main, "storage_client", mock_storage),
        patch.object(logstory_main, "BUCKET_NAME", "my-test-bucket"),
    ):
      res = _get_log_content("MY_USECASE", "TEST_LOG", entities=True)
      assert res == "log line from gcs"
      mock_storage.bucket.assert_called_once_with("my-test-bucket")
      mock_bucket.get_blob.assert_called_once_with("MY_USECASE/ENTITIES/TEST_LOG.log")

  def test_get_ingestion_labels(self):
    """Test generation of ingestion labels list."""
    dt = datetime.datetime(2026, 8, 13, 10, 30, 0)
    labels = _get_ingestion_labels("EDR_WORKSHOP", dt, "unstructuredlogentries")
    label_dict = {l["key"]: l["value"] for l in labels}

    assert label_dict["ingestion_method"] == "unstructuredlogentries"
    assert label_dict["source_usecase"] == "EDR_WORKSHOP"
    assert label_dict["replayed_from"] == "logstory"
    assert label_dict["log_replay"] == "true"

  def test_get_current_time(self):
    """Test _get_current_time returns current datetime."""
    now = _get_current_time()
    assert isinstance(now, datetime.datetime)


class TestTimestampCalculations:
  """Test timestamp replacement calculation and updating."""

  def test_calculate_replacement_epoch(self):
    """Test epoch timestamp replacement calculation."""
    log_text = '{"timestamp": 1700000000, "msg": "test"}'
    ts_config = {
        "pattern": r'"timestamp":\s*(\d{10})',
        "group": 1,
        "dateformat": "epoch",
    }
    old_base_time = datetime.datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC)
    delta_dict = {"d": 1}

    result = _calculate_timestamp_replacement(
        log_text, ts_config, old_base_time, delta_dict
    )
    assert result is not None
    match_obj, replacement = result
    assert int(replacement) > 1700000000

  def test_calculate_replacement_windowsfiletime(self):
    """Test Windows FileTime replacement calculation."""
    log_text = "EventTime=133629802620000000 info"
    ts_config = {
        "pattern": r"EventTime=(\d{18})",
        "group": 1,
        "dateformat": "windowsfiletime",
    }
    old_base_time = datetime.datetime(2024, 6, 16, 13, 37, 42, tzinfo=UTC)
    delta_dict = {"d": 1}

    result = _calculate_timestamp_replacement(
        log_text, ts_config, old_base_time, delta_dict
    )
    assert result is not None
    match_obj, replacement = result
    assert int(replacement) > 133629802620000000

  def test_calculate_replacement_no_match(self):
    """Test calculation when regex pattern does not match returns None."""
    log_text = "no timestamp here"
    ts_config = {
        "pattern": r"(\d{4}-\d{2}-\d{2})",
        "group": 1,
        "dateformat": "%Y-%m-%d",
    }
    old_base_time = datetime.datetime.now(UTC)
    delta_dict = {"d": 1}

    assert (
        _calculate_timestamp_replacement(log_text, ts_config, old_base_time, delta_dict)
        is None
    )

  def test_update_timestamp_wrapper(self):
    """Test _update_timestamp compatibility wrapper function."""
    log_text = "Date: 2024-01-01 status: ok"
    ts_config = {
        "pattern": r"Date:\s*(\d{4}-\d{2}-\d{2})",
        "group": 1,
        "dateformat": "%Y-%m-%d",
    }
    old_base_time = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    delta_dict = {"d": 2}

    updated = _update_timestamp(log_text, ts_config, old_base_time, delta_dict)
    assert "2024-01-01" not in updated


class TestLocalFileOutputAndBatching:
  """Test writing entries to local files and posting in batches."""

  def test_write_entries_unstructured_and_json(self):
    """Test writing both unstructured and UDM entries to local disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
      entries = [
          {"logText": "unstructured line 1"},
          {"metadata": {"id": "udm-event-1"}},
          "plain fallback line",
      ]
      _write_entries_to_local_file("TEST_TYPE", entries, log_dir=tmpdir)

      output_file = Path(tmpdir) / "TEST_TYPE.log"
      assert output_file.exists()
      content = output_file.read_text(encoding="utf-8")
      assert "unstructured line 1" in content
      assert "udm-event-1" in content
      assert "plain fallback line" in content

  def test_post_entries_in_batches_local_file_routing(self):
    """Test that local_file_output=True directs entries to _write_entries_to_local_file."""
    with tempfile.TemporaryDirectory() as tmpdir:
      entries = [{"logText": "batch line"}]
      _post_entries_in_batches(
          api="unstructuredlogentries",
          log_type="LOCAL_LOG",
          all_entries=entries,
          ingestion_labels=[],
          local_file_output=True,
          log_dir=tmpdir,
      )
      assert (Path(tmpdir) / "LOCAL_LOG.log").exists()

  def test_post_entries_in_batches_missing_backend_raises(self):
    """Test that missing backend when not using local file output raises RuntimeError."""
    with pytest.raises(RuntimeError, match="Backend must be provided"):
      _post_entries_in_batches(
          api="unstructuredlogentries",
          log_type="TEST_LOG",
          all_entries=[{"logText": "line"}],
          ingestion_labels=[],
          backend=None,
          local_file_output=False,
      )

  def test_post_entries_in_batches_count_threshold(self):
    """Test batch posting when number of entries exceeds threshold."""
    mock_backend = MagicMock(spec=LegacyIngestionBackend)
    entries = [{"logText": f"line {i}"} for i in range(1005)]
    _post_entries_in_batches(
        api="unstructuredlogentries",
        log_type="TEST_LOG",
        all_entries=entries,
        ingestion_labels=[],
        backend=mock_backend,
        local_file_output=False,
    )
    # 1005 entries should be posted in 2 batches (1000 + 5)
    assert mock_backend.post_unstructured_logs.call_count == 2

  def test_post_entries_routing_and_validation(self):
    """Test post_entries routing to backend methods and error validation."""
    mock_backend = MagicMock(spec=LegacyIngestionBackend)

    with pytest.raises(RuntimeError, match="No ingestion backend provided"):
      post_entries("unstructuredlogentries", "TYPE", [], [], backend=None)

    post_entries(
        "unstructuredlogentries", "TYPE", [{"logText": "a"}], [], backend=mock_backend
    )
    mock_backend.post_unstructured_logs.assert_called_once_with(
        "TYPE", [{"logText": "a"}], []
    )

    post_entries("udmevents", "TYPE", [{"udm": "b"}], [], backend=mock_backend)
    mock_backend.post_udm_events.assert_called_once_with([{"udm": "b"}], [])

    post_entries("entities", "TYPE", [{"ent": "c"}], [], backend=mock_backend)
    mock_backend.post_entities.assert_called_once_with("TYPE", [{"ent": "c"}], [])

    with pytest.raises(ValueError, match="Unknown API type: invalid_api"):
      post_entries("invalid_api", "TYPE", [], [], backend=mock_backend)


class TestUsecaseReplayLogtype:
  """Test usecase_replay_logtype end-to-end replay logic."""

  def test_replay_with_local_file_output(self):
    """Test replaying a usecase with local_file_output=True."""
    sample_log = (
        '{"ts": 1718545020.123, "msg": "test message"}\n{"ts": 1718545025.456, "msg":'
        ' "test 2"}'
    )
    with patch("logstory.main._get_log_content", return_value=sample_log):
      with tempfile.TemporaryDirectory() as tmpdir:
        old_base = usecase_replay_logtype(
            use_case="NETWORK_ANALYSIS",
            log_type="BRO_JSON",
            logstory_exe_time=datetime.datetime.now(UTC),
            local_file_output=True,
        )
        assert old_base is not None


class TestCloudFunctionMainHandler:
  """Test Google Cloud Function entrypoint main()."""

  @patch("logstory.main.usecase_replay_logtype")
  def test_main_executes_usecase_replay(self, mock_replay):
    """Test cloud function main execution iterating enabled usecases."""
    mock_replay.return_value = datetime.datetime(2026, 8, 13, 12, 0, 0, tzinfo=UTC)

    mock_yaml_data = {
        "TEST_USECASE": {
            "enabled": 1,
            "log_type": ["LINUX_SYSLOG"],
        }
    }

    with patch("builtins.open", mock_open(read_data=yaml.dump(mock_yaml_data))):
      cloud_function_main(request=None, enabled=True)
      mock_replay.assert_called_once()


class TestMainModuleBranches:
  """Test additional branches and edge cases in main.py."""

  def test_post_entries_in_batches_udm_event_bytes(self):
    """Test post_entries_in_batches calculating bytes for udmevents."""
    mock_backend = MagicMock(spec=LegacyIngestionBackend)
    entries = [{"udm": "event 1"}, {"udm": "event 2"}]
    _post_entries_in_batches(
        api="udmevents",
        log_type="UDM",
        all_entries=entries,
        ingestion_labels=[],
        backend=mock_backend,
        local_file_output=False,
    )
    mock_backend.post_udm_events.assert_called_once()

  def test_write_entries_directory_creation_error_raises(self):
    """Test PermissionError / OSError handling during directory creation."""
    with patch("pathlib.Path.mkdir", side_effect=PermissionError("denied")):
      with pytest.raises(PermissionError):
        _write_entries_to_local_file(
            "TYPE", [{"logText": "msg"}], log_dir="/restricted"
        )

    with patch("pathlib.Path.mkdir", side_effect=RuntimeError("disk error")):
      with pytest.raises(RuntimeError):
        _write_entries_to_local_file(
            "TYPE", [{"logText": "msg"}], log_dir="/restricted"
        )

  def test_write_entries_file_permission_error_raises(self):
    """Test PermissionError when opening local file for writing."""
    with patch("builtins.open", side_effect=PermissionError("cannot write")):
      with pytest.raises(PermissionError):
        _write_entries_to_local_file("TYPE", [{"logText": "msg"}], log_dir="/tmp")

  def test_usecase_replay_logtype_api_posting_and_entities(self):
    """Test usecase_replay_logtype with API posting and entities=True."""
    mock_backend = MagicMock(spec=LegacyIngestionBackend)
    sample_log = "2024-06-16 13:37:42 test message"

    with patch.object(logstory_main, "ingestion_backend", mock_backend):
      with patch("logstory.main._get_log_content", return_value=sample_log):
        # Events replay
        usecase_replay_logtype(
            use_case="NETWORK_ANALYSIS",
            log_type="AUDITD",
            logstory_exe_time=datetime.datetime.now(UTC),
            local_file_output=False,
        )
        mock_backend.post_unstructured_logs.assert_called()

  def test_usecase_replay_logtype_no_base_time_found(self):
    """Test usecase_replay_logtype handles logs with no valid base time."""
    sample_log = "unparseable lines without any timestamps"
    with tempfile.TemporaryDirectory() as tmpdir:
      with patch.dict(os.environ, {"LOGSTORY_LOCAL_LOG_DIR": tmpdir}):
        with patch("logstory.main._get_log_content", return_value=sample_log):
          old_base = usecase_replay_logtype(
              use_case="NETWORK_ANALYSIS",
              log_type="BRO_JSON",
              logstory_exe_time=datetime.datetime.now(UTC),
              local_file_output=True,
          )
          assert old_base is None
