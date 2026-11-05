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

"""5-gate validator and anti-spoiler boundary checker for Logstory usecases."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from logstory.schema.models import (
    SCHEMA_VERSION_V1,
    PairRelationship,
    ScenarioType,
    SchemaValidationError,
    SecurityUsecaseEval,
    SecurityUsecaseManifest,
    _normalize_yaml_scalars,
    split_frontmatter_and_body,
    split_solution_section,
)

GATE_G1_SCHEMA = "G1_SCHEMA"
GATE_G2_INTEGRITY = "G2_INTEGRITY"
GATE_G3_ANTI_SPOILER = "G3_ANTI_SPOILER"
GATE_G4_COUNTERFACTUAL = "G4_COUNTERFACTUAL"
GATE_G5_LEGACY_V1 = "G5_LEGACY_V1"

MIN_SPOILER_TOKEN_LEN = 3

FORBIDDEN_FRONTMATTER_KEYS: frozenset[str] = frozenset({
    "ground_truth",
    "kill_chain",
    "malicious_iocs",
    "compliance_gates",
    "threat_context",
    "compromised_accounts",
    "affected_assets",
    "expected_disposition",
    "expected_verdict",
    "cisa_advisories",
    "patient_zero_host",
    "patient_zero_account",
    "counterfactual_pair",
})

_TRIVIAL_PLACEHOLDERS: frozenset[str] = frozenset({
    "n/a",
    "none",
    "null",
    "tbd",
    "unknown",
})


@dataclass
class ValidationFinding:
  """Single validation finding emitted by one of the 5 verification gates."""

  gate: str
  severity: Literal["ERROR", "WARNING"]
  message: str
  path: str | None = None

  def to_dict(self) -> dict[str, Any]:
    """Serialize ValidationFinding to a plain dictionary."""
    return {
        "gate": self.gate,
        "severity": self.severity,
        "message": self.message,
        "path": self.path,
    }


@dataclass
class UsecaseValidationResult:
  """Structured 5-gate validation outcome for a single usecase package."""

  usecase_id: str
  usecase_dir: Path
  schema_version: str
  findings: list[ValidationFinding] = field(default_factory=list)

  @property
  def is_valid(self) -> bool:
    """Return True when zero ERROR-severity findings were recorded."""
    return not self.errors

  @property
  def errors(self) -> list[ValidationFinding]:
    """Return all ERROR-severity findings."""
    return [f for f in self.findings if f.severity == "ERROR"]

  @property
  def warnings(self) -> list[ValidationFinding]:
    """Return all WARNING-severity findings."""
    return [f for f in self.findings if f.severity == "WARNING"]

  def to_dict(self) -> dict[str, Any]:
    """Serialize UsecaseValidationResult to a JSON-compatible dictionary."""
    return {
        "usecase_id": self.usecase_id,
        "usecase_dir": str(self.usecase_dir),
        "schema_version": self.schema_version,
        "is_valid": self.is_valid,
        "findings": [f.to_dict() for f in self.findings],
        "errors": [f.to_dict() for f in self.errors],
        "warnings": [f.to_dict() for f in self.warnings],
    }


def _check_forbidden_frontmatter_keys(
    data: Any, path: str, findings: list[ValidationFinding]
) -> None:
  """Recursively detect held-out ground-truth keys placed in <USECASE>.md."""
  if isinstance(data, dict):
    for key, value in data.items():
      field_path = f"{path}.{key}" if path else str(key)
      if key in FORBIDDEN_FRONTMATTER_KEYS:
        findings.append(
            ValidationFinding(
                gate=GATE_G3_ANTI_SPOILER,
                severity="ERROR",
                message=(
                    f"Forbidden ground-truth key '{key}' is not permitted in"
                    " <USECASE>.md frontmatter"
                ),
                path=field_path,
            )
        )
      else:
        _check_forbidden_frontmatter_keys(value, field_path, findings)
  elif isinstance(data, list):
    for idx, item in enumerate(data):
      _check_forbidden_frontmatter_keys(item, f"{path}[{idx}]", findings)


def _strip_forbidden_frontmatter_keys(data: dict[str, Any]) -> dict[str, Any]:
  """Return a copy of frontmatter with forbidden ground-truth keys removed."""
  cleaned: dict[str, Any] = {}
  for key, value in data.items():
    if key in FORBIDDEN_FRONTMATTER_KEYS:
      continue
    if isinstance(value, dict):
      cleaned[key] = _strip_forbidden_frontmatter_keys(value)
    else:
      cleaned[key] = value
  return cleaned


def _validate_v1_frontmatter(
    raw_frontmatter: dict[str, Any],
    strict_v2: bool,
    findings: list[ValidationFinding],
) -> None:
  """Run Gate 5 legacy v1 compatibility and basic structure checks."""
  if strict_v2:
    findings.append(
        ValidationFinding(
            gate=GATE_G5_LEGACY_V1,
            severity="ERROR",
            message=(
                "Usecase manifest lacks schema_version '2.0' (legacy v1"
                " frontmatter rejected under strict_v2=True)"
            ),
            path="manifest.schema_version",
        )
    )
    return

  findings.append(
      ValidationFinding(
          gate=GATE_G5_LEGACY_V1,
          severity="WARNING",
          message=(
              "Usecase uses legacy v1 frontmatter; migrate to schema_version"
              " '2.0' and held-out eval.yaml"
          ),
          path="manifest.schema_version",
      )
  )
  for required_v1_key in ("title", "description"):
    val = raw_frontmatter.get(required_v1_key)
    if not isinstance(val, str) or not val.strip():
      findings.append(
          ValidationFinding(
              gate=GATE_G1_SCHEMA,
              severity="ERROR",
              message=f"Legacy v1 frontmatter is missing '{required_v1_key}'",
              path=f"manifest.{required_v1_key}",
          )
      )


def _validate_gate2_integrity(
    resolved_dir: Path,
    manifest: SecurityUsecaseManifest,
    eval_data: SecurityUsecaseEval | None,
    findings: list[ValidationFinding],
) -> None:
  """Run Gate 2 (G2_INTEGRITY) stream ID cross-reference and file path checks."""
  declared_stream_ids: set[str] = set()

  for idx, event_stream in enumerate(manifest.telemetry.events):
    stream_path = f"manifest.telemetry.events[{idx}]"
    if event_stream.stream_id in declared_stream_ids:
      findings.append(
          ValidationFinding(
              gate=GATE_G2_INTEGRITY,
              severity="ERROR",
              message=f"Duplicate telemetry stream_id {event_stream.stream_id!r}",
              path=f"{stream_path}.stream_id",
          )
      )
    declared_stream_ids.add(event_stream.stream_id)
    if not (resolved_dir / event_stream.path).is_file():
      findings.append(
          ValidationFinding(
              gate=GATE_G2_INTEGRITY,
              severity="ERROR",
              message=f"Missing event telemetry file on disk: {event_stream.path}",
              path=f"{stream_path}.path",
          )
      )

  for idx, entity_stream in enumerate(manifest.telemetry.entities):
    stream_path = f"manifest.telemetry.entities[{idx}]"
    if entity_stream.stream_id in declared_stream_ids:
      findings.append(
          ValidationFinding(
              gate=GATE_G2_INTEGRITY,
              severity="ERROR",
              message=f"Duplicate telemetry stream_id {entity_stream.stream_id!r}",
              path=f"{stream_path}.stream_id",
          )
      )
    declared_stream_ids.add(entity_stream.stream_id)
    if not (resolved_dir / entity_stream.path).is_file():
      findings.append(
          ValidationFinding(
              gate=GATE_G2_INTEGRITY,
              severity="ERROR",
              message=f"Missing entity telemetry file on disk: {entity_stream.path}",
              path=f"{stream_path}.path",
          )
      )

  secops = manifest.platforms.google_secops
  if secops is not None:
    for stream_id in secops.log_type_mappings:
      if stream_id not in declared_stream_ids:
        findings.append(
            ValidationFinding(
                gate=GATE_G2_INTEGRITY,
                severity="ERROR",
                message=(
                    "google_secops.log_type_mappings references unknown"
                    f" stream_id {stream_id!r}"
                ),
                path=f"manifest.platforms.google_secops.log_type_mappings.{stream_id}",
            )
        )
    for idx, detection in enumerate(secops.detections):
      if detection.path and not (resolved_dir / detection.path).is_file():
        findings.append(
            ValidationFinding(
                gate=GATE_G2_INTEGRITY,
                severity="ERROR",
                message=f"Missing detection rule file on disk: {detection.path}",
                path=f"manifest.platforms.google_secops.detections[{idx}].path",
            )
        )
    for idx, ext_path in enumerate(secops.parser_extensions):
      if ext_path and not (resolved_dir / ext_path).is_file():
        findings.append(
            ValidationFinding(
                gate=GATE_G2_INTEGRITY,
                severity="ERROR",
                message=f"Missing parser extension file on disk: {ext_path}",
                path=f"manifest.platforms.google_secops.parser_extensions[{idx}]",
            )
        )

  databricks = manifest.platforms.databricks
  if databricks is not None:
    for stream_id in databricks.table_mappings:
      if stream_id not in declared_stream_ids:
        findings.append(
            ValidationFinding(
                gate=GATE_G2_INTEGRITY,
                severity="ERROR",
                message=(
                    "databricks.table_mappings references unknown stream_id"
                    f" {stream_id!r}"
                ),
                path=f"manifest.platforms.databricks.table_mappings.{stream_id}",
            )
        )

  splunk = manifest.platforms.splunk
  if splunk is not None:
    for stream_id in splunk.sourcetypes:
      if stream_id not in declared_stream_ids:
        findings.append(
            ValidationFinding(
                gate=GATE_G2_INTEGRITY,
                severity="ERROR",
                message=(
                    f"splunk.sourcetypes references unknown stream_id {stream_id!r}"
                ),
                path=f"manifest.platforms.splunk.sourcetypes.{stream_id}",
            )
        )

  sigma = manifest.platforms.sigma
  if sigma is not None:
    for idx, rule_path in enumerate(sigma.rules):
      if rule_path and not (resolved_dir / rule_path).is_file():
        findings.append(
            ValidationFinding(
                gate=GATE_G2_INTEGRITY,
                severity="ERROR",
                message=f"Missing Sigma rule file on disk: {rule_path}",
                path=f"manifest.platforms.sigma.rules[{idx}]",
            )
        )

  if eval_data is not None:
    for idx, stage in enumerate(eval_data.ground_truth.kill_chain):
      if stage.stream_id not in declared_stream_ids:
        findings.append(
            ValidationFinding(
                gate=GATE_G2_INTEGRITY,
                severity="ERROR",
                message=(
                    f"kill_chain[{idx}] references unknown stream_id"
                    f" {stage.stream_id!r}"
                ),
                path=f"eval.ground_truth.kill_chain[{idx}].stream_id",
            )
        )
    if eval_data.counterfactual_pair is not None:
      for idx, stream_id in enumerate(
          eval_data.counterfactual_pair.shared_telemetry_streams
      ):
        if stream_id not in declared_stream_ids:
          findings.append(
              ValidationFinding(
                  gate=GATE_G2_INTEGRITY,
                  severity="ERROR",
                  message=(
                      "counterfactual_pair.shared_telemetry_streams references"
                      f" unknown stream_id {stream_id!r}"
                  ),
                  path=f"eval.counterfactual_pair.shared_telemetry_streams[{idx}]",
              )
          )


def _collect_frontmatter_text_surfaces(
    raw_frontmatter: dict[str, Any],
) -> list[tuple[str, str]]:
  """Collect blind-visible frontmatter text surfaces for anti-spoiler scanning."""
  surfaces: list[tuple[str, str]] = []
  for top_key in ("title", "description", "notes"):
    val = raw_frontmatter.get(top_key)
    if isinstance(val, str) and val.strip():
      surfaces.append((f"manifest.{top_key}", val))

  tags = raw_frontmatter.get("tags")
  if isinstance(tags, list):
    for idx, tag in enumerate(tags):
      if isinstance(tag, str) and tag.strip():
        surfaces.append((f"manifest.tags[{idx}]", tag))

  def _walk_notes(node: Any, path: str) -> None:
    if isinstance(node, dict):
      for k, v in node.items():
        subpath = f"{path}.{k}" if path else str(k)
        if k == "notes" and isinstance(v, str) and v.strip():
          surfaces.append((subpath, v))
        else:
          _walk_notes(v, subpath)
    elif isinstance(node, list):
      for idx, item in enumerate(node):
        _walk_notes(item, f"{path}[{idx}]")

  for section_key in ("environment", "telemetry", "platforms"):
    if section_key in raw_frontmatter:
      _walk_notes(raw_frontmatter[section_key], f"manifest.{section_key}")

  return surfaces


def _collect_spoiler_indicators(
    eval_data: SecurityUsecaseEval,
) -> list[tuple[str, str]]:
  """Extract non-trivial IOCs, compromised accounts, and CISA advisories."""
  indicators: list[tuple[str, str]] = []
  entities = eval_data.ground_truth.entities_and_iocs

  for ioc in entities.malicious_iocs:
    candidate = ioc.value.strip()
    if (
        len(candidate) >= MIN_SPOILER_TOKEN_LEN
        and candidate.lower() not in _TRIVIAL_PLACEHOLDERS
    ):
      indicators.append((f"malicious_ioc ({ioc.type})", candidate))

  for account in entities.compromised_accounts:
    candidate = account.strip()
    if (
        len(candidate) >= MIN_SPOILER_TOKEN_LEN
        and candidate.lower() not in _TRIVIAL_PLACEHOLDERS
    ):
      indicators.append(("compromised_account", candidate))

  for advisory in eval_data.threat_context.cisa_advisories:
    candidate = advisory.strip()
    if (
        len(candidate) >= MIN_SPOILER_TOKEN_LEN
        and candidate.lower() not in _TRIVIAL_PLACEHOLDERS
    ):
      indicators.append(("cisa_advisory", candidate))

  return indicators


def _validate_gate3_anti_spoiler(
    raw_frontmatter: dict[str, Any],
    public_markdown_body: str,
    eval_data: SecurityUsecaseEval | None,
    findings: list[ValidationFinding],
) -> None:
  """Run Gate 3 (G3_ANTI_SPOILER) leakage checks against eval.yaml indicators."""
  if eval_data is None:
    return

  indicators = _collect_spoiler_indicators(eval_data)
  if not indicators:
    return

  surfaces = _collect_frontmatter_text_surfaces(raw_frontmatter)
  for surface_path, surface_text in surfaces:
    lower_surface = surface_text.lower()
    for indicator_kind, indicator_value in indicators:
      if indicator_value.lower() in lower_surface:
        findings.append(
            ValidationFinding(
                gate=GATE_G3_ANTI_SPOILER,
                severity="ERROR",
                message=(
                    f"Spoiler {indicator_kind} {indicator_value!r} leaked in"
                    f" frontmatter field '{surface_path}'"
                ),
                path=surface_path,
            )
        )

  if public_markdown_body:
    lower_public_body = public_markdown_body.lower()
    for indicator_kind, indicator_value in indicators:
      if indicator_value.lower() in lower_public_body:
        findings.append(
            ValidationFinding(
                gate=GATE_G3_ANTI_SPOILER,
                severity="ERROR",
                message=(
                    f"Spoiler {indicator_kind} {indicator_value!r} leaked in"
                    " Markdown body above <!-- BEGIN_SOLUTION -->"
                ),
                path="public_markdown_body",
            )
        )


def _validate_gate4_counterfactual(
    manifest: SecurityUsecaseManifest,
    eval_data: SecurityUsecaseEval | None,
    corpus_root: Path | None,
    findings: list[ValidationFinding],
) -> None:
  """Run Gate 4 (G4_COUNTERFACTUAL) counterfactual twin consistency checks."""
  checked_missing_dirs: set[str] = set()

  if eval_data is not None and eval_data.counterfactual_pair is not None:
    pair = eval_data.counterfactual_pair
    paired_id = pair.paired_usecase_id
    is_baseline_scenario = manifest.environment.scenario_type in (
        ScenarioType.BENIGN_BASELINE,
        ScenarioType.BASELINE,
    )
    if (
        pair.pair_relationship == PairRelationship.MALICIOUS_VARIANT_OF_BENIGN_BASELINE
        and not is_baseline_scenario
        and paired_id not in manifest.environment.paired_baselines
    ):
      findings.append(
          ValidationFinding(
              gate=GATE_G4_COUNTERFACTUAL,
              severity="ERROR",
              message=(
                  f"Counterfactual paired baseline {paired_id!r} in eval.yaml"
                  " is not listed in manifest environment.paired_baselines"
              ),
              path="manifest.environment.paired_baselines",
          )
      )

    if corpus_root is not None and not (Path(corpus_root) / paired_id).is_dir():
      checked_missing_dirs.add(paired_id)
      findings.append(
          ValidationFinding(
              gate=GATE_G4_COUNTERFACTUAL,
              severity="ERROR",
              message=(
                  "Counterfactual paired usecase directory does not exist in"
                  f" corpus_root: {paired_id}"
              ),
              path="eval.counterfactual_pair.paired_usecase_id",
          )
      )

  if corpus_root is not None:
    for idx, baseline_id in enumerate(manifest.environment.paired_baselines):
      if baseline_id in checked_missing_dirs:
        continue
      if not (Path(corpus_root) / baseline_id).is_dir():
        checked_missing_dirs.add(baseline_id)
        findings.append(
            ValidationFinding(
                gate=GATE_G4_COUNTERFACTUAL,
                severity="ERROR",
                message=(
                    "Paired baseline directory does not exist in corpus_root:"
                    f" {baseline_id}"
                ),
                path=f"manifest.environment.paired_baselines[{idx}]",
            )
        )


def validate_usecase_package(
    usecase_dir: Path,
    strict_v2: bool = False,
    corpus_root: Path | None = None,
) -> UsecaseValidationResult:
  """Execute the 5-gate validation pipeline on a single usecase directory.

  Args:
    usecase_dir: Path to `<USECASE>` directory.
    strict_v2: When True, rejects legacy v1 packages and requires `eval.yaml`.
    corpus_root: Optional path to the parent corpus root directory for verifying
      that paired counterfactual baseline directories exist on disk.

  Returns:
    Populated `UsecaseValidationResult` containing all errors and warnings.
  """
  resolved_dir = Path(usecase_dir)
  usecase_id = resolved_dir.name
  findings: list[ValidationFinding] = []

  md_path = resolved_dir / f"{usecase_id}.md"
  if not md_path.is_file():
    findings.append(
        ValidationFinding(
            gate=GATE_G1_SCHEMA,
            severity="ERROR",
            message=f"Missing required usecase manifest file: {md_path}",
            path=str(md_path),
        )
    )
    return UsecaseValidationResult(
        usecase_id=usecase_id,
        usecase_dir=resolved_dir,
        schema_version="unknown",
        findings=findings,
    )

  try:
    raw_frontmatter, markdown_body = split_frontmatter_and_body(
        md_path.read_text(encoding="utf-8")
    )
  except SchemaValidationError as exc:
    findings.append(
        ValidationFinding(
            gate=GATE_G1_SCHEMA,
            severity="ERROR",
            message=exc.reason,
            path=exc.path or "frontmatter",
        )
    )
    return UsecaseValidationResult(
        usecase_id=usecase_id,
        usecase_dir=resolved_dir,
        schema_version="unknown",
        findings=findings,
    )

  public_markdown_body, _ = split_solution_section(markdown_body)
  _check_forbidden_frontmatter_keys(raw_frontmatter, "manifest", findings)

  has_schema_version = (
      "schema_version" in raw_frontmatter
      and raw_frontmatter["schema_version"] is not None
  )
  raw_version = (
      str(raw_frontmatter["schema_version"])
      if has_schema_version
      else SCHEMA_VERSION_V1
  )

  if not has_schema_version or raw_version == SCHEMA_VERSION_V1:
    _validate_v1_frontmatter(raw_frontmatter, strict_v2, findings)
    return UsecaseValidationResult(
        usecase_id=usecase_id,
        usecase_dir=resolved_dir,
        schema_version=SCHEMA_VERSION_V1,
        findings=findings,
    )

  cleaned_frontmatter = _strip_forbidden_frontmatter_keys(raw_frontmatter)
  manifest: SecurityUsecaseManifest | None = None
  try:
    manifest = SecurityUsecaseManifest.from_dict(cleaned_frontmatter, path="manifest")
    if manifest.id != usecase_id:
      findings.append(
          ValidationFinding(
              gate=GATE_G1_SCHEMA,
              severity="ERROR",
              message=(
                  f"Manifest id {manifest.id!r} does not match directory name"
                  f" {usecase_id!r}"
              ),
              path="manifest.id",
          )
      )
  except SchemaValidationError as exc:
    findings.append(
        ValidationFinding(
            gate=GATE_G1_SCHEMA,
            severity="ERROR",
            message=exc.reason,
            path=exc.path or "manifest",
        )
    )

  eval_data: SecurityUsecaseEval | None = None
  eval_path = resolved_dir / "eval.yaml"
  if eval_path.is_file():
    try:
      loaded_eval = yaml.safe_load(eval_path.read_text(encoding="utf-8"))
      eval_data = SecurityUsecaseEval.from_dict(
          _normalize_yaml_scalars(loaded_eval), path="eval"
      )
      if eval_data.usecase_id != usecase_id:
        findings.append(
            ValidationFinding(
                gate=GATE_G1_SCHEMA,
                severity="ERROR",
                message=(
                    f"eval.yaml usecase_id {eval_data.usecase_id!r} does not"
                    f" match directory name {usecase_id!r}"
                ),
                path="eval.usecase_id",
            )
        )
    except yaml.YAMLError as exc:
      findings.append(
          ValidationFinding(
              gate=GATE_G1_SCHEMA,
              severity="ERROR",
              message=f"Invalid YAML syntax in eval.yaml: {exc}",
              path="eval.yaml",
          )
      )
    except SchemaValidationError as exc:
      findings.append(
          ValidationFinding(
              gate=GATE_G1_SCHEMA,
              severity="ERROR",
              message=exc.reason,
              path=exc.path or "eval",
          )
      )
  else:
    findings.append(
        ValidationFinding(
            gate=GATE_G1_SCHEMA,
            severity="ERROR" if strict_v2 else "WARNING",
            message="Missing eval.yaml for v2 usecase package",
            path="eval.yaml",
        )
    )

  if manifest is not None:
    _validate_gate2_integrity(resolved_dir, manifest, eval_data, findings)

  _validate_gate3_anti_spoiler(
      raw_frontmatter, public_markdown_body, eval_data, findings
  )

  if manifest is not None:
    _validate_gate4_counterfactual(manifest, eval_data, corpus_root, findings)

  return UsecaseValidationResult(
      usecase_id=usecase_id,
      usecase_dir=resolved_dir,
      schema_version=raw_version,
      findings=findings,
  )


def validate_usecase_corpus(
    corpus_dir: Path, strict_v2: bool = False
) -> list[UsecaseValidationResult]:
  """Discover and validate all usecase directories under `corpus_dir`.

  Args:
    corpus_dir: Root directory containing multiple `<USECASE>/` subdirectories,
      or a single `<USECASE>/` directory.
    strict_v2: When True, requires `schema_version: "2.0"` and `eval.yaml` for
      every discovered usecase package.

  Returns:
    List of `UsecaseValidationResult` objects sorted by `usecase_id`.
  """
  resolved_corpus = Path(corpus_dir)
  if (resolved_corpus / f"{resolved_corpus.name}.md").is_file():
    return [
        validate_usecase_package(
            resolved_corpus,
            strict_v2=strict_v2,
            corpus_root=resolved_corpus.parent,
        )
    ]

  usecase_dirs: list[Path] = []
  for child in sorted(resolved_corpus.iterdir(), key=lambda p: p.name):
    if not child.is_dir() or child.name.startswith("."):
      continue
    if (
        (child / f"{child.name}.md").is_file()
        or (child / "eval.yaml").is_file()
        or (child / "EVENTS").is_dir()
    ):
      usecase_dirs.append(child)

  return [
      validate_usecase_package(uc_dir, strict_v2=strict_v2, corpus_root=resolved_corpus)
      for uc_dir in usecase_dirs
  ]
