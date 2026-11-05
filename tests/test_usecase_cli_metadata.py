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

"""CLI tests for usecases validate, inspect, export-schemas, and paired baselines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from logstory.logstory import _get_paired_baselines, app

runner = CliRunner()


def _valid_manifest_dict(
    usecase_id: str = "DNS_TUNNELING_EXFIL_GTI",
    paired_baselines: list[str] | None = None,
) -> dict[str, Any]:
  """Return a valid v2 SecurityUsecaseManifest dictionary."""
  return {
      "schema_version": "2.0",
      "id": usecase_id,
      "title": f"{usecase_id} Telemetry Package",
      "version": "2.0.0",
      "created": "2026-10-18",
      "updated": "2026-11-05",
      "author": "Google Cloud Security",
      "license": "Apache-2.0",
      "description": (
          "Enterprise DNS and directory telemetry package for network protocol"
          " analysis."
      ),
      "tags": ["network-c2", "dns", "ocsf", "google-secops"],
      "environment": {
          "organization": "cymbal-investments.org",
          "scenario_type": "attack",
          "paired_baselines": (
              paired_baselines
              if paired_baselines is not None
              else ["CYMBAL_BASELINE_NETWORK"]
          ),
          "timestamp_policy": {
              "base_date": "2026-10-18",
              "preserve_relative_offsets": True,
              "default_delta": "1d",
              "entity_offset_days": 1,
          },
      },
      "telemetry": {
          "events": [{
              "stream_id": "zeek_dns",
              "path": "EVENTS/BRO_JSON.log",
              "log_type": "BRO_JSON",
              "vendor_name": "Zeek",
              "product_name": "Bro",
              "ocsf_category_uid": 4,
              "ocsf_class_uid": 4003,
              "ocsf_class_name": "DNS Activity",
          }],
          "entities": [{
              "stream_id": "windows_ad_users",
              "path": "ENTITIES/WINDOWS_AD.log",
              "log_type": "WINDOWS_AD",
              "vendor_name": "Microsoft",
              "product_name": "Active Directory",
              "ocsf_category_uid": 5,
              "ocsf_class_uid": 5003,
              "ocsf_class_name": "User Inventory",
          }],
      },
      "platforms": {
          "google_secops": {
              "run_frequency": {
                  "events": "Every 1 day",
                  "entities": "Every 1 day (offset 1 day prior)",
              },
              "data_rbac": "Standard RBAC",
              "log_type_mappings": {
                  "zeek_dns": "BRO_JSON",
                  "windows_ad_users": "WINDOWS_AD",
              },
              "detections": [{
                  "name": "dns_tunneling_low_reputation_domain",
                  "path": "RULES/dns_tunneling_low_reputation_domain.yl2",
                  "live": True,
                  "alerting": True,
              }],
          },
      },
  }


def _valid_eval_dict(
    usecase_id: str = "DNS_TUNNELING_EXFIL_GTI",
    paired_baseline_id: str | None = "CYMBAL_BASELINE_NETWORK",
) -> dict[str, Any]:
  """Return a valid v2 SecurityUsecaseEval dictionary."""
  eval_dict: dict[str, Any] = {
      "schema_version": "2.0",
      "usecase_id": usecase_id,
      "threat_context": {
          "grounding_tier": "stix_grounded",
          "difficulty_tier": "advanced",
          "threat_actor": "UNC-STRATIO",
          "actor_aliases": ["StratioGroup"],
          "campaign_name": "Operation HexSubdomain",
          "cisa_advisories": ["AA24-242A"],
          "cve_ids": ["CVE-2024-12345"],
          "mitre_tactics": ["TA0011", "TA0010"],
          "mitre_techniques": ["T1071.004", "T1048.003"],
      },
      "tasks": {
          "alert_triage": {
              "enabled": True,
              "case_id": "CASE-4012",
              "alert_ids": ["de_4cfa127e-8a09-3f1b-05b8-588dbfaf257b"],
              "prompt": "Triage CASE-4012 and determine disposition.",
              "expected_skill": "dns-tunneling-network-beacon-hunt",
              "time_horizon_hours": 72,
          },
          "threat_hunt": {
              "enabled": True,
              "prompt_unalerted": "Hunt across zeek_dns and windows_ad_users.",
              "expected_patient_zero": "fin-wks-20",
              "time_horizon_hours": 168,
          },
          "detection_engineering": {
              "enabled": True,
              "prompt": "Author a detection rule for DNS tunneling.",
              "target_techniques": ["T1071.004"],
              "reference_rules": ["RULES/dns_tunneling_low_reputation_domain.yl2"],
              "expected_rule_count_min": 1,
              "max_false_positives_on_paired_baseline": 0,
          },
      },
      "ground_truth": {
          "expected_disposition": "TRUE_POSITIVE",
          "expected_verdict": "MALICIOUS",
          "severity": "HIGH",
          "patient_zero_host": "fin-wks-20",
          "patient_zero_account": "alice.smith",
          "root_cause_summary": "DNS tunneling exfiltration to stratioai.org.",
          "kill_chain": [{
              "stage": "exfiltration",
              "stream_id": "zeek_dns",
              "timestamp_utc": "2026-10-18T11:20:00Z",
              "tactic": "TA0010",
              "technique_id": "T1048.003",
              "summary": "Hex-encoded subdomain DNS queries to C2 domain.",
          }],
          "entities_and_iocs": {
              "compromised_accounts": ["alice.smith"],
              "affected_assets": [{
                  "hostname": "fin-wks-20",
                  "criticality_tier": "tier_2_workstation",
                  "ip_addresses": ["10.128.0.20"],
                  "patient_zero": True,
                  "blast_radius_fp_usd": 500.0,
                  "blast_radius_fn_usd": 50000.0,
              }],
              "malicious_iocs": [{
                  "type": "domain",
                  "value": "stratioai.org",
                  "role": "c2_domain",
              }],
          },
      },
      "compliance_gates": {
          "requires_pre_containment_verification": True,
          "requires_168h_horizon_widening": False,
          "forbid_external_cti_on_internal_ips": True,
          "forbid_lolbin_hash_blocking": True,
      },
  }
  if paired_baseline_id is not None:
    eval_dict["counterfactual_pair"] = {
        "paired_usecase_id": paired_baseline_id,
        "pair_relationship": "malicious_variant_of_benign_baseline",
        "shared_entities": ["fin-wks-20", "alice.smith"],
        "shared_telemetry_streams": ["zeek_dns"],
        "discriminating_invariant": "Subdomain labels exceed 40 hex chars.",
    }
  return eval_dict


def _write_usecase_fixture(
    root_dir: Path,
    usecase_name: str = "DNS_TUNNELING_EXFIL_GTI",
    manifest: dict[str, Any] | None = None,
    eval_data: dict[str, Any] | None = None,
    public_body: str = "# DNS_TUNNELING_EXFIL_GTI\n\nBlind-safe public overview.",
    solution_body: str | None = (
        "## Analyst Solution\n\n"
        "Compromised account alice.smith exfiltrated data to stratioai.org "
        "matching advisory AA24-242A."
    ),
    create_files: bool = True,
) -> Path:
  """Materialize a usecase directory fixture on disk for CLI tests."""
  usecase_dir = root_dir / usecase_name
  usecase_dir.mkdir(parents=True, exist_ok=True)

  manifest_dict = (
      manifest if manifest is not None else _valid_manifest_dict(usecase_name)
  )
  frontmatter_yaml = yaml.safe_dump(manifest_dict, sort_keys=False)
  if solution_body is not None:
    md_text = (
        f"---\n{frontmatter_yaml}---\n\n{public_body}\n\n"
        f"<!-- BEGIN_SOLUTION -->\n\n{solution_body}\n"
    )
  else:
    md_text = f"---\n{frontmatter_yaml}---\n\n{public_body}\n"

  (usecase_dir / f"{usecase_name}.md").write_text(md_text, encoding="utf-8")

  eval_dict = eval_data if eval_data is not None else _valid_eval_dict(usecase_name)
  (usecase_dir / "eval.yaml").write_text(
      yaml.safe_dump(eval_dict, sort_keys=False), encoding="utf-8"
  )

  if create_files:
    events_dir = usecase_dir / "EVENTS"
    entities_dir = usecase_dir / "ENTITIES"
    rules_dir = usecase_dir / "RULES"
    events_dir.mkdir(parents=True, exist_ok=True)
    entities_dir.mkdir(parents=True, exist_ok=True)
    rules_dir.mkdir(parents=True, exist_ok=True)
    (events_dir / "BRO_JSON.log").write_text('{"ts": "2026-10-18"}\n', encoding="utf-8")
    (entities_dir / "WINDOWS_AD.log").write_text(
        '{"user": "alice"}\n', encoding="utf-8"
    )
    (rules_dir / "dns_tunneling_low_reputation_domain.yl2").write_text(
        "rule dns_tunneling_low_reputation_domain {}\n", encoding="utf-8"
    )

  return usecase_dir


class TestUsecasesValidateCli:
  """Tests for `logstory usecases validate` subcommand."""

  def test_validate_single_usecase_dir_json_and_text(self, tmp_path: Path):
    usecase_dir = _write_usecase_fixture(tmp_path)

    res_json = runner.invoke(
        app,
        ["usecases", "validate", str(usecase_dir), "--strict-v2", "--format", "json"],
    )
    assert res_json.exit_code == 0, res_json.stdout
    payload = json.loads(res_json.stdout)
    assert payload["valid"] is True
    assert payload["total"] == 1
    assert payload["passed"] == 1
    assert payload["failed"] == 0
    assert payload["results"][0]["usecase_id"] == "DNS_TUNNELING_EXFIL_GTI"
    assert payload["results"][0]["is_valid"] is True

    res_text = runner.invoke(
        app,
        ["usecases", "validate", str(usecase_dir), "--strict-v2", "--format", "text"],
    )
    assert res_text.exit_code == 0, res_text.stdout
    assert "DNS_TUNNELING_EXFIL_GTI" in res_text.stdout
    assert "PASS" in res_text.stdout

  def test_validate_corpus_directory_success_and_failure(self, tmp_path: Path):
    _write_usecase_fixture(
        tmp_path,
        usecase_name="CYMBAL_BASELINE_NETWORK",
        manifest=_valid_manifest_dict("CYMBAL_BASELINE_NETWORK", paired_baselines=[]),
        eval_data=_valid_eval_dict("CYMBAL_BASELINE_NETWORK", paired_baseline_id=None),
    )
    _write_usecase_fixture(
        tmp_path,
        usecase_name="DNS_TUNNELING_EXFIL_GTI",
    )

    res = runner.invoke(
        app,
        ["usecases", "validate", str(tmp_path), "--strict-v2", "--format", "json"],
    )
    assert res.exit_code == 0, res.stdout
    payload = json.loads(res.stdout)
    assert payload["valid"] is True
    assert payload["total"] == 2
    assert payload["passed"] == 2

    # Introduce spoiler leakage into public markdown body to fail Gate 3
    bad_dir = _write_usecase_fixture(
        tmp_path,
        usecase_name="SPOILER_USECASE",
        manifest=_valid_manifest_dict("SPOILER_USECASE", paired_baselines=[]),
        eval_data=_valid_eval_dict("SPOILER_USECASE", paired_baseline_id=None),
        public_body="Public text leaking stratioai.org before delimiter.",
    )
    assert bad_dir.is_dir()

    res_fail = runner.invoke(
        app,
        ["usecases", "validate", str(tmp_path), "--strict-v2", "--format", "json"],
    )
    assert res_fail.exit_code == 1
    fail_payload = json.loads(res_fail.stdout)
    assert fail_payload["valid"] is False
    assert fail_payload["failed"] == 1

    res_fail_text = runner.invoke(
        app,
        ["usecases", "validate", str(tmp_path), "--strict-v2", "--format", "text"],
    )
    assert res_fail_text.exit_code == 1
    assert "FAIL" in res_fail_text.stdout
    assert "G3_ANTI_SPOILER" in res_fail_text.stdout

  def test_validate_installed_usecases_and_missing_target(self):
    res_all = runner.invoke(
        app, ["usecases", "validate", "--strict-v2", "--format", "json"]
    )
    assert res_all.exit_code == 0, res_all.stdout
    payload = json.loads(res_all.stdout)
    assert payload["valid"] is True
    assert payload["total"] >= 2

    res_named = runner.invoke(
        app,
        ["usecases", "validate", "NETWORK_ANALYSIS", "--strict-v2", "--format", "json"],
    )
    assert res_named.exit_code == 0, res_named.stdout
    named_payload = json.loads(res_named.stdout)
    assert named_payload["results"][0]["usecase_id"] == "NETWORK_ANALYSIS"

    res_missing = runner.invoke(
        app, ["usecases", "validate", "NONEXISTENT_USECASE_XYZ"]
    )
    assert res_missing.exit_code == 1


class TestUsecasesInspectCli:
  """Tests for `logstory usecases inspect` subcommand."""

  def test_inspect_blind_strips_solution_and_eval(self, tmp_path: Path):
    usecase_dir = _write_usecase_fixture(tmp_path)

    res_blind = runner.invoke(
        app,
        ["usecases", "inspect", str(usecase_dir), "--blind", "--format", "json"],
    )
    assert res_blind.exit_code == 0, res_blind.stdout
    blind_data = json.loads(res_blind.stdout)
    assert blind_data["manifest"]["id"] == "DNS_TUNNELING_EXFIL_GTI"
    assert "Blind-safe public overview." in blind_data["public_markdown_body"]
    assert "stratioai.org" not in res_blind.stdout
    assert "alice.smith" not in res_blind.stdout
    assert "AA24-242A" not in res_blind.stdout
    assert blind_data["solution_markdown_body"] is None
    assert blind_data["eval_data"] is None

    res_blind_text = runner.invoke(
        app,
        ["usecases", "inspect", str(usecase_dir), "--blind", "--format", "text"],
    )
    assert res_blind_text.exit_code == 0, res_blind_text.stdout
    assert "DNS_TUNNELING_EXFIL_GTI" in res_blind_text.stdout
    assert "stratioai.org" not in res_blind_text.stdout

  def test_inspect_include_eval_returns_eval_and_solution(self, tmp_path: Path):
    usecase_dir = _write_usecase_fixture(tmp_path)

    res_full = runner.invoke(
        app,
        ["usecases", "inspect", str(usecase_dir), "--include-eval", "--format", "json"],
    )
    assert res_full.exit_code == 0, res_full.stdout
    full_data = json.loads(res_full.stdout)
    assert full_data["eval_data"] is not None
    assert full_data["eval_data"]["usecase_id"] == "DNS_TUNNELING_EXFIL_GTI"
    assert full_data["solution_markdown_body"] is not None
    assert "stratioai.org" in full_data["solution_markdown_body"]

    res_full_text = runner.invoke(
        app,
        ["usecases", "inspect", str(usecase_dir), "--include-eval", "--format", "text"],
    )
    assert res_full_text.exit_code == 0, res_full_text.stdout
    assert "TRUE_POSITIVE" in res_full_text.stdout

  def test_inspect_installed_usecase_and_missing(self):
    res_installed = runner.invoke(
        app, ["usecases", "inspect", "NETWORK_ANALYSIS", "--blind", "--format", "json"]
    )
    assert res_installed.exit_code == 0, res_installed.stdout
    data = json.loads(res_installed.stdout)
    assert data["manifest"]["id"] == "NETWORK_ANALYSIS"
    assert data["eval_data"] is None

    res_missing = runner.invoke(app, ["usecases", "inspect", "NONEXISTENT_USECASE_XYZ"])
    assert res_missing.exit_code == 1


class TestUsecasesExportSchemasCli:
  """Tests for `logstory usecases export-schemas` subcommand."""

  def test_export_schemas_writes_json_schema_files(self, tmp_path: Path):
    out_dir = tmp_path / "exported_schemas"
    res = runner.invoke(
        app, ["usecases", "export-schemas", "--output-dir", str(out_dir)]
    )
    assert res.exit_code == 0, res.stdout
    usecase_schema = out_dir / "usecase.schema.json"
    eval_schema = out_dir / "eval.schema.json"
    assert usecase_schema.is_file()
    assert eval_schema.is_file()

    uc_json = json.loads(usecase_schema.read_text(encoding="utf-8"))
    ev_json = json.loads(eval_schema.read_text(encoding="utf-8"))
    assert uc_json["title"] == "SecurityUsecaseManifest"
    assert ev_json["title"] == "SecurityUsecaseEval"


class TestReplayWithPairedBaselines:
  """Tests for `logstory replay usecase --with-paired-baselines`."""

  def test_replay_usecase_with_paired_baselines_deduplicates_and_replays_first(
      self, tmp_path: Path
  ):
    manifest = _valid_manifest_dict(
        "ATTACK_UC",
        paired_baselines=[
            "CYMBAL_BASELINE_NETWORK",
            "CYMBAL_BASELINE_ENDPOINT",
            "CYMBAL_BASELINE_NETWORK",
        ],
    )
    _write_usecase_fixture(
        tmp_path,
        usecase_name="ATTACK_UC",
        manifest=manifest,
        eval_data=_valid_eval_dict("ATTACK_UC"),
    )

    replayed_calls: list[tuple[str, str, bool]] = []

    def fake_replay_logtype(
        use_case,
        log_type,
        _logstory_exe_time,
        old_base_time,
        timestamp_delta=None,
        entities=False,
        local_file_output=False,
    ):
      del timestamp_delta, local_file_output
      replayed_calls.append((use_case, log_type, entities))
      return old_base_time

    def fake_get_logtypes(_usecase: str, entities: bool = False) -> list[str]:
      if entities:
        return ["WINDOWS_AD"]
      return ["BRO_JSON"]

    with (
        patch(
            "logstory.logstory.get_usecases",
            return_value=[
                "ATTACK_UC",
                "CYMBAL_BASELINE_NETWORK",
                "CYMBAL_BASELINE_ENDPOINT",
            ],
        ),
        patch("logstory.logstory._get_logtypes", side_effect=fake_get_logtypes),
        patch(
            "logstory.logstory.imported_main.usecase_replay_logtype",
            side_effect=fake_replay_logtype,
        ),
        patch(
            "logstory.logstory._get_paired_baselines",
            side_effect=lambda uc: _get_paired_baselines(uc, search_roots=[tmp_path]),
        ),
    ):
      res = runner.invoke(
          app,
          [
              "replay",
              "usecase",
              "ATTACK_UC",
              "--with-paired-baselines",
              "--local-file-output",
              "--no-get",
          ],
      )
      assert res.exit_code == 0, res.stdout
      replayed_usecases = [call[0] for call in replayed_calls]
      assert replayed_usecases == [
          "CYMBAL_BASELINE_NETWORK",
          "CYMBAL_BASELINE_ENDPOINT",
          "ATTACK_UC",
      ]

  def test_replay_usecase_with_paired_baselines_downloads_when_get_enabled(
      self, tmp_path: Path
  ):
    manifest = _valid_manifest_dict(
        "ATTACK_UC",
        paired_baselines=["CYMBAL_BASELINE_NETWORK"],
    )
    _write_usecase_fixture(
        tmp_path,
        usecase_name="ATTACK_UC",
        manifest=manifest,
        eval_data=_valid_eval_dict("ATTACK_UC"),
    )

    installed = ["ATTACK_UC"]
    downloaded: list[str] = []

    def fake_download(uc: str, _bucket: str | None = None) -> bool:
      downloaded.append(uc)
      installed.append(uc)
      return True

    with (
        patch("logstory.logstory.get_usecases", side_effect=lambda: list(installed)),
        patch("logstory.logstory._download_usecase", side_effect=fake_download),
        patch("logstory.logstory._get_logtypes", return_value=["BRO_JSON"]),
        patch(
            "logstory.logstory.imported_main.usecase_replay_logtype",
            return_value=None,
        ),
        patch(
            "logstory.logstory._get_paired_baselines",
            side_effect=lambda uc: _get_paired_baselines(uc, search_roots=[tmp_path]),
        ),
    ):
      res = runner.invoke(
          app,
          [
              "replay",
              "usecase",
              "ATTACK_UC",
              "--with-paired-baselines",
              "--local-file-output",
              "--get",
          ],
      )
      assert res.exit_code == 0, res.stdout
      assert downloaded == ["CYMBAL_BASELINE_NETWORK"]
