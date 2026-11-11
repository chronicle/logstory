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

"""Unit tests for native WIZ_IO timestamp configuration and log replay shifting."""

import datetime
import json
from datetime import UTC
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from logstory import main as logstory_main
from logstory.ingestion import LegacyIngestionBackend
from logstory.main import (
    _calculate_timestamp_replacement,
    _validate_timestamp_config,
    usecase_replay_logtype,
)
from tests.test_yaml import _validate_single_log_type

EVENTS_YAML_PATH = (
    Path(__file__).parent.parent / "src/logstory/logtypes_events_timestamps.yaml"
)

FIXED_NOW = datetime.datetime(2026, 11, 11, 16, 0, 0, tzinfo=UTC)
BASE_DATE = "2025-08-04"
SHIFTED_DATE = "2026-11-10"

EXPECTED_PATTERN_NAMES = [
    "wiz_timestamp",
    "wiz_created",
    "wiz_createdAt",
    "wiz_updatedAt",
    "wiz_updated",
    "wiz_statusChangedAt",
    "wiz_resolvedAt",
    "wiz_dueAt",
    "wiz_start",
    "wiz_end",
    "wiz_eventTime",
    "wiz_executionTime_0",
    "wiz_executionTime_1",
    "wiz_executionTime_2",
]


def _load_events_timestamp_map() -> dict:
  with open(EVENTS_YAML_PATH, encoding="utf-8") as fh:
    return yaml.safe_load(fh)


def _build_wiz_issue_payload() -> str:
  """Build a Wiz ISSUE (TOXIC_COMBINATION) payload covering all issue timestamps."""
  payload = {
      "timestamp": f"{BASE_DATE}T13:45:10.600000Z",
      "trigger": {
          "source": "ISSUE",
          "type": "Updated",
          "ruleId": "a1b2c3d4-1111-4321-abcd-000000000001",
          "ruleName": "Wiz Issues and Toxic Combinations to Google SecOps",
          "changedBy": "Wiz",
      },
      "metadata": {"version": "1.0.0"},
      "createdAt": f"{BASE_DATE}T13:40:00.120000Z",
      "updatedAt": f"{BASE_DATE}T13:45:10.600000Z",
      "statusChangedAt": f"{BASE_DATE}T13:44:55.250000Z",
      "resolvedAt": f"{BASE_DATE}T13:45:09.900000Z",
      "dueAt": f"{BASE_DATE}T23:59:59.000000Z",
      "issue": {
          "id": "a1b2c3d4-1112-4321-abcd-000000000002",
          "type": "TOXIC_COMBINATION",
          "issueURL": (
              "https://app.wiz.io/issues#~(issue~'a1b2c3d4-1112-4321-abcd-000000000002)"
          ),
          "status": "RESOLVED",
          "severity": "CRITICAL",
          "created": f"{BASE_DATE}T13:40:00.120000Z",
          "updated": f"{BASE_DATE}T13:45:10.600000Z",
          "projects": "cymbal-investments-prod",
      },
      "resource": {
          "id": (
              "projects/cymbal-investments-prod/zones/us-central1-a/"
              "instances/gce-payments-api-01"
          ),
          "name": "gce-payments-api-01",
          "type": "VIRTUAL_MACHINE",
          "cloudPlatform": "GCP",
          "subscriptionId": "cymbal-investments-prod",
          "region": "us-central1",
          "status": "Active",
      },
      "control": {
          "id": "wc-id-1397",
          "name": "Publicly exposed VM with initial access vulnerabilities",
          "severity": "CRITICAL",
          "risks": ["EXTERNAL_EXPOSURE", "VULNERABILITY"],
      },
  }
  return json.dumps(payload, separators=(",", ":"))


def _build_wiz_detection_payload() -> str:
  """Build a Wiz DETECTIONS (eBPF WIZ_SENSOR) payload with a 3-node processTree."""
  payload = {
      "timestamp": f"{BASE_DATE}T14:02:54.420000Z",
      "trigger": {
          "source": "DETECTIONS",
          "type": "Created",
          "ruleId": "a1b2c3d4-2221-4321-abcd-000000000011",
          "ruleName": "Wiz Defend Runtime and CDR Detections to Google SecOps",
      },
      "metadata": {"version": "1.0.0"},
      "detection": {
          "id": "a1b2c3d4-2222-4321-abcd-000000000012",
          "threatId": "a1b2c3d4-2223-4321-abcd-000000000013",
          "title": "Reverse shell spawned from Gunicorn web worker process",
          "severity": "HIGH",
          "createdAt": f"{BASE_DATE}T14:02:54.420000Z",
          "tdrId": "cer-sen-id-595",
          "tdrSource": "WIZ_SENSOR",
          "timeframe": {
              "start": f"{BASE_DATE}T14:02:49.180Z",
              "end": f"{BASE_DATE}T14:02:53.910Z",
          },
          "triggeringEventsCount": 1,
          "triggeringEvents": [{
              "id": "a1b2c3d4-2224-4321-abcd-000000000014",
              "category": "Detection",
              "cloudPlatform": "GCP",
              "eventTime": f"{BASE_DATE}T14:02:49.180Z",
              "name": "Reverse shell spawned from Gunicorn web worker process",
              "origin": "WIZ_SENSOR",
              "runtimeDetails": {
                  "processTree": [
                      {
                          "command": "/usr/bin/dash -i",
                          "currentWorkingDirectory": "/srv/payments-api",
                          "executionTime": f"{BASE_DATE}T14:02:49.180Z",
                          "id": "18422",
                          "path": "/usr/bin/dash",
                          "userId": "33",
                          "username": "www-data",
                      },
                      {
                          "command": "/srv/payments-api/venv/bin/gunicorn wsgi:app",
                          "currentWorkingDirectory": "/srv/payments-api",
                          "executionTime": f"{BASE_DATE}T06:15:10.100Z",
                          "id": "2140",
                          "path": "/srv/payments-api/venv/bin/python3",
                          "userId": "33",
                          "username": "www-data",
                      },
                      {
                          "command": "/usr/lib/systemd/systemd --system",
                          "currentWorkingDirectory": "/",
                          "executionTime": f"{BASE_DATE}T06:14:55.050Z",
                          "id": "1",
                          "path": "/usr/lib/systemd/systemd",
                          "userId": "0",
                          "username": "root",
                      },
                  ]
              },
              "source": "WizSensorAlert##RuleEngine",
              "status": "Success",
          }],
      },
  }
  return json.dumps(payload, separators=(",", ":"))


def _build_wiz_threat_payload() -> str:
  """Build a Wiz THREATS payload with nested threat lifecycle timestamps."""
  payload = {
      "timestamp": f"{BASE_DATE}T14:15:30.527330111Z",
      "trigger": {
          "source": "THREATS",
          "type": "Updated",
          "ruleId": "a1b2c3d4-3331-4321-abcd-000000000021",
          "ruleName": "Wiz Threats to Google SecOps",
          "changedBy": "Wiz",
      },
      "threat": {
          "id": "a1b2c3d4-3332-4321-abcd-000000000022",
          "title": "Compromised workload impersonating privileged service account",
          "status": "RESOLVED",
          "severity": "CRITICAL",
          "created": f"{BASE_DATE}T14:02:55.100000Z",
          "updatedAt": f"{BASE_DATE}T14:15:30.527330111Z",
          "resolvedAt": f"{BASE_DATE}T14:15:29.000000Z",
          "cloudPlatform": "GCP",
          "detectionIds": "a1b2c3d4-2222-4321-abcd-000000000012",
          "mitreTactics": ["TA0002", "TA0004"],
          "mitreTechniques": ["TA0002-T1059.004", "TA0004-T1078.004"],
      },
  }
  return json.dumps(payload, separators=(",", ":"))


def _build_wiz_audit_login_payload() -> str:
  """Build a Wiz Audit (Login) payload."""
  payload = {
      "id": "a1b2c3d4-4441-4321-abcd-000000000031",
      "action": "Login",
      "requestId": "a1b2c3d4-4442-4321-abcd-000000000032",
      "status": "SUCCESS",
      "timestamp": f"{BASE_DATE}T15:05:01.166091Z",
      "actionParameters": {
          "clientID": "wiz-secops-connector-client",
          "name": "SecOps_Connector_SA",
          "scopes": ["read:issues", "read:detections", "admin:audit"],
      },
      "userAgent": "Google-SecOps-Wiz-Connector/1.0",
      "sourceIP": "198.51.100.24",
      "serviceAccount": {
          "id": "a1b2c3d4-4443-4321-abcd-000000000033",
          "name": "SecOps_Connector_SA",
      },
      "user": None,
  }
  return json.dumps(payload, separators=(",", ":"))


class TestWizIoTimestampConfig:
  """Validate WIZ_IO configuration in logtypes_events_timestamps.yaml."""

  def test_wiz_io_exists_with_expected_schema(self):
    timestamp_map = _load_events_timestamp_map()
    assert "WIZ_IO" in timestamp_map

    wiz_config = timestamp_map["WIZ_IO"]
    assert wiz_config["api"] == "unstructuredlogentries"
    assert wiz_config["log_dir"] == "/tmp/var/log/logstory"

    timestamps = wiz_config["timestamps"]
    assert [ts["name"] for ts in timestamps] == EXPECTED_PATTERN_NAMES

    base_time_entries = [ts for ts in timestamps if ts.get("base_time")]
    assert len(base_time_entries) == 1
    assert base_time_entries[0]["name"] == "wiz_timestamp"
    assert base_time_entries[0]["dateformat"] == "%Y-%m-%dT%H:%M:%S"
    assert base_time_entries[0]["group"] == 2

  def test_wiz_io_passes_yaml_and_runtime_validators(self):
    timestamp_map = _load_events_timestamp_map()
    _validate_single_log_type("WIZ_IO", timestamp_map["WIZ_IO"])
    _validate_timestamp_config("WIZ_IO", timestamp_map)


class TestWizIoTimestampReplay:
  """Verify end-to-end Logstory replay shifts all WIZ_IO timestamp fields."""

  def _replay_wiz_lines(
      self, lines: list[str], timestamp_delta: str = "1d"
  ) -> list[dict]:
    sample_content = "\n".join(lines)
    mock_backend = MagicMock(spec=LegacyIngestionBackend)

    with (
        patch.object(logstory_main, "ingestion_backend", mock_backend),
        patch("logstory.main._get_log_content", return_value=sample_content),
        patch("logstory.main._get_current_time", return_value=FIXED_NOW),
    ):
      old_base_time = usecase_replay_logtype(
          use_case="WIZ_GCP_CLOUD_INTRUSION",
          log_type="WIZ_IO",
          logstory_exe_time=FIXED_NOW,
          timestamp_delta=timestamp_delta,
          local_file_output=False,
      )

    assert old_base_time is not None
    mock_backend.post_unstructured_logs.assert_called_once()
    call_args = mock_backend.post_unstructured_logs.call_args[0]
    assert call_args[0] == "WIZ_IO"
    entries = call_args[1]
    assert len(entries) == len(lines)

    parsed = []
    for entry in entries:
      raw_text = entry["logText"]
      assert BASE_DATE not in raw_text, f"Unshifted base date in: {raw_text}"
      parsed.append(json.loads(raw_text))
    return parsed

  def test_shifts_all_four_wiz_payload_families_with_zero_stale_dates(self):
    raw_lines = [
        _build_wiz_issue_payload(),
        _build_wiz_detection_payload(),
        _build_wiz_threat_payload(),
        _build_wiz_audit_login_payload(),
    ]

    replayed = self._replay_wiz_lines(raw_lines, timestamp_delta="1d")
    issue_ev, det_ev, threat_ev, audit_ev = replayed

    # 1. Wiz ISSUE (TOXIC_COMBINATION + GraphQL/Webhook lifecycle timestamps)
    assert issue_ev["timestamp"] == f"{SHIFTED_DATE}T13:45:10.600000Z"
    assert issue_ev["createdAt"] == f"{SHIFTED_DATE}T13:40:00.120000Z"
    assert issue_ev["updatedAt"] == f"{SHIFTED_DATE}T13:45:10.600000Z"
    assert issue_ev["statusChangedAt"] == f"{SHIFTED_DATE}T13:44:55.250000Z"
    assert issue_ev["resolvedAt"] == f"{SHIFTED_DATE}T13:45:09.900000Z"
    assert issue_ev["dueAt"] == f"{SHIFTED_DATE}T23:59:59.000000Z"
    assert issue_ev["issue"]["created"] == f"{SHIFTED_DATE}T13:40:00.120000Z"
    assert issue_ev["issue"]["updated"] == f"{SHIFTED_DATE}T13:45:10.600000Z"

    # 2. Wiz DETECTIONS (eBPF WIZ_SENSOR with timeframe, eventTime, processTree[0..2])
    assert det_ev["timestamp"] == f"{SHIFTED_DATE}T14:02:54.420000Z"
    det = det_ev["detection"]
    assert det["createdAt"] == f"{SHIFTED_DATE}T14:02:54.420000Z"
    assert det["timeframe"]["start"] == f"{SHIFTED_DATE}T14:02:49.180Z"
    assert det["timeframe"]["end"] == f"{SHIFTED_DATE}T14:02:53.910Z"
    trig = det["triggeringEvents"][0]
    assert trig["eventTime"] == f"{SHIFTED_DATE}T14:02:49.180Z"
    proc_tree = trig["runtimeDetails"]["processTree"]
    assert proc_tree[0]["executionTime"] == f"{SHIFTED_DATE}T14:02:49.180Z"
    assert proc_tree[1]["executionTime"] == f"{SHIFTED_DATE}T06:15:10.100Z"
    assert proc_tree[2]["executionTime"] == f"{SHIFTED_DATE}T06:14:55.050Z"

    # 3. Wiz THREATS (nested created, updatedAt, resolvedAt + nanosecond precision)
    assert threat_ev["timestamp"] == f"{SHIFTED_DATE}T14:15:30.527330111Z"
    assert threat_ev["threat"]["created"] == f"{SHIFTED_DATE}T14:02:55.100000Z"
    assert threat_ev["threat"]["updatedAt"] == f"{SHIFTED_DATE}T14:15:30.527330111Z"
    assert threat_ev["threat"]["resolvedAt"] == f"{SHIFTED_DATE}T14:15:29.000000Z"

    # 4. Wiz Audit (Login)
    assert audit_ev["action"] == "Login"
    assert audit_ev["timestamp"] == f"{SHIFTED_DATE}T15:05:01.166091Z"

  def test_preserves_multi_day_relative_offsets_and_null_fields(self):
    pretty_json_line = json.dumps({
        "timestamp": "2025-08-04T14:00:00Z",
        "trigger": {
            "source": "DETECTIONS",
            "type": "Created",
            "ruleId": "a1b2c3d4-5551-4321-abcd-000000000041",
        },
        "dueAt": "2025-08-18T14:00:00Z",
        "resolvedAt": None,
        "statusChangedAt": "",
        "detection": {
            "id": "a1b2c3d4-5552-4321-abcd-000000000042",
            "createdAt": "2025-08-04T14:00:00Z",
            "timeframe": {
                "start": "2025-08-04T13:58:00Z",
                "end": "2025-08-04T13:59:30Z",
            },
            "triggeringEvents": [{
                "id": "a1b2c3d4-5553-4321-abcd-000000000043",
                "eventTime": "2025-08-04T13:59:30Z",
                "runtimeDetails": {
                    "processTree": [
                        {"id": "300", "executionTime": "2025-08-04T13:59:30.500Z"},
                        {"id": "200", "executionTime": "2025-08-03T22:10:00.250Z"},
                        {"id": "1", "executionTime": "2025-08-02T08:00:00.000Z"},
                    ]
                },
            }],
        },
    })

    replayed = self._replay_wiz_lines([pretty_json_line], timestamp_delta="1d")[0]

    assert replayed["timestamp"] == "2026-11-10T14:00:00Z"
    # +14 days relative to 2025-08-04 -> 2026-11-24
    assert replayed["dueAt"] == "2026-11-24T14:00:00Z"
    assert replayed["resolvedAt"] is None
    assert replayed["statusChangedAt"] == ""

    proc_tree = replayed["detection"]["triggeringEvents"][0]["runtimeDetails"][
        "processTree"
    ]
    assert proc_tree[0]["executionTime"] == "2026-11-10T13:59:30.500Z"
    # -1 day relative to 2025-08-04 -> 2026-11-09
    assert proc_tree[1]["executionTime"] == "2026-11-09T22:10:00.250Z"
    # -2 days relative to 2025-08-04 -> 2026-11-08
    assert proc_tree[2]["executionTime"] == "2026-11-08T08:00:00.000Z"

  def test_execution_time_positional_patterns_target_distinct_spans(self):
    timestamp_map = _load_events_timestamp_map()
    exec_patterns = [
        ts
        for ts in timestamp_map["WIZ_IO"]["timestamps"]
        if ts["name"].startswith("wiz_executionTime_")
    ]
    assert len(exec_patterns) == 3

    det_line = _build_wiz_detection_payload()
    old_base_time = datetime.datetime(2025, 8, 4, 14, 2, 54)

    spans = []
    with patch("logstory.main._get_current_time", return_value=FIXED_NOW):
      for ts_cfg in exec_patterns:
        replacement = _calculate_timestamp_replacement(
            det_line, ts_cfg, old_base_time, {"d": 1}
        )
        assert replacement is not None, f"{ts_cfg['name']} failed to match"
        match_obj, new_ts = replacement
        spans.append((match_obj.start(), match_obj.end(), new_ts))

    # Ensure all 3 processTree executionTime spans are distinct and ordered
    assert len({(s, e) for s, e, _ in spans}) == 3
    assert spans[0][0] < spans[1][0] < spans[2][0]
    assert [s[2] for s in spans] == [
        f"{SHIFTED_DATE}T14:02:49",
        f"{SHIFTED_DATE}T06:15:10",
        f"{SHIFTED_DATE}T06:14:55",
    ]
