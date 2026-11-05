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

"""Unit tests for v2 security usecase and Blue Team eval schema models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from logstory.schema import (
    AffectedAsset,
    AlertTriageTask,
    BenignConfusers,
    ChangeWindow,
    ComplianceGates,
    CounterfactualPair,
    CriticalityTier,
    DatabricksPlatform,
    DetectionEngineeringTask,
    DifficultyTier,
    EntitiesAndIocs,
    EnvironmentContext,
    EvaluationTasks,
    ExpectedActions,
    ExpectedDisposition,
    ExpectedVerdict,
    GoogleSecOpsDetection,
    GoogleSecOpsPlatform,
    GoogleSecOpsReferenceList,
    GoogleSecOpsRunFrequency,
    GoogleSecOpsSavedSearch,
    GroundingTier,
    GroundTruth,
    KillChainStage,
    MaliciousIoc,
    PairRelationship,
    ParsedUsecasePackage,
    PlatformBindings,
    ReferenceQueries,
    ScenarioType,
    SchemaValidationError,
    SecurityUsecaseEval,
    SecurityUsecaseManifest,
    SigmaPlatform,
    SplunkPlatform,
    TelemetrySection,
    TelemetryStream,
    ThreatContext,
    ThreatHuntTask,
    TimestampPolicy,
    build_eval_json_schema,
    build_usecase_json_schema,
    export_json_schemas,
    parse_usecase_package,
    split_frontmatter_and_body,
    split_solution_section,
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
          "Enterprise DNS and endpoint process telemetry package for network"
          " protocol analysis."
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
              "detections": [{
                  "name": "dns_tunneling_low_reputation_domain",
                  "path": "RULES/dns_tunneling_low_reputation_domain.yl2",
                  "live": True,
                  "alerting": True,
                  "notes": "Detects high-entropy DNS subdomain queries.",
              }],
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
  udm_query = (
      'metadata.event_type = "NETWORK_DNS" AND'
      " network.dns.questions.name = /stratioai\\.org$/"
  )
  databricks_sql_query = (
      "SELECT * FROM security_lakehouse.ocsf_silver.dns_activity"
      " WHERE query_hostname LIKE '%.stratioai.org'"
  )
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
              "prompt": (
                  "Triage CASE-4012 and determine disposition, affected assets,"
                  " and containment actions."
              ),
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
              "prompt_unalerted": (
                  "Hunt across zeek_dns and windows_ad_users streams for"
                  " covert C2 or DNS exfiltration activity."
              ),
              "prompt_intel_driven": (
                  "Sweep telemetry for indicators associated with advisory AA24-242A."
              ),
              "expected_patient_zero": "fin-wks-20",
              "time_horizon_hours": 168,
          },
          "detection_engineering": {
              "enabled": True,
              "prompt": (
                  "Author a detection rule identifying hex-encoded subdomain"
                  " exfiltration over DNS."
              ),
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
              "Compromised finance workstation exfiltrating sensitive payload"
              " chunks via hex-encoded DNS TXT/A queries to stratioai.org."
          ),
          "kill_chain": [{
              "stage": "exfiltration",
              "stream_id": "zeek_dns",
              "timestamp_utc": "2026-10-18T11:20:00Z",
              "tactic": "TA0010",
              "technique_id": "T1048.003",
              "summary": "Hex-encoded subdomain DNS queries to C2 domain.",
              "key_evidence": [
                  "4a6f686e446f655365637265745061796c6f6164.t.stratioai.org"
              ],
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
                  "change_window": {
                      "ticket_id": "CHG-2026-1018",
                      "approved": False,
                      "start_utc": "2026-10-18T01:00:00Z",
                      "end_utc": "2026-10-18T03:00:00Z",
                      "summary": "Unrelated nocturnal DNS cache flush.",
                  },
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
          "google_secops_udm": [udm_query],
          "google_secops_yaral": ["RULES/dns_tunneling_low_reputation_domain.yl2"],
          "databricks_sql": [databricks_sql_query],
          "sigma": ["RULES/sigma_dns_tunneling.yml"],
          "splunk_spl": ['sourcetype="zeek:dns:json" query="*.stratioai.org"'],
      },
  }


class TestManifestAndEvalModels:
  """Test v2 SecurityUsecaseManifest and SecurityUsecaseEval serialization."""

  def test_manifest_roundtrip_and_types(self):
    raw = _valid_manifest_dict()
    manifest = SecurityUsecaseManifest.from_dict(raw)

    assert manifest.schema_version == "2.0"
    assert manifest.id == "DNS_TUNNELING_EXFIL_GTI"
    assert manifest.version == "2.0.0"
    assert manifest.author == "Google Cloud Security"
    assert manifest.license == "Apache-2.0"
    assert isinstance(manifest.environment, EnvironmentContext)
    assert manifest.environment.scenario_type == ScenarioType.ATTACK
    assert manifest.environment.paired_baselines == ["CYMBAL_BASELINE_NETWORK"]
    assert isinstance(manifest.environment.timestamp_policy, TimestampPolicy)
    assert isinstance(manifest.telemetry, TelemetrySection)
    assert isinstance(manifest.telemetry.events[0], TelemetryStream)
    assert manifest.telemetry.events[0].ocsf_class_uid == 4003
    assert isinstance(manifest.platforms, PlatformBindings)
    assert isinstance(manifest.platforms.google_secops, GoogleSecOpsPlatform)
    assert isinstance(
        manifest.platforms.google_secops.run_frequency,
        GoogleSecOpsRunFrequency,
    )
    assert isinstance(
        manifest.platforms.google_secops.detections[0], GoogleSecOpsDetection
    )
    assert isinstance(
        manifest.platforms.google_secops.saved_searches[0],
        GoogleSecOpsSavedSearch,
    )
    assert isinstance(
        manifest.platforms.google_secops.reference_lists[0],
        GoogleSecOpsReferenceList,
    )
    assert isinstance(manifest.platforms.databricks, DatabricksPlatform)
    assert isinstance(manifest.platforms.sigma, SigmaPlatform)
    assert isinstance(manifest.platforms.splunk, SplunkPlatform)

    serialized = manifest.to_dict()
    rehydrated = SecurityUsecaseManifest.from_dict(serialized)
    assert rehydrated.to_dict() == serialized

  def test_google_secops_detection_optional_path(self):
    det = GoogleSecOpsDetection.from_dict({
        "name": "whoami_execution.yaral",
        "live": True,
        "alerting": False,
        "notes": "Rule Workshop slide 17",
    })
    assert det.path is None
    assert det.to_dict()["path"] is None

  def test_eval_roundtrip_and_types(self):
    raw = _valid_eval_dict()
    eval_model = SecurityUsecaseEval.from_dict(raw)

    assert eval_model.schema_version == "2.0"
    assert eval_model.usecase_id == "DNS_TUNNELING_EXFIL_GTI"
    assert isinstance(eval_model.threat_context, ThreatContext)
    assert eval_model.threat_context.grounding_tier == (GroundingTier.STIX_GROUNDED)
    assert eval_model.threat_context.difficulty_tier == DifficultyTier.ADVANCED
    assert isinstance(eval_model.tasks, EvaluationTasks)
    assert isinstance(eval_model.tasks.alert_triage, AlertTriageTask)
    assert isinstance(eval_model.tasks.threat_hunt, ThreatHuntTask)
    assert isinstance(eval_model.tasks.detection_engineering, DetectionEngineeringTask)
    assert isinstance(eval_model.ground_truth, GroundTruth)
    assert eval_model.ground_truth.expected_disposition == (
        ExpectedDisposition.TRUE_POSITIVE
    )
    assert eval_model.ground_truth.expected_verdict == (ExpectedVerdict.MALICIOUS)
    assert isinstance(eval_model.ground_truth.kill_chain[0], KillChainStage)
    assert isinstance(eval_model.ground_truth.entities_and_iocs, EntitiesAndIocs)
    assert isinstance(
        eval_model.ground_truth.entities_and_iocs.affected_assets[0],
        AffectedAsset,
    )
    assert (
        eval_model.ground_truth.entities_and_iocs.affected_assets[0].criticality_tier
        == CriticalityTier.TIER_2_WORKSTATION
    )
    assert isinstance(
        eval_model.ground_truth.entities_and_iocs.malicious_iocs[0],
        MaliciousIoc,
    )
    assert isinstance(
        eval_model.ground_truth.entities_and_iocs.benign_confusers,
        BenignConfusers,
    )
    assert isinstance(
        eval_model.ground_truth.entities_and_iocs.benign_confusers.change_window,
        ChangeWindow,
    )
    assert isinstance(eval_model.compliance_gates, ComplianceGates)
    assert isinstance(eval_model.compliance_gates.expected_actions, ExpectedActions)
    assert isinstance(eval_model.counterfactual_pair, CounterfactualPair)
    assert eval_model.counterfactual_pair.pair_relationship == (
        PairRelationship.MALICIOUS_VARIANT_OF_BENIGN_BASELINE
    )
    assert isinstance(eval_model.reference_queries, ReferenceQueries)

    serialized = eval_model.to_dict()
    rehydrated = SecurityUsecaseEval.from_dict(serialized)
    assert rehydrated.to_dict() == serialized


class TestSchemaValidationErrors:
  """Test rejection of unknown keys, missing required fields, and bad enums."""

  def test_rejects_unknown_top_level_key_in_manifest(self):
    bad = _valid_manifest_dict()
    bad["unexpected_spoiler_field"] = "bad"
    with pytest.raises(SchemaValidationError) as exc_info:
      SecurityUsecaseManifest.from_dict(bad)
    assert "unexpected_spoiler_field" in str(exc_info.value)

  def test_rejects_unknown_nested_key_in_eval(self):
    bad = _valid_eval_dict()
    bad["ground_truth"]["unknown_nested_key"] = 123
    with pytest.raises(SchemaValidationError) as exc_info:
      SecurityUsecaseEval.from_dict(bad)
    assert "unknown_nested_key" in str(exc_info.value)

  def test_rejects_invalid_enum_values(self):
    bad_eval = _valid_eval_dict()
    bad_eval["ground_truth"]["expected_disposition"] = "MAYBE_MALICIOUS"
    with pytest.raises(SchemaValidationError) as exc_info:
      SecurityUsecaseEval.from_dict(bad_eval)
    assert "expected_disposition" in str(exc_info.value)

    bad_manifest = _valid_manifest_dict()
    bad_manifest["environment"]["scenario_type"] = "not_a_type"
    with pytest.raises(SchemaValidationError) as exc_info:
      SecurityUsecaseManifest.from_dict(bad_manifest)
    assert "scenario_type" in str(exc_info.value)

  def test_rejects_missing_required_okf_fields(self):
    for required_key in ("license", "version", "author", "id", "title"):
      bad = _valid_manifest_dict()
      del bad[required_key]
      with pytest.raises(SchemaValidationError) as exc_info:
        SecurityUsecaseManifest.from_dict(bad)
      assert required_key in str(exc_info.value)


class TestPackageParsingAndBlindMode:
  """Test splitting frontmatter, solution delimiter, and blind package mode."""

  def test_split_frontmatter_and_solution_section(self, tmp_path: Path):
    usecase_dir = tmp_path / "DNS_TUNNELING_EXFIL_GTI"
    usecase_dir.mkdir()

    frontmatter_yaml = yaml.safe_dump(_valid_manifest_dict(), sort_keys=False)
    md_content = (
        f"---\n{frontmatter_yaml}---\n\n"
        "# DNS_TUNNELING_EXFIL_GTI\n\n"
        "Public blind-safe telemetry overview.\n\n"
        "<!-- BEGIN_SOLUTION -->\n\n"
        "## Analyst Solution Walkthrough\n\n"
        "Attacker exfiltrated data to stratioai.org from fin-wks-20.\n"
    )
    (usecase_dir / "DNS_TUNNELING_EXFIL_GTI.md").write_text(
        md_content, encoding="utf-8"
    )
    (usecase_dir / "eval.yaml").write_text(
        yaml.safe_dump(_valid_eval_dict(), sort_keys=False), encoding="utf-8"
    )

    parsed_fm, body = split_frontmatter_and_body(md_content)
    assert parsed_fm["id"] == "DNS_TUNNELING_EXFIL_GTI"
    pub_body, sol_body = split_solution_section(body)
    assert "Public blind-safe telemetry overview." in pub_body
    assert "stratioai.org" not in pub_body
    assert sol_body is not None
    assert "stratioai.org" in sol_body

    blind_pkg = parse_usecase_package(usecase_dir, blind=True)
    assert isinstance(blind_pkg, ParsedUsecasePackage)
    assert blind_pkg.schema_version == "2.0"
    assert blind_pkg.manifest is not None
    assert "Public blind-safe telemetry overview." in (blind_pkg.public_markdown_body)
    assert "stratioai.org" not in blind_pkg.public_markdown_body
    assert blind_pkg.solution_markdown_body is None
    assert blind_pkg.eval_data is None

    full_pkg = parse_usecase_package(usecase_dir, blind=False)
    assert full_pkg.solution_markdown_body is not None
    assert "stratioai.org" in full_pkg.solution_markdown_body
    assert full_pkg.eval_data is not None
    assert full_pkg.eval_data.usecase_id == "DNS_TUNNELING_EXFIL_GTI"

    blind_serialized = full_pkg.to_dict(blind=True)
    assert blind_serialized["solution_markdown_body"] is None
    assert blind_serialized["eval_data"] is None
    full_serialized = full_pkg.to_dict(blind=False)
    assert full_serialized["solution_markdown_body"] is not None
    assert full_serialized["eval_data"] is not None

  def test_legacy_v1_package_and_error_branches(self, tmp_path: Path):
    v1_dir = tmp_path / "LEGACY_USECASE"
    v1_dir.mkdir()
    (v1_dir / "LEGACY_USECASE.md").write_text(
        "---\ntitle: LEGACY_USECASE\ndescription: Legacy v1\n---\n\n# Body\n",
        encoding="utf-8",
    )
    pkg = parse_usecase_package(v1_dir, blind=False)
    assert pkg.schema_version == "1.0"
    assert pkg.manifest is None
    assert pkg.solution_markdown_body is None
    assert pkg.to_dict(blind=False)["manifest"]["title"] == "LEGACY_USECASE"

    with pytest.raises(SchemaValidationError):
      split_frontmatter_and_body("No frontmatter here")

    with pytest.raises(SchemaValidationError):
      split_frontmatter_and_body("---\nunterminated: true\n")


class TestJsonSchemaExport:
  """Test Draft 2020-12 JSON Schema generation and deterministic export."""

  def test_export_json_schemas_deterministic(self, tmp_path: Path):
    usecase_path, eval_path = export_json_schemas(tmp_path)
    assert usecase_path == tmp_path / "usecase.schema.json"
    assert eval_path == tmp_path / "eval.schema.json"
    assert usecase_path.exists()
    assert eval_path.exists()

    usecase_schema = json.loads(usecase_path.read_text(encoding="utf-8"))
    eval_schema = json.loads(eval_path.read_text(encoding="utf-8"))

    assert usecase_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert eval_schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert usecase_schema["additionalProperties"] is False
    assert eval_schema["additionalProperties"] is False
    assert "telemetry" in usecase_schema["properties"]
    assert "platforms" in usecase_schema["properties"]
    assert "ground_truth" in eval_schema["properties"]
    assert "compliance_gates" in eval_schema["properties"]

    # Verify deterministic output matches builder functions
    assert usecase_schema == build_usecase_json_schema()
    assert eval_schema == build_eval_json_schema()
