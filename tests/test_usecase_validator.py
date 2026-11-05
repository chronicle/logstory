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

"""Unit tests for the 5-gate usecase package validator and anti-spoiler checker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from logstory.schema import (
    UsecaseValidationResult,
    ValidationFinding,
    validate_usecase_corpus,
    validate_usecase_package,
)


def _valid_manifest_dict() -> dict[str, Any]:
  """Return a complete valid v2 SecurityUsecaseManifest dictionary."""
  return {
      "schema_version": "2.0",
      "id": "DNS_TUNNELING_EXFIL_GTI",
      "title": "DNS Tunneling Data Exfiltration Telemetry Package",
      "version": "2.0.0",
      "created": "2026-10-18",
      "updated": "2026-11-05",
      "author": "Google Cloud Security",
      "license": "Apache-2.0",
      "description": (
          "Enterprise DNS and directory telemetry package for network protocol"
          " analysis."
      ),
      "tags": [
          "network-c2",
          "dns",
          "ocsf",
          "google-secops",
          "databricks",
      ],
      "environment": {
          "organization": "cymbal-investments.org",
          "scenario_type": "attack",
          "paired_baselines": ["CYMBAL_BASELINE_NETWORK"],
          "timestamp_policy": {
              "base_date": "2026-10-18",
              "preserve_relative_offsets": True,
              "default_delta": "1d",
              "entity_offset_days": 1,
          },
          "notes": "Standard enterprise network telemetry segment.",
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
              "notes": "Core DNS resolution telemetry.",
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
              "notes": "Directory user context.",
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
              "detections": [
                  {
                      "name": "dns_tunneling_low_reputation_domain",
                      "path": "RULES/dns_tunneling_low_reputation_domain.yl2",
                      "live": True,
                      "alerting": True,
                      "notes": "Detects high-entropy DNS subdomain queries.",
                  },
                  {
                      "name": "workshop_conceptual_rule_without_file",
                      "path": None,
                      "live": False,
                      "alerting": False,
                      "notes": "Conceptual workshop rule.",
                  },
              ],
              "saved_searches": [{
                  "name": "High Entropy DNS Queries",
                  "creator": "secops-team@cymbal-investments.org",
                  "notes": "Baseline DNS query length exploration.",
              }],
              "reference_lists": [{
                  "name": "approved_dns_resolvers",
                  "type": "String",
                  "notes": "Internal corporate DNS resolvers.",
              }],
          },
          "databricks": {
              "catalog": "security_lakehouse",
              "schema_name": "ocsf_silver",
              "table_mappings": {
                  "zeek_dns": "secops_ocsf.dns_activity",
                  "windows_ad_users": "secops_ocsf.user_inventory",
              },
              "detections": ["RULES/databricks_dns_tunneling.sql"],
          },
          "sigma": {
              "rules": ["RULES/sigma_dns_tunneling.yml"],
          },
          "splunk": {
              "sourcetypes": {
                  "zeek_dns": "zeek:dns:json",
                  "windows_ad_users": "ms:ad:user",
              },
          },
      },
  }


def _valid_eval_dict() -> dict[str, Any]:
  """Return a complete valid v2 SecurityUsecaseEval dictionary."""
  return {
      "schema_version": "2.0",
      "usecase_id": "DNS_TUNNELING_EXFIL_GTI",
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
          "release_day": 14,
      },
      "tasks": {
          "alert_triage": {
              "enabled": True,
              "case_id": "CASE-4012",
              "alert_ids": ["de_4cfa127e-8a09-3f1b-05b8-588dbfaf257b"],
              "prompt": "Triage CASE-4012 and determine disposition.",
              "expected_skill": "dns-tunneling-network-beacon-hunt",
              "skill_bindings": {
                  "google_secops": "dns-tunneling-network-beacon-hunt",
                  "goose": "dns-tunneling-network-beacon-hunt",
                  "databricks": "ocsf-dns-beacon-hunt",
              },
              "time_horizon_hours": 72,
          },
          "threat_hunt": {
              "enabled": True,
              "prompt_unalerted": "Hunt across zeek_dns and windows_ad_users.",
              "prompt_intel_driven": "Sweep telemetry for CISA advisory indicators.",
              "expected_patient_zero": "fin-wks-20",
              "time_horizon_hours": 168,
          },
          "detection_engineering": {
              "enabled": True,
              "prompt": "Author a detection rule for DNS tunneling.",
              "target_techniques": ["T1071.004", "T1048.003"],
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
          "root_cause_summary": (
              "Compromised finance workstation exfiltrating data via DNS"
              " queries to stratioai.org."
          ),
          "kill_chain": [{
              "stage": "exfiltration",
              "stream_id": "zeek_dns",
              "timestamp_utc": "2026-10-18T11:20:00Z",
              "tactic": "TA0010",
              "technique_id": "T1048.003",
              "summary": "Hex-encoded subdomain DNS queries to C2 domain.",
              "key_evidence": ["4a6f686e446f65536563726574.t.stratioai.org"],
          }],
          "entities_and_iocs": {
              "compromised_accounts": ["alice.smith"],
              "affected_assets": [{
                  "hostname": "fin-wks-20",
                  "criticality_tier": "tier_2_workstation",
                  "ip_addresses": ["10.128.0.20"],
                  "role": "Finance analyst workstation",
                  "patient_zero": True,
                  "blast_radius_fp_usd": 500.0,
                  "blast_radius_fn_usd": 50000.0,
              }],
              "malicious_iocs": [
                  {
                      "type": "domain",
                      "value": "stratioai.org",
                      "role": "c2_domain",
                      "notes": "Primary authoritative DNS tunneling domain.",
                  },
                  {
                      "type": "ip",
                      "value": "198.51.100.44",
                      "role": "c2_resolver",
                      "notes": "External malicious DNS server IP.",
                  },
              ],
              "benign_confusers": {
                  "signed_lolbins": [
                      "7d99c80a1249a1ec9af0f3047c855778b06ea57e11943a271071985afe09e6c2"
                  ],
                  "internal_ips": ["10.128.0.20"],
              },
          },
      },
      "compliance_gates": {
          "requires_pre_containment_verification": True,
          "requires_168h_horizon_widening": False,
          "forbid_external_cti_on_internal_ips": True,
          "forbid_lolbin_hash_blocking": True,
          "respect_change_window": False,
          "expected_actions": {
              "primary": ["isolate_host:fin-wks-20", "block_ioc:stratioai.org"],
              "secondary": ["reset_credentials:alice.smith"],
              "prohibited": [
                  "block_ioc:7d99c80a1249a1ec9af0f3047c855778b06ea57e11943a271071985afe09e6c2",
                  "enrich_external_cti:10.128.0.20",
              ],
          },
      },
      "counterfactual_pair": {
          "paired_usecase_id": "CYMBAL_BASELINE_NETWORK",
          "pair_relationship": "malicious_variant_of_benign_baseline",
          "shared_entities": ["fin-wks-20", "alice.smith"],
          "shared_telemetry_streams": ["zeek_dns"],
          "discriminating_invariant": (
              "Subdomain labels exceed 40 hex chars and resolve to"
              " unapproved external domain stratioai.org."
          ),
      },
      "reference_queries": {
          "google_secops_udm": ['metadata.event_type = "NETWORK_DNS"'],
          "google_secops_yaral": ["RULES/dns_tunneling_low_reputation_domain.yl2"],
          "databricks_sql": [
              "SELECT * FROM security_lakehouse.ocsf_silver.dns_activity"
          ],
          "sigma": ["RULES/sigma_dns_tunneling.yml"],
          "splunk_spl": ['sourcetype="zeek:dns:json"'],
      },
  }


def _write_usecase_fixture(
    root_dir: Path,
    manifest: dict[str, Any] | None = None,
    eval_data: dict[str, Any] | None = None,
    public_body: str = "# DNS_TUNNELING_EXFIL_GTI\n\nBlind-safe public overview.",
    solution_body: str | None = (
        "## Analyst Solution\n\n"
        "Compromised account alice.smith exfiltrated data to stratioai.org "
        "(198.51.100.44) matching advisory AA24-242A."
    ),
    create_files: bool = True,
    usecase_name: str = "DNS_TUNNELING_EXFIL_GTI",
) -> Path:
  """Materialize a usecase directory fixture on disk for validator tests."""
  usecase_dir = root_dir / usecase_name
  usecase_dir.mkdir(parents=True, exist_ok=True)

  manifest_dict = manifest if manifest is not None else _valid_manifest_dict()
  frontmatter_yaml = yaml.safe_dump(manifest_dict, sort_keys=False)
  if solution_body is not None:
    md_text = (
        f"---\n{frontmatter_yaml}---\n\n{public_body}\n\n"
        f"<!-- BEGIN_SOLUTION -->\n\n{solution_body}\n"
    )
  else:
    md_text = f"---\n{frontmatter_yaml}---\n\n{public_body}\n"

  (usecase_dir / f"{usecase_name}.md").write_text(md_text, encoding="utf-8")

  eval_dict = eval_data if eval_data is not None else _valid_eval_dict()
  (usecase_dir / "eval.yaml").write_text(
      yaml.safe_dump(eval_dict, sort_keys=False), encoding="utf-8"
  )

  if create_files:
    events_dir = usecase_dir / "EVENTS"
    entities_dir = usecase_dir / "ENTITIES"
    rules_dir = usecase_dir / "RULES"
    events_dir.mkdir(exist_ok=True)
    entities_dir.mkdir(exist_ok=True)
    rules_dir.mkdir(exist_ok=True)
    (events_dir / "BRO_JSON.log").write_text('{"ts": 1}\n', encoding="utf-8")
    (entities_dir / "WINDOWS_AD.log").write_text('{"user": 1}\n', encoding="utf-8")
    (rules_dir / "dns_tunneling_low_reputation_domain.yl2").write_text(
        "rule dns_tunneling_low_reputation_domain {}\n", encoding="utf-8"
    )
    (rules_dir / "sigma_dns_tunneling.yml").write_text(
        "title: Sigma DNS Tunneling\n", encoding="utf-8"
    )

  return usecase_dir


class TestGate1SchemaAndProvenance:
  """Test Gate 1 (G1_SCHEMA) schema and OKF v0.2 provenance checks."""

  def test_valid_v2_package_passes_all_gates(self, tmp_path: Path):
    usecase_dir = _write_usecase_fixture(tmp_path)
    baseline_dir = tmp_path / "CYMBAL_BASELINE_NETWORK"
    baseline_dir.mkdir()

    result = validate_usecase_package(usecase_dir, strict_v2=True, corpus_root=tmp_path)
    assert isinstance(result, UsecaseValidationResult)
    assert result.is_valid is True
    assert result.schema_version == "2.0"
    assert result.errors == []
    assert result.warnings == []

    serialized = result.to_dict()
    assert serialized["usecase_id"] == "DNS_TUNNELING_EXFIL_GTI"
    assert serialized["is_valid"] is True
    assert serialized["errors"] == []

  @pytest.mark.parametrize("missing_field", ["license", "version", "author"])
  def test_missing_okf_provenance_field_fails_g1(
      self, tmp_path: Path, missing_field: str
  ):
    manifest = _valid_manifest_dict()
    del manifest[missing_field]
    usecase_dir = _write_usecase_fixture(tmp_path, manifest=manifest)

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G1_SCHEMA" and missing_field in f.message for f in result.errors
    )

  def test_invalid_iso_dates_fail_g1(self, tmp_path: Path):
    manifest = _valid_manifest_dict()
    manifest["created"] = "10/18/2026"
    usecase_dir = _write_usecase_fixture(tmp_path, manifest=manifest)

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(f.gate == "G1_SCHEMA" and "created" in f.message for f in result.errors)

  def test_invalid_eval_enum_fails_g1(self, tmp_path: Path):
    eval_data = _valid_eval_dict()
    eval_data["ground_truth"]["expected_disposition"] = "NOT_A_DISPOSITION"
    usecase_dir = _write_usecase_fixture(tmp_path, eval_data=eval_data)

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G1_SCHEMA" and "expected_disposition" in (f.path or "")
        for f in result.errors
    )


class TestGate2StreamAndFileIntegrity:
  """Test Gate 2 (G2_INTEGRITY) stream cross-references and on-disk files."""

  def test_missing_event_log_file_fails_g2(self, tmp_path: Path):
    usecase_dir = _write_usecase_fixture(tmp_path)
    (usecase_dir / "EVENTS" / "BRO_JSON.log").unlink()

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G2_INTEGRITY" and "EVENTS/BRO_JSON.log" in f.message
        for f in result.errors
    )

  def test_missing_detection_rule_file_fails_g2(self, tmp_path: Path):
    usecase_dir = _write_usecase_fixture(tmp_path)
    (usecase_dir / "RULES" / "dns_tunneling_low_reputation_domain.yl2").unlink()

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G2_INTEGRITY"
        and "dns_tunneling_low_reputation_domain.yl2" in f.message
        for f in result.errors
    )

  def test_unknown_kill_chain_stream_id_fails_g2(self, tmp_path: Path):
    eval_data = _valid_eval_dict()
    eval_data["ground_truth"]["kill_chain"][0]["stream_id"] = "nonexistent_stream"
    usecase_dir = _write_usecase_fixture(tmp_path, eval_data=eval_data)

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G2_INTEGRITY" and "nonexistent_stream" in f.message
        for f in result.errors
    )

  def test_missing_entity_and_sigma_rule_and_platform_mapping_fails_g2(
      self, tmp_path: Path
  ):
    manifest = _valid_manifest_dict()
    manifest["platforms"]["google_secops"]["log_type_mappings"][
        "unknown_stream"
    ] = "POWERSHELL"
    manifest["platforms"]["databricks"]["table_mappings"][
        "unknown_db_stream"
    ] = "secops_ocsf.proc"
    manifest["platforms"]["splunk"]["sourcetypes"][
        "unknown_splunk_stream"
    ] = "win:security"
    usecase_dir = _write_usecase_fixture(tmp_path, manifest=manifest)
    (usecase_dir / "ENTITIES" / "WINDOWS_AD.log").unlink()
    (usecase_dir / "RULES" / "sigma_dns_tunneling.yml").unlink()

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    error_messages = [f.message for f in result.errors if f.gate == "G2_INTEGRITY"]
    assert any("ENTITIES/WINDOWS_AD.log" in msg for msg in error_messages)
    assert any("RULES/sigma_dns_tunneling.yml" in msg for msg in error_messages)
    assert any("unknown_stream" in msg for msg in error_messages)
    assert any("unknown_db_stream" in msg for msg in error_messages)
    assert any("unknown_splunk_stream" in msg for msg in error_messages)


class TestGate3AntiSpoilerLeakage:
  """Test Gate 3 (G3_ANTI_SPOILER) frontmatter and markdown boundary checks."""

  @pytest.mark.parametrize(
      "forbidden_key",
      ["ground_truth", "kill_chain", "malicious_iocs", "compliance_gates"],
  )
  def test_forbidden_ground_truth_key_in_frontmatter_fails_g3(
      self, tmp_path: Path, forbidden_key: str
  ):
    manifest = _valid_manifest_dict()
    manifest[forbidden_key] = {"leaked": True}
    usecase_dir = _write_usecase_fixture(tmp_path, manifest=manifest)

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G3_ANTI_SPOILER" and forbidden_key in f.message
        for f in result.errors
    )

  @pytest.mark.parametrize(
      ("leaked_value", "target_field"),
      [
          ("stratioai.org", "title"),
          ("198.51.100.44", "description"),
          ("alice.smith", "tags"),
          ("AA24-242A", "notes"),
      ],
  )
  def test_spoiler_value_in_frontmatter_fields_fails_g3(
      self, tmp_path: Path, leaked_value: str, target_field: str
  ):
    manifest = _valid_manifest_dict()
    if target_field == "tags":
      manifest["tags"].append(leaked_value)
    elif target_field == "notes":
      manifest["environment"]["notes"] = f"Investigate {leaked_value} activity."
    else:
      manifest[target_field] = f"Scenario involving {leaked_value}"

    usecase_dir = _write_usecase_fixture(tmp_path, manifest=manifest)
    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G3_ANTI_SPOILER" and leaked_value in f.message for f in result.errors
    )

  @pytest.mark.parametrize(
      "leaked_value", ["stratioai.org", "alice.smith", "AA24-242A"]
  )
  def test_spoiler_value_above_begin_solution_fails_g3(
      self, tmp_path: Path, leaked_value: str
  ):
    public_body = (
        "# DNS_TUNNELING_EXFIL_GTI\n\n"
        f"This scenario contains indicator {leaked_value} in the public section."
    )
    usecase_dir = _write_usecase_fixture(tmp_path, public_body=public_body)

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G3_ANTI_SPOILER" and leaked_value in f.message for f in result.errors
    )

  def test_spoiler_values_below_begin_solution_pass_g3(self, tmp_path: Path):
    usecase_dir = _write_usecase_fixture(
        tmp_path,
        public_body="# DNS_TUNNELING_EXFIL_GTI\n\nClean blind-safe description.",
        solution_body=(
            "## Full Walkthrough\n\n"
            "Indicator stratioai.org (198.51.100.44), user alice.smith, "
            "and advisory AA24-242A are documented here below the delimiter."
        ),
    )

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is True
    assert not any(f.gate == "G3_ANTI_SPOILER" for f in result.findings)


class TestGate4CounterfactualTwinConsistency:
  """Test Gate 4 (G4_COUNTERFACTUAL) paired baseline consistency and corpus checks."""

  def test_missing_paired_baseline_in_manifest_fails_g4(self, tmp_path: Path):
    manifest = _valid_manifest_dict()
    manifest["environment"]["paired_baselines"] = []
    usecase_dir = _write_usecase_fixture(tmp_path, manifest=manifest)

    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is False
    assert any(
        f.gate == "G4_COUNTERFACTUAL" and "CYMBAL_BASELINE_NETWORK" in f.message
        for f in result.errors
    )

  def test_benign_baseline_with_attack_twin_does_not_require_self_in_paired_baselines(
      self, tmp_path: Path
  ):
    manifest = _valid_manifest_dict()
    manifest["id"] = "CYMBAL_BASELINE_NETWORK"
    manifest["environment"]["scenario_type"] = "benign_baseline"
    manifest["environment"]["paired_baselines"] = []

    eval_data = _valid_eval_dict()
    eval_data["usecase_id"] = "CYMBAL_BASELINE_NETWORK"
    eval_data["counterfactual_pair"] = {
        "paired_usecase_id": "DNS_TUNNELING_EXFIL_GTI",
        "pair_relationship": "benign_baseline_for_malicious_variant",
        "shared_entities": ["fin-wks-20"],
        "shared_telemetry_streams": ["zeek_dns"],
        "discriminating_invariant": "Benign corporate DNS traffic only.",
    }

    usecase_dir = _write_usecase_fixture(
        tmp_path,
        manifest=manifest,
        eval_data=eval_data,
        usecase_name="CYMBAL_BASELINE_NETWORK",
    )
    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is True

  def test_missing_paired_directory_in_corpus_root_fails_g4(self, tmp_path: Path):
    usecase_dir = _write_usecase_fixture(tmp_path)

    result = validate_usecase_package(usecase_dir, strict_v2=True, corpus_root=tmp_path)
    assert result.is_valid is False
    assert any(
        f.gate == "G4_COUNTERFACTUAL" and "CYMBAL_BASELINE_NETWORK" in f.message
        for f in result.errors
    )


class TestGate5LegacyV1CompatibilityAndCorpus:
  """Test Gate 5 (G5_LEGACY_V1) compatibility mode and corpus validation."""

  def test_legacy_v1_warns_when_not_strict_and_fails_when_strict(self, tmp_path: Path):
    v1_dir = tmp_path / "LEGACY_WORKSHOP"
    v1_dir.mkdir()
    (v1_dir / "LEGACY_WORKSHOP.md").write_text(
        "---\n"
        "title: LEGACY_WORKSHOP\n"
        "description: Legacy v1 usecase\n"
        "tags:\n"
        "  - workshop\n"
        "events:\n"
        "  - log_type: POWERSHELL\n"
        "---\n\n"
        "# LEGACY_WORKSHOP\n",
        encoding="utf-8",
    )

    permissive = validate_usecase_package(v1_dir, strict_v2=False)
    assert permissive.is_valid is True
    assert permissive.schema_version == "1.0"
    assert permissive.errors == []
    assert len(permissive.warnings) == 1
    assert isinstance(permissive.warnings[0], ValidationFinding)
    assert permissive.warnings[0].gate == "G5_LEGACY_V1"
    assert permissive.warnings[0].severity == "WARNING"

    strict = validate_usecase_package(v1_dir, strict_v2=True)
    assert strict.is_valid is False
    assert any(
        f.gate == "G5_LEGACY_V1" and f.severity == "ERROR" for f in strict.errors
    )

  def test_validate_usecase_corpus_discovers_and_validates_all(self, tmp_path: Path):
    _write_usecase_fixture(tmp_path)

    baseline_manifest = _valid_manifest_dict()
    baseline_manifest["id"] = "CYMBAL_BASELINE_NETWORK"
    baseline_manifest["environment"]["scenario_type"] = "benign_baseline"
    baseline_manifest["environment"]["paired_baselines"] = []

    baseline_eval = _valid_eval_dict()
    baseline_eval["usecase_id"] = "CYMBAL_BASELINE_NETWORK"
    baseline_eval["ground_truth"]["expected_disposition"] = "BENIGN_POSITIVE"
    baseline_eval["ground_truth"]["expected_verdict"] = "BENIGN"
    baseline_eval["ground_truth"]["kill_chain"] = []
    baseline_eval["ground_truth"]["entities_and_iocs"]["compromised_accounts"] = []
    baseline_eval["ground_truth"]["entities_and_iocs"]["malicious_iocs"] = []
    baseline_eval["threat_context"]["cisa_advisories"] = []
    baseline_eval["counterfactual_pair"] = {
        "paired_usecase_id": "DNS_TUNNELING_EXFIL_GTI",
        "pair_relationship": "benign_baseline_for_malicious_variant",
        "shared_entities": ["fin-wks-20"],
        "shared_telemetry_streams": ["zeek_dns"],
        "discriminating_invariant": "Normal DNS baseline.",
    }
    _write_usecase_fixture(
        tmp_path,
        manifest=baseline_manifest,
        eval_data=baseline_eval,
        usecase_name="CYMBAL_BASELINE_NETWORK",
    )

    results = validate_usecase_corpus(tmp_path, strict_v2=True)
    assert len(results) == 2
    assert [r.usecase_id for r in results] == [
        "CYMBAL_BASELINE_NETWORK",
        "DNS_TUNNELING_EXFIL_GTI",
    ]
    assert all(r.is_valid for r in results)
