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

"""Unit tests for v1/v2 usecase documentation generator and built-in usecases."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from logstory.schema import parse_usecase_package, validate_usecase_package
from usecases.generate_usecase_docs import (
    _render_without_jinja2,
    generate_usecase_doc,
    normalize_frontmatter_for_template,
    parse_frontmatter,
    process_usecase_directory,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "usecases" / "usecase_template.j2"


def _sample_v2_frontmatter() -> dict[str, Any]:
  """Return a complete v2 SecurityUsecaseManifest frontmatter dictionary."""
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


def _sample_v1_frontmatter() -> dict[str, Any]:
  """Return a legacy v1 frontmatter dictionary."""
  return {
      "title": "LEGACY_WORKSHOP",
      "description": "Legacy v1 workshop usecase.",
      "tags": ["workshop", "legacy"],
      "created": "2025-07-26",
      "updated": "2025-07-26",
      "run_frequency": {
          "events": "Every 3 days",
          "entities": "Every 3 days (offset 1 day)",
      },
      "data_rbac": "Must be disabled",
      "events": [{
          "log_type": "POWERSHELL.log",
          "product_name": "PowerShell",
          "vendor_name": "Microsoft",
          "notes": "PowerShell script block logs",
      }],
      "entities": [{
          "log_type": "N/A",
          "product_name": "",
          "vendor_name": "",
          "notes": "",
      }],
      "rules": [{
          "name": "whoami_execution.yaral",
          "live": True,
          "alerting": False,
          "notes": "Slide 17",
      }],
      "saved_searches": [{
          "name": "Failed User Logins",
          "creator": "Curated",
          "notes": "Slide 15",
      }],
      "reference_lists": [{
          "name": "key_servers",
          "type": "String",
          "notes": "Key server hostnames",
      }],
  }


class TestFrontmatterNormalization:
  """Test v1/v2 frontmatter normalization shim for template rendering."""

  def test_normalize_v2_frontmatter_populates_legacy_and_preserves_v2_keys(
      self,
  ):
    v2 = _sample_v2_frontmatter()
    normalized = normalize_frontmatter_for_template(v2)

    # Preserved v2 keys
    assert normalized["schema_version"] == "2.0"
    assert normalized["id"] == "DNS_TUNNELING_EXFIL_GTI"
    assert normalized["version"] == "2.0.0"
    assert normalized["author"] == "Google Cloud Security"
    assert normalized["license"] == "Apache-2.0"
    assert normalized["environment"]["organization"] == "cymbal-investments.org"
    assert normalized["environment"]["paired_baselines"] == ["CYMBAL_BASELINE_NETWORK"]
    assert "telemetry" in normalized
    assert "platforms" in normalized

    # Populated legacy compatibility keys
    assert len(normalized["events"]) == 1
    assert normalized["events"][0]["log_type"] == "BRO_JSON"
    assert normalized["events"][0]["vendor_name"] == "Zeek"
    assert normalized["events"][0]["product_name"] == "Bro"
    assert normalized["events"][0]["ocsf_class_uid"] == 4003
    assert normalized["events"][0]["ocsf_class_name"] == "DNS Activity"

    assert len(normalized["entities"]) == 1
    assert normalized["entities"][0]["log_type"] == "WINDOWS_AD"
    assert normalized["entities"][0]["ocsf_class_uid"] == 5003

    assert normalized["run_frequency"] == {
        "events": "Every 1 day",
        "entities": "Every 1 day (offset 1 day prior)",
    }
    assert normalized["data_rbac"] == "Standard RBAC"

    assert len(normalized["rules"]) == 1
    assert normalized["rules"][0]["name"] == "dns_tunneling_low_reputation_domain"
    assert normalized["rules"][0]["live"] is True
    assert normalized["rules"][0]["alerting"] is True

    assert len(normalized["saved_searches"]) == 1
    assert normalized["saved_searches"][0]["name"] == "High Entropy DNS Queries"

    assert len(normalized["reference_lists"]) == 1
    assert normalized["reference_lists"][0]["name"] == "approved_dns_resolvers"

  def test_normalize_v1_frontmatter_preserves_existing_keys(self):
    v1 = _sample_v1_frontmatter()
    normalized = normalize_frontmatter_for_template(v1)
    assert normalized["title"] == "LEGACY_WORKSHOP"
    assert normalized["events"][0]["log_type"] == "POWERSHELL.log"
    assert normalized["rules"][0]["name"] == "whoami_execution.yaral"
    assert normalized["data_rbac"] == "Must be disabled"


class TestGenerateUsecaseDocRendering:
  """Test documentation rendering for v1 and v2 frontmatter."""

  def test_generate_usecase_doc_v1(self, tmp_path: Path):
    v1 = _sample_v1_frontmatter()
    out_file = tmp_path / "LEGACY_WORKSHOP_generated.md"
    rendered = generate_usecase_doc(v1, TEMPLATE_PATH, out_file)

    assert out_file.is_file()
    assert "# LEGACY_WORKSHOP" in rendered
    assert "Legacy v1 workshop usecase." in rendered
    assert "POWERSHELL.log" in rendered
    assert "No entities configured for this usecase." in rendered
    assert "whoami_execution.yaral" in rendered
    assert "Failed User Logins" in rendered
    assert "key_servers" in rendered

  def test_generate_usecase_doc_v2_renders_ocsf_baselines_and_platforms(
      self, tmp_path: Path
  ):
    v2 = _sample_v2_frontmatter()
    out_file = tmp_path / "DNS_TUNNELING_EXFIL_GTI_generated.md"
    rendered = generate_usecase_doc(v2, TEMPLATE_PATH, out_file)

    assert out_file.is_file()
    assert "# DNS Tunneling Data Exfiltration Telemetry Package" in rendered
    assert "Apache-2.0" in rendered
    assert "Google Cloud Security" in rendered
    assert "2.0.0" in rendered

    # OCSF classes and paired baselines
    assert "DNS Activity" in rendered
    assert "4003" in rendered
    assert "User Inventory" in rendered
    assert "5003" in rendered
    assert "CYMBAL_BASELINE_NETWORK" in rendered

    # Platform bindings
    assert "Google SecOps" in rendered
    assert "Databricks" in rendered
    assert "secops_ocsf.dns_activity" in rendered
    assert "Sigma" in rendered
    assert "RULES/sigma_dns_tunneling.yml" in rendered
    assert "Splunk" in rendered
    assert "zeek:dns:json" in rendered

    # Fallback renderer parity
    normalized = normalize_frontmatter_for_template(v2)
    fallback_rendered = _render_without_jinja2(normalized)
    assert "DNS Activity" in fallback_rendered
    assert "CYMBAL_BASELINE_NETWORK" in fallback_rendered
    assert "Databricks" in fallback_rendered
    assert "Sigma" in fallback_rendered
    assert "Splunk" in fallback_rendered

  def test_process_usecase_directory_and_parse_frontmatter(self, tmp_path: Path):
    uc_dir = tmp_path / "SAMPLE_UC"
    uc_dir.mkdir()
    md_path = uc_dir / "SAMPLE_UC.md"
    md_path.write_text(
        "---\ntitle: SAMPLE_UC\ndescription: Sample description\n---\n\n# Body\n",
        encoding="utf-8",
    )

    fm, body = parse_frontmatter(md_path)
    assert fm["title"] == "SAMPLE_UC"
    assert "# Body" in body

    generated = process_usecase_directory(uc_dir, TEMPLATE_PATH)
    assert generated is not None
    assert "# SAMPLE_UC" in generated
    assert (uc_dir / "SAMPLE_UC_generated.md").is_file()


class TestBuiltinUsecasesStrictV2:
  """Verify built-in logstory usecases are migrated to v2 and pass all 5 gates."""

  @pytest.mark.parametrize(
      "usecase_rel_path",
      [
          "usecases/NETWORK_ANALYSIS",
          "usecases/RULES_SEARCH_WORKSHOP",
          "src/logstory/usecases/NETWORK_ANALYSIS",
          "src/logstory/usecases/RULES_SEARCH_WORKSHOP",
      ],
  )
  def test_builtin_usecase_validates_strict_v2(self, usecase_rel_path: str):
    usecase_dir = REPO_ROOT / usecase_rel_path
    result = validate_usecase_package(usecase_dir, strict_v2=True)
    assert result.is_valid is True, f"Validation failed: {result.findings}"
    assert result.schema_version == "2.0"
    assert result.errors == []
    assert result.warnings == []

  def test_network_analysis_package_contents_and_symlink(self):
    symlink_eval = REPO_ROOT / "src/logstory/usecases/NETWORK_ANALYSIS/eval.yaml"
    assert symlink_eval.is_symlink()
    assert symlink_eval.is_file()

    pkg = parse_usecase_package(REPO_ROOT / "usecases/NETWORK_ANALYSIS", blind=True)
    assert pkg.schema_version == "2.0"
    assert pkg.manifest is not None
    assert pkg.manifest.id == "NETWORK_ANALYSIS"
    assert pkg.solution_markdown_body is None
    assert pkg.eval_data is None

    full_pkg = parse_usecase_package(
        REPO_ROOT / "usecases/NETWORK_ANALYSIS", blind=False
    )
    assert full_pkg.eval_data is not None
    assert full_pkg.eval_data.usecase_id == "NETWORK_ANALYSIS"

  def test_rules_search_workshop_telemetry_and_detections(self):
    pkg = parse_usecase_package(
        REPO_ROOT / "usecases/RULES_SEARCH_WORKSHOP", blind=False
    )
    assert pkg.schema_version == "2.0"
    assert pkg.manifest is not None
    assert pkg.manifest.id == "RULES_SEARCH_WORKSHOP"

    event_paths = [s.path for s in pkg.manifest.telemetry.events]
    assert event_paths == [
        "EVENTS/POWERSHELL.log",
        "EVENTS/WINDOWS_DEFENDER_AV.log",
        "EVENTS/WINDOWS_SYSMON.log",
        "EVENTS/WINEVTLOG.log",
    ]

    entity_paths = [s.path for s in pkg.manifest.telemetry.entities]
    assert entity_paths == ["ENTITIES/WINDOWS_AD.log"]

    secops = pkg.manifest.platforms.google_secops
    assert secops is not None
    rule_paths = [d.path for d in secops.detections if d.path is not None]
    assert sorted(rule_paths) == [
        "RULES/mitre_attack_T1021_002_windows_admin_share_basic.yl2",
        "RULES/rw_mimikatz_T1003.yl2",
        "RULES/win_password_spray.yl2",
        "RULES/win_repeatedAuthFailure_thenSuccess.yl2",
    ]
    assert pkg.eval_data is not None
    assert pkg.eval_data.usecase_id == "RULES_SEARCH_WORKSHOP"

  @pytest.mark.parametrize(
      "usecase_name", ["NETWORK_ANALYSIS", "RULES_SEARCH_WORKSHOP"]
  )
  def test_builtin_usecase_process_directory_generates_docs(
      self, tmp_path: Path, usecase_name: str
  ):
    usecase_dir = REPO_ROOT / "usecases" / usecase_name
    rendered = process_usecase_directory(
        usecase_dir, TEMPLATE_PATH, output_dir=tmp_path
    )
    assert rendered is not None
    assert f"# {usecase_name}" in rendered
    assert "OCSF Class" in rendered
    assert "Platform Bindings" in rendered
    assert (tmp_path / f"{usecase_name}_generated.md").is_file()
