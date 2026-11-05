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

"""Full 47-scenario corpus validation tests for logstory_usecases v2 migration."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from logstory.schema import (
    build_eval_json_schema,
    build_usecase_json_schema,
    parse_usecase_package,
    validate_usecase_corpus,
)

EXPECTED_USECASE_COUNT = 47
EXPECTED_ATTACK_COUNT = 43
EXPECTED_BASELINE_IDS = frozenset({
    "CYMBAL_BASELINE_CLOUD",
    "CYMBAL_BASELINE_ENDPOINT",
    "CYMBAL_BASELINE_IDENTITY",
    "CYMBAL_BASELINE_NETWORK",
})

_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001f9ff\U0001fa00-\U0001faff\u2600-\u26ff\u2700-\u27bf]"
)


def _resolve_usecases_corpus_dir() -> Path | None:
  """Locate the logstory_usecases worktree directory if mounted locally."""
  env_override = os.environ.get("LOGSTORY_USECASES_DIR", "").strip()
  if env_override:
    env_path = Path(env_override)
    if env_path.is_dir():
      return env_path

  repo_root = Path(__file__).resolve().parent.parent
  projects_dir = repo_root.parent.parent
  candidates = [
      projects_dir / "logstory_usecases__worktrees" / "schema__usecase-metadata-v2",
      projects_dir / "logstory_usecases__worktrees" / "main",
      projects_dir / "logstory_usecases",
  ]
  for candidate in candidates:
    if candidate.is_dir() and (candidate / "AKIRA_RANSOMWARE").is_dir():
      return candidate
  return None


@pytest.fixture(scope="module", name="corpus_dir")
def fixture_corpus_dir() -> Path:
  """Return the mounted logstory_usecases corpus directory or skip cleanly."""
  resolved = _resolve_usecases_corpus_dir()
  if resolved is None:
    pytest.skip("logstory_usecases repository is not mounted locally")
  return resolved


class TestLogstoryUsecasesCorpusV2:
  """Validate all 47 scenarios in logstory_usecases against v2 5-gate checks."""

  def test_all_47_usecases_pass_strict_v2_validation(self, corpus_dir: Path):
    results = validate_usecase_corpus(corpus_dir, strict_v2=True)
    assert len(results) == EXPECTED_USECASE_COUNT

    failures = {
        r.usecase_id: [f.to_dict() for f in r.findings]
        for r in results
        if not r.is_valid or r.warnings
    }
    assert failures == {}, f"Corpus validation findings: {failures}"
    assert all(r.schema_version == "2.0" for r in results)

  def test_synchronized_json_schemas_exist_in_corpus(self, corpus_dir: Path):
    usecase_schema_path = corpus_dir / "schemas" / "usecase.schema.json"
    eval_schema_path = corpus_dir / "schemas" / "eval.schema.json"
    assert usecase_schema_path.is_file()
    assert eval_schema_path.is_file()

    assert (
        json.loads(usecase_schema_path.read_text(encoding="utf-8"))
        == build_usecase_json_schema()
    )
    assert (
        json.loads(eval_schema_path.read_text(encoding="utf-8"))
        == build_eval_json_schema()
    )

  def test_blind_and_full_parsing_and_ocsf_mappings_across_corpus(
      self, corpus_dir: Path
  ):
    results = validate_usecase_corpus(corpus_dir, strict_v2=True)
    assert len(results) == EXPECTED_USECASE_COUNT

    attack_count = 0
    baseline_ids: set[str] = set()

    for res in results:
      uc_dir = res.usecase_dir
      blind_pkg = parse_usecase_package(uc_dir, blind=True)
      assert blind_pkg.schema_version == "2.0"
      assert blind_pkg.manifest is not None
      assert blind_pkg.eval_data is None
      assert blind_pkg.solution_markdown_body is None
      assert f"# {res.usecase_id}" in blind_pkg.public_markdown_body
      assert "## Overview" in blind_pkg.public_markdown_body
      assert "## Telemetry Streams" in blind_pkg.public_markdown_body
      assert "## Replay Instructions" in blind_pkg.public_markdown_body

      full_pkg = parse_usecase_package(uc_dir, blind=False)
      assert full_pkg.eval_data is not None
      assert full_pkg.solution_markdown_body is not None

      manifest = full_pkg.manifest
      assert manifest is not None
      eval_data = full_pkg.eval_data

      all_streams = list(manifest.telemetry.events) + list(manifest.telemetry.entities)
      assert len(all_streams) >= 1
      secops = manifest.platforms.google_secops
      databricks = manifest.platforms.databricks
      assert secops is not None
      assert databricks is not None

      for stream in all_streams:
        assert stream.ocsf_category_uid is not None
        assert stream.ocsf_class_uid is not None
        assert stream.ocsf_class_name
        assert stream.stream_id in secops.log_type_mappings
        assert stream.stream_id in databricks.table_mappings
        assert databricks.table_mappings[stream.stream_id].startswith("secops_ocsf.")

      if res.usecase_id in EXPECTED_BASELINE_IDS:
        baseline_ids.add(res.usecase_id)
        assert manifest.environment.scenario_type.value == "benign_baseline"
        assert eval_data.ground_truth.expected_verdict.value == "BENIGN"
        assert eval_data.ground_truth.expected_disposition.value == "BENIGN_POSITIVE"
        assert eval_data.counterfactual_pair is not None
      else:
        attack_count += 1
        assert manifest.environment.scenario_type.value == "attack"
        assert eval_data.ground_truth.expected_verdict.value == "MALICIOUS"
        assert eval_data.ground_truth.expected_disposition.value == "TRUE_POSITIVE"
        assert len(eval_data.ground_truth.kill_chain) >= 1

      md_text = (uc_dir / f"{res.usecase_id}.md").read_text(encoding="utf-8")
      eval_text = (uc_dir / "eval.yaml").read_text(encoding="utf-8")
      assert not _EMOJI_RE.search(md_text), f"Emoji found in {res.usecase_id}.md"
      assert not _EMOJI_RE.search(
          eval_text
      ), f"Emoji found in {res.usecase_id}/eval.yaml"

    assert attack_count == EXPECTED_ATTACK_COUNT
    assert baseline_ids == EXPECTED_BASELINE_IDS
