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

"""Core v2 schema models, package parser, and Draft 2020-12 JSON Schema exporter."""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeVar

import yaml

SCHEMA_VERSION_V1 = "1.0"
SCHEMA_VERSION_V2 = "2.0"
SOLUTION_DELIMITER = "<!-- BEGIN_SOLUTION -->"
JSON_SCHEMA_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
USECASE_ID_PATTERN = r"^[A-Z0-9_]+$"
ISO_DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
MIN_FRONTMATTER_PARTS = 3
DEFAULT_TRIAGE_HORIZON_HOURS = 72
DEFAULT_HUNT_HORIZON_HOURS = 168

_USECASE_ID_RE = re.compile(USECASE_ID_PATTERN)
_ISO_DATE_RE = re.compile(ISO_DATE_PATTERN)

E = TypeVar("E", bound=StrEnum)


class SchemaValidationError(ValueError):
  """Raised when usecase manifest or eval metadata violates the v2 schema."""

  def __init__(self, message: str, path: str | None = None) -> None:
    """Initialize SchemaValidationError with an optional field path.

    Args:
      message: Human-readable validation failure description.
      path: Dotted field path where validation failed.
    """
    self.path = path
    self.reason = message
    full_message = f"{path}: {message}" if path else message
    super().__init__(full_message)


class ScenarioType(StrEnum):
  """High-level scenario classification for a usecase package."""

  ATTACK = "attack"
  BENIGN_BASELINE = "benign_baseline"
  BASELINE = "baseline"
  HYBRID = "hybrid"
  WORKSHOP = "workshop"


class GroundingTier(StrEnum):
  """Real-world threat intelligence grounding tier for a scenario."""

  STIX_GROUNDED = "stix_grounded"
  TRADECRAFT_MODELED = "tradecraft_modeled"
  BEHAVIORAL_SYNTHETIC = "behavioral_synthetic"
  BENIGN_BASELINE = "benign_baseline"


class ExpectedDisposition(StrEnum):
  """Canonical SOC 4-way (+ inconclusive) case triage disposition."""

  TRUE_POSITIVE = "TRUE_POSITIVE"
  BENIGN_POSITIVE = "BENIGN_POSITIVE"
  FALSE_POSITIVE = "FALSE_POSITIVE"
  SUSPICIOUS_TRUE_POSITIVE = "SUSPICIOUS_TRUE_POSITIVE"
  INCONCLUSIVE = "INCONCLUSIVE"


class ExpectedVerdict(StrEnum):
  """High-level threat verdict for evaluation scoring."""

  MALICIOUS = "MALICIOUS"
  BENIGN = "BENIGN"
  SUSPICIOUS = "SUSPICIOUS"
  INCONCLUSIVE = "INCONCLUSIVE"


class CriticalityTier(StrEnum):
  """Enterprise asset criticality tier for blast-radius evaluation."""

  TIER_0 = "TIER_0"
  TIER_1 = "TIER_1"
  TIER_2 = "TIER_2"
  TIER_3 = "TIER_3"
  TIER_0_CROWN_JEWEL = "tier_0_crown_jewel"
  TIER_1_CORE_INFRA = "tier_1_core_infra"
  TIER_2_WORKSTATION = "tier_2_workstation"
  CRITICAL = "critical"
  HIGH = "high"
  MEDIUM = "medium"
  LOW = "low"


class PairRelationship(StrEnum):
  """Signal Detection Theory relationship between counterfactual twin usecases."""

  MALICIOUS_VARIANT_OF_BENIGN_BASELINE = "malicious_variant_of_benign_baseline"
  BENIGN_BASELINE_FOR_MALICIOUS_VARIANT = "benign_baseline_for_malicious_variant"
  CONFUSABLE_TWIN = "confusable_twin"
  BENIGN_TWIN = "benign_twin"
  ATTACK_TWIN = "attack_twin"


class DifficultyTier(StrEnum):
  """Progression difficulty tier for Blue Team evaluation tasks."""

  BEGINNER = "beginner"
  INTERMEDIATE = "intermediate"
  ADVANCED = "advanced"
  EXPERT = "expert"
  TIER_1 = "tier_1"
  TIER_2 = "tier_2"
  TIER_3 = "tier_3"
  TIER_4 = "tier_4"
  TIER_5 = "tier_5"


def _normalize_yaml_scalars(value: Any) -> Any:
  """Recursively normalize YAML date/datetime scalars into ISO strings."""
  if isinstance(value, datetime.datetime):
    return value.isoformat()
  if isinstance(value, datetime.date):
    return value.isoformat()
  if isinstance(value, dict):
    return {str(k): _normalize_yaml_scalars(v) for k, v in value.items()}
  if isinstance(value, list):
    return [_normalize_yaml_scalars(item) for item in value]
  return value


def _ensure_mapping(data: Any, path: str) -> dict[str, Any]:
  """Verify that data is a dict and return a normalized shallow copy."""
  if not isinstance(data, dict):
    raise SchemaValidationError(
        f"Expected mapping/object, got {type(data).__name__}", path=path
    )
  return dict(data)


def _reject_unknown_keys(data: dict[str, Any], allowed: set[str], path: str) -> None:
  """Raise SchemaValidationError if any keys in data are outside allowed."""
  unknown = sorted(set(data.keys()) - allowed)
  if unknown:
    joined = ", ".join(unknown)
    raise SchemaValidationError(f"Unknown field(s): {joined}", path=path)


def _require_non_empty_str(data: dict[str, Any], key: str, path: str) -> str:
  """Extract a required non-empty string field from data."""
  field_path = f"{path}.{key}" if path else key
  if key not in data or data[key] is None:
    raise SchemaValidationError(f"Missing required field '{key}'", path=field_path)
  val = data[key]
  if isinstance(val, (datetime.date, datetime.datetime)):
    val = val.isoformat()
  if not isinstance(val, str) or not val.strip():
    raise SchemaValidationError(
        f"Field '{key}' must be a non-empty string", path=field_path
    )
  return val


def _optional_str(
    data: dict[str, Any],
    key: str,
    path: str,
    default: str | None = None,
) -> str | None:
  """Extract an optional string field from data."""
  field_path = f"{path}.{key}" if path else key
  if key not in data or data[key] is None:
    return default
  val = data[key]
  if isinstance(val, (datetime.date, datetime.datetime)):
    val = val.isoformat()
  if not isinstance(val, str):
    raise SchemaValidationError(f"Field '{key}' must be a string", path=field_path)
  return val


def _optional_bool(
    data: dict[str, Any], key: str, path: str, default: bool = False
) -> bool:
  """Extract an optional boolean field from data."""
  field_path = f"{path}.{key}" if path else key
  if key not in data or data[key] is None:
    return default
  val = data[key]
  if not isinstance(val, bool):
    raise SchemaValidationError(f"Field '{key}' must be a boolean", path=field_path)
  return val


def _optional_int(
    data: dict[str, Any],
    key: str,
    path: str,
    default: int | None = None,
) -> int | None:
  """Extract an optional integer field from data."""
  field_path = f"{path}.{key}" if path else key
  if key not in data or data[key] is None:
    return default
  val = data[key]
  if isinstance(val, bool) or not isinstance(val, int):
    raise SchemaValidationError(f"Field '{key}' must be an integer", path=field_path)
  return val


def _optional_float(
    data: dict[str, Any], key: str, path: str, default: float = 0.0
) -> float:
  """Extract an optional numeric field as float."""
  field_path = f"{path}.{key}" if path else key
  if key not in data or data[key] is None:
    return default
  val = data[key]
  if isinstance(val, bool) or not isinstance(val, (int, float)):
    raise SchemaValidationError(f"Field '{key}' must be a number", path=field_path)
  return float(val)


def _str_list(
    data: dict[str, Any],
    key: str,
    path: str,
    required: bool = False,
) -> list[str]:
  """Extract a list of strings from data."""
  field_path = f"{path}.{key}" if path else key
  if key not in data or data[key] is None:
    if required:
      raise SchemaValidationError(f"Missing required field '{key}'", path=field_path)
    return []
  val = data[key]
  if not isinstance(val, list) or not all(isinstance(item, str) for item in val):
    raise SchemaValidationError(
        f"Field '{key}' must be a list of strings", path=field_path
    )
  return list(val)


def _str_dict(data: dict[str, Any], key: str, path: str) -> dict[str, str]:
  """Extract a dict[str, str] mapping from data."""
  field_path = f"{path}.{key}" if path else key
  if key not in data or data[key] is None:
    return {}
  val = data[key]
  if not isinstance(val, dict) or not all(
      isinstance(k, str) and isinstance(v, str) for k, v in val.items()
  ):
    raise SchemaValidationError(
        f"Field '{key}' must be a mapping of string keys to string values",
        path=field_path,
    )
  return dict(val)


def _parse_enum(value: Any, enum_cls: type[E], path: str) -> E:
  """Convert a raw value into an Enum member or raise SchemaValidationError."""
  if isinstance(value, enum_cls):
    return value
  if (
      isinstance(value, int)
      and not isinstance(value, bool)
      and enum_cls is DifficultyTier
  ):
    tier_key = f"tier_{value}"
    for member in enum_cls:
      if member.value == tier_key:
        return member
  if isinstance(value, str):
    for member in enum_cls:
      if member.value == value:
        return member
  allowed = ", ".join(m.value for m in enum_cls)
  raise SchemaValidationError(
      f"Invalid value {value!r}; expected one of: {allowed}", path=path
  )


@dataclass
class TimestampPolicy:
  """Replay timestamp adjustment policy for a usecase."""

  base_date: str = "2025-08-04"
  preserve_relative_offsets: bool = True
  default_delta: str = "1d"
  entity_offset_days: int = 1
  window_start: str | None = None
  window_end: str | None = None

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "environment.timestamp_policy"
  ) -> TimestampPolicy:
    """Validate and construct a TimestampPolicy from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "base_date",
            "preserve_relative_offsets",
            "default_delta",
            "entity_offset_days",
            "window_start",
            "window_end",
        },
        path,
    )
    base_date = (
        _optional_str(mapping, "base_date", path, default="2025-08-04") or "2025-08-04"
    )
    preserve_offsets = _optional_bool(
        mapping, "preserve_relative_offsets", path, default=True
    )
    default_delta = _optional_str(mapping, "default_delta", path, default="1d") or "1d"
    entity_offset = _optional_int(mapping, "entity_offset_days", path, default=1)
    return cls(
        base_date=base_date,
        preserve_relative_offsets=preserve_offsets,
        default_delta=default_delta,
        entity_offset_days=1 if entity_offset is None else entity_offset,
        window_start=_optional_str(mapping, "window_start", path),
        window_end=_optional_str(mapping, "window_end", path),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize TimestampPolicy to a plain dictionary."""
    result: dict[str, Any] = {
        "base_date": self.base_date,
        "preserve_relative_offsets": self.preserve_relative_offsets,
        "default_delta": self.default_delta,
        "entity_offset_days": self.entity_offset_days,
    }
    if self.window_start is not None:
      result["window_start"] = self.window_start
    if self.window_end is not None:
      result["window_end"] = self.window_end
    return result


@dataclass
class EnvironmentContext:
  """Enterprise environment context, scenario type, and paired baselines."""

  organization: str = "cymbal-investments.org"
  scenario_type: ScenarioType = ScenarioType.ATTACK
  paired_baselines: list[str] = field(default_factory=list)
  timestamp_policy: TimestampPolicy = field(default_factory=TimestampPolicy)
  notes: str = ""

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "environment"
  ) -> EnvironmentContext:
    """Validate and construct an EnvironmentContext from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "organization",
            "scenario_type",
            "paired_baselines",
            "timestamp_policy",
            "notes",
        },
        path,
    )
    org = (
        _optional_str(mapping, "organization", path, default="cymbal-investments.org")
        or "cymbal-investments.org"
    )
    raw_scenario_type = mapping.get("scenario_type", ScenarioType.ATTACK.value)
    scenario_type = _parse_enum(
        raw_scenario_type, ScenarioType, f"{path}.scenario_type"
    )
    paired_baselines = _str_list(mapping, "paired_baselines", path)
    raw_ts_policy = mapping.get("timestamp_policy")
    ts_policy = (
        TimestampPolicy.from_dict(raw_ts_policy, f"{path}.timestamp_policy")
        if raw_ts_policy is not None
        else TimestampPolicy()
    )
    notes = _optional_str(mapping, "notes", path, default="") or ""
    return cls(
        organization=org,
        scenario_type=scenario_type,
        paired_baselines=paired_baselines,
        timestamp_policy=ts_policy,
        notes=notes,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize EnvironmentContext to a plain dictionary."""
    result: dict[str, Any] = {
        "organization": self.organization,
        "scenario_type": self.scenario_type.value,
        "paired_baselines": list(self.paired_baselines),
        "timestamp_policy": self.timestamp_policy.to_dict(),
    }
    if self.notes:
      result["notes"] = self.notes
    return result


@dataclass
class TelemetryStream:
  """Vendor-neutral event or entity telemetry stream with OCSF alignment."""

  stream_id: str
  path: str
  log_type: str
  vendor_name: str = ""
  product_name: str = ""
  ocsf_category_uid: int | None = None
  ocsf_class_uid: int | None = None
  ocsf_class_name: str | None = None
  notes: str = ""

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "telemetry.stream"
  ) -> TelemetryStream:
    """Validate and construct a TelemetryStream from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "stream_id",
            "path",
            "log_type",
            "vendor_name",
            "product_name",
            "ocsf_category_uid",
            "ocsf_class_uid",
            "ocsf_class_name",
            "notes",
        },
        path,
    )
    stream_id = _require_non_empty_str(mapping, "stream_id", path)
    rel_path = _require_non_empty_str(mapping, "path", path)
    log_type = (
        _optional_str(mapping, "log_type", path, default=Path(rel_path).stem)
        or Path(rel_path).stem
    )
    vendor_name = _optional_str(mapping, "vendor_name", path, default="") or ""
    product_name = _optional_str(mapping, "product_name", path, default="") or ""
    ocsf_category_uid = _optional_int(mapping, "ocsf_category_uid", path)
    ocsf_class_uid = _optional_int(mapping, "ocsf_class_uid", path)
    ocsf_class_name = _optional_str(mapping, "ocsf_class_name", path)
    notes = _optional_str(mapping, "notes", path, default="") or ""
    return cls(
        stream_id=stream_id,
        path=rel_path,
        log_type=log_type,
        vendor_name=vendor_name,
        product_name=product_name,
        ocsf_category_uid=ocsf_category_uid,
        ocsf_class_uid=ocsf_class_uid,
        ocsf_class_name=ocsf_class_name,
        notes=notes,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize TelemetryStream to a plain dictionary."""
    result: dict[str, Any] = {
        "stream_id": self.stream_id,
        "path": self.path,
        "log_type": self.log_type,
        "vendor_name": self.vendor_name,
        "product_name": self.product_name,
    }
    if self.ocsf_category_uid is not None:
      result["ocsf_category_uid"] = self.ocsf_category_uid
    if self.ocsf_class_uid is not None:
      result["ocsf_class_uid"] = self.ocsf_class_uid
    if self.ocsf_class_name is not None:
      result["ocsf_class_name"] = self.ocsf_class_name
    result["notes"] = self.notes
    return result


@dataclass
class TelemetrySection:
  """Container for event and entity telemetry streams in a usecase."""

  events: list[TelemetryStream] = field(default_factory=list)
  entities: list[TelemetryStream] = field(default_factory=list)

  @classmethod
  def from_dict(cls, data: dict[str, Any], path: str = "telemetry") -> TelemetrySection:
    """Validate and construct a TelemetrySection from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"events", "entities"}, path)

    raw_events = mapping.get("events", [])
    if not isinstance(raw_events, list):
      raise SchemaValidationError(
          "Field 'events' must be a list", path=f"{path}.events"
      )
    events = [
        TelemetryStream.from_dict(item, f"{path}.events[{idx}]")
        for idx, item in enumerate(raw_events)
    ]

    raw_entities = mapping.get("entities", [])
    if raw_entities is None:
      raw_entities = []
    if not isinstance(raw_entities, list):
      raise SchemaValidationError(
          "Field 'entities' must be a list", path=f"{path}.entities"
      )
    entities = [
        TelemetryStream.from_dict(item, f"{path}.entities[{idx}]")
        for idx, item in enumerate(raw_entities)
    ]
    return cls(events=events, entities=entities)

  def to_dict(self) -> dict[str, Any]:
    """Serialize TelemetrySection to a plain dictionary."""
    return {
        "events": [stream.to_dict() for stream in self.events],
        "entities": [stream.to_dict() for stream in self.entities],
    }


@dataclass
class GoogleSecOpsRunFrequency:
  """Recommended replay schedule for Google Security Operations."""

  events: str = "Every 1 day"
  entities: str | None = None

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "platforms.google_secops.run_frequency",
  ) -> GoogleSecOpsRunFrequency:
    """Validate and construct GoogleSecOpsRunFrequency from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"events", "entities"}, path)
    events = _require_non_empty_str(mapping, "events", path)
    entities = _optional_str(mapping, "entities", path)
    return cls(events=events, entities=entities)

  def to_dict(self) -> dict[str, Any]:
    """Serialize GoogleSecOpsRunFrequency to a plain dictionary."""
    result: dict[str, Any] = {"events": self.events}
    if self.entities is not None:
      result["entities"] = self.entities
    return result


@dataclass
class GoogleSecOpsDetection:
  """YARA-L 2.0 detection rule metadata for Google Security Operations."""

  name: str
  path: str | None = None
  live: bool = False
  alerting: bool = False
  notes: str = ""

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "platforms.google_secops.detections",
  ) -> GoogleSecOpsDetection:
    """Validate and construct GoogleSecOpsDetection from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"name", "path", "live", "alerting", "notes"}, path)
    name = _require_non_empty_str(mapping, "name", path)
    rule_path = _optional_str(mapping, "path", path)
    live = _optional_bool(mapping, "live", path, default=False)
    alerting = _optional_bool(mapping, "alerting", path, default=False)
    notes = _optional_str(mapping, "notes", path, default="") or ""
    return cls(
        name=name,
        path=rule_path,
        live=live,
        alerting=alerting,
        notes=notes,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize GoogleSecOpsDetection to a plain dictionary."""
    return {
        "name": self.name,
        "path": self.path,
        "live": self.live,
        "alerting": self.alerting,
        "notes": self.notes,
    }


@dataclass
class GoogleSecOpsSavedSearch:
  """Saved UDM search metadata for Google Security Operations."""

  name: str
  creator: str = ""
  notes: str = ""
  query: str | None = None

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "platforms.google_secops.saved_searches",
  ) -> GoogleSecOpsSavedSearch:
    """Validate and construct GoogleSecOpsSavedSearch from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"name", "creator", "notes", "query"}, path)
    name = _require_non_empty_str(mapping, "name", path)
    creator = _optional_str(mapping, "creator", path, default="") or ""
    notes = _optional_str(mapping, "notes", path, default="") or ""
    query = _optional_str(mapping, "query", path)
    return cls(name=name, creator=creator, notes=notes, query=query)

  def to_dict(self) -> dict[str, Any]:
    """Serialize GoogleSecOpsSavedSearch to a plain dictionary."""
    result: dict[str, Any] = {
        "name": self.name,
        "creator": self.creator,
        "notes": self.notes,
    }
    if self.query is not None:
      result["query"] = self.query
    return result


@dataclass
class GoogleSecOpsReferenceList:
  """Reference list metadata for Google Security Operations."""

  name: str
  type: str = "String"
  notes: str = ""

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "platforms.google_secops.reference_lists",
  ) -> GoogleSecOpsReferenceList:
    """Validate and construct GoogleSecOpsReferenceList from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"name", "type", "notes"}, path)
    name = _require_non_empty_str(mapping, "name", path)
    list_type = _optional_str(mapping, "type", path, default="String") or "String"
    notes = _optional_str(mapping, "notes", path, default="") or ""
    return cls(name=name, type=list_type, notes=notes)

  def to_dict(self) -> dict[str, Any]:
    """Serialize GoogleSecOpsReferenceList to a plain dictionary."""
    return {
        "name": self.name,
        "type": self.type,
        "notes": self.notes,
    }


@dataclass
class GoogleSecOpsPlatform:
  """Platform bindings for Google Security Operations (UDM and YARA-L 2.0)."""

  run_frequency: GoogleSecOpsRunFrequency | None = None
  data_rbac: str | None = None
  log_type_mappings: dict[str, str] = field(default_factory=dict)
  detections: list[GoogleSecOpsDetection] = field(default_factory=list)
  saved_searches: list[GoogleSecOpsSavedSearch] = field(default_factory=list)
  reference_lists: list[GoogleSecOpsReferenceList] = field(default_factory=list)
  parser_extensions: list[str] = field(default_factory=list)

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "platforms.google_secops"
  ) -> GoogleSecOpsPlatform:
    """Validate and construct GoogleSecOpsPlatform from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "run_frequency",
            "data_rbac",
            "log_type_mappings",
            "detections",
            "saved_searches",
            "reference_lists",
            "parser_extensions",
        },
        path,
    )
    raw_freq = mapping.get("run_frequency")
    run_frequency = (
        GoogleSecOpsRunFrequency.from_dict(raw_freq, f"{path}.run_frequency")
        if raw_freq is not None
        else None
    )
    data_rbac = _optional_str(mapping, "data_rbac", path)
    log_type_mappings = _str_dict(mapping, "log_type_mappings", path)

    raw_detections = mapping.get("detections", []) or []
    if not isinstance(raw_detections, list):
      raise SchemaValidationError(
          "Field 'detections' must be a list", path=f"{path}.detections"
      )
    detections = [
        GoogleSecOpsDetection.from_dict(item, f"{path}.detections[{idx}]")
        for idx, item in enumerate(raw_detections)
    ]

    raw_searches = mapping.get("saved_searches", []) or []
    if not isinstance(raw_searches, list):
      raise SchemaValidationError(
          "Field 'saved_searches' must be a list",
          path=f"{path}.saved_searches",
      )
    saved_searches = [
        GoogleSecOpsSavedSearch.from_dict(item, f"{path}.saved_searches[{idx}]")
        for idx, item in enumerate(raw_searches)
    ]

    raw_ref_lists = mapping.get("reference_lists", []) or []
    if not isinstance(raw_ref_lists, list):
      raise SchemaValidationError(
          "Field 'reference_lists' must be a list",
          path=f"{path}.reference_lists",
      )
    reference_lists = [
        GoogleSecOpsReferenceList.from_dict(item, f"{path}.reference_lists[{idx}]")
        for idx, item in enumerate(raw_ref_lists)
    ]

    parser_extensions = _str_list(mapping, "parser_extensions", path)
    return cls(
        run_frequency=run_frequency,
        data_rbac=data_rbac,
        log_type_mappings=log_type_mappings,
        detections=detections,
        saved_searches=saved_searches,
        reference_lists=reference_lists,
        parser_extensions=parser_extensions,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize GoogleSecOpsPlatform to a plain dictionary."""
    result: dict[str, Any] = {}
    if self.run_frequency is not None:
      result["run_frequency"] = self.run_frequency.to_dict()
    if self.data_rbac is not None:
      result["data_rbac"] = self.data_rbac
    result["log_type_mappings"] = dict(self.log_type_mappings)
    result["detections"] = [det.to_dict() for det in self.detections]
    result["saved_searches"] = [s.to_dict() for s in self.saved_searches]
    result["reference_lists"] = [r.to_dict() for r in self.reference_lists]
    if self.parser_extensions:
      result["parser_extensions"] = list(self.parser_extensions)
    return result


@dataclass
class DatabricksPlatform:
  """Platform bindings for Databricks Unity Catalog OCSF Lakehouse."""

  catalog: str = "security_lakehouse"
  schema_name: str = "ocsf_silver"
  table_mappings: dict[str, str] = field(default_factory=dict)
  detections: list[str] = field(default_factory=list)
  notes: str = ""

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "platforms.databricks"
  ) -> DatabricksPlatform:
    """Validate and construct DatabricksPlatform from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {"catalog", "schema_name", "table_mappings", "detections", "notes"},
        path,
    )
    catalog = (
        _optional_str(mapping, "catalog", path, default="security_lakehouse")
        or "security_lakehouse"
    )
    schema_name = (
        _optional_str(mapping, "schema_name", path, default="ocsf_silver")
        or "ocsf_silver"
    )
    table_mappings = _str_dict(mapping, "table_mappings", path)
    detections = _str_list(mapping, "detections", path)
    notes = _optional_str(mapping, "notes", path, default="") or ""
    return cls(
        catalog=catalog,
        schema_name=schema_name,
        table_mappings=table_mappings,
        detections=detections,
        notes=notes,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize DatabricksPlatform to a plain dictionary."""
    result: dict[str, Any] = {
        "catalog": self.catalog,
        "schema_name": self.schema_name,
        "table_mappings": dict(self.table_mappings),
        "detections": list(self.detections),
    }
    if self.notes:
      result["notes"] = self.notes
    return result


@dataclass
class SigmaPlatform:
  """Platform bindings for Sigma vendor-neutral detection rules."""

  rules: list[str] = field(default_factory=list)
  notes: str = ""

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "platforms.sigma"
  ) -> SigmaPlatform:
    """Validate and construct SigmaPlatform from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"rules", "notes"}, path)
    rules = _str_list(mapping, "rules", path)
    notes = _optional_str(mapping, "notes", path, default="") or ""
    return cls(rules=rules, notes=notes)

  def to_dict(self) -> dict[str, Any]:
    """Serialize SigmaPlatform to a plain dictionary."""
    result: dict[str, Any] = {"rules": list(self.rules)}
    if self.notes:
      result["notes"] = self.notes
    return result


@dataclass
class SplunkPlatform:
  """Platform bindings for Splunk sourcetypes and saved searches."""

  sourcetypes: dict[str, str] = field(default_factory=dict)
  saved_searches: list[str] = field(default_factory=list)
  notes: str = ""

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "platforms.splunk"
  ) -> SplunkPlatform:
    """Validate and construct SplunkPlatform from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"sourcetypes", "saved_searches", "notes"}, path)
    sourcetypes = _str_dict(mapping, "sourcetypes", path)
    saved_searches = _str_list(mapping, "saved_searches", path)
    notes = _optional_str(mapping, "notes", path, default="") or ""
    return cls(
        sourcetypes=sourcetypes,
        saved_searches=saved_searches,
        notes=notes,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize SplunkPlatform to a plain dictionary."""
    result: dict[str, Any] = {"sourcetypes": dict(self.sourcetypes)}
    if self.saved_searches:
      result["saved_searches"] = list(self.saved_searches)
    if self.notes:
      result["notes"] = self.notes
    return result


@dataclass
class PlatformBindings:
  """Cross-vendor platform bindings for a security usecase package."""

  google_secops: GoogleSecOpsPlatform | None = None
  databricks: DatabricksPlatform | None = None
  sigma: SigmaPlatform | None = None
  splunk: SplunkPlatform | None = None

  @classmethod
  def from_dict(cls, data: dict[str, Any], path: str = "platforms") -> PlatformBindings:
    """Validate and construct PlatformBindings from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping, {"google_secops", "databricks", "sigma", "splunk"}, path
    )
    secops = (
        GoogleSecOpsPlatform.from_dict(
            mapping["google_secops"], f"{path}.google_secops"
        )
        if mapping.get("google_secops") is not None
        else None
    )
    databricks = (
        DatabricksPlatform.from_dict(mapping["databricks"], f"{path}.databricks")
        if mapping.get("databricks") is not None
        else None
    )
    sigma = (
        SigmaPlatform.from_dict(mapping["sigma"], f"{path}.sigma")
        if mapping.get("sigma") is not None
        else None
    )
    splunk = (
        SplunkPlatform.from_dict(mapping["splunk"], f"{path}.splunk")
        if mapping.get("splunk") is not None
        else None
    )
    return cls(
        google_secops=secops,
        databricks=databricks,
        sigma=sigma,
        splunk=splunk,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize PlatformBindings to a plain dictionary."""
    result: dict[str, Any] = {}
    if self.google_secops is not None:
      result["google_secops"] = self.google_secops.to_dict()
    if self.databricks is not None:
      result["databricks"] = self.databricks.to_dict()
    if self.sigma is not None:
      result["sigma"] = self.sigma.to_dict()
    if self.splunk is not None:
      result["splunk"] = self.splunk.to_dict()
    return result


@dataclass
class SecurityUsecaseManifest:
  """Top-level v2 <USECASE>.md frontmatter manifest (OKF v0.2 + OCSF)."""

  schema_version: str
  id: str
  title: str
  version: str
  created: str
  updated: str
  author: str
  license: str
  description: str
  tags: list[str]
  environment: EnvironmentContext
  telemetry: TelemetrySection
  platforms: PlatformBindings

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "manifest"
  ) -> SecurityUsecaseManifest:
    """Validate and construct SecurityUsecaseManifest from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "schema_version",
            "id",
            "title",
            "version",
            "created",
            "updated",
            "author",
            "license",
            "description",
            "tags",
            "environment",
            "telemetry",
            "platforms",
        },
        path,
    )
    schema_version = _require_non_empty_str(mapping, "schema_version", path)
    if schema_version != SCHEMA_VERSION_V2:
      raise SchemaValidationError(
          f"Unsupported schema_version {schema_version!r}; expected '2.0'",
          path=f"{path}.schema_version",
      )
    usecase_id = _require_non_empty_str(mapping, "id", path)
    if not _USECASE_ID_RE.match(usecase_id):
      raise SchemaValidationError(
          f"Usecase id {usecase_id!r} must match {USECASE_ID_PATTERN}",
          path=f"{path}.id",
      )
    title = _require_non_empty_str(mapping, "title", path)
    version = _require_non_empty_str(mapping, "version", path)
    created = _require_non_empty_str(mapping, "created", path)
    updated = _require_non_empty_str(mapping, "updated", path)
    author = _require_non_empty_str(mapping, "author", path)
    license_id = _require_non_empty_str(mapping, "license", path)
    description = _require_non_empty_str(mapping, "description", path)
    tags = _str_list(mapping, "tags", path, required=True)
    if not tags:
      raise SchemaValidationError(
          "Field 'tags' must contain at least one tag", path=f"{path}.tags"
      )

    if "environment" not in mapping or mapping["environment"] is None:
      raise SchemaValidationError(
          "Missing required field 'environment'", path=f"{path}.environment"
      )
    environment = EnvironmentContext.from_dict(
        mapping["environment"], f"{path}.environment"
    )

    if "telemetry" not in mapping or mapping["telemetry"] is None:
      raise SchemaValidationError(
          "Missing required field 'telemetry'", path=f"{path}.telemetry"
      )
    telemetry = TelemetrySection.from_dict(mapping["telemetry"], f"{path}.telemetry")

    if "platforms" not in mapping or mapping["platforms"] is None:
      raise SchemaValidationError(
          "Missing required field 'platforms'", path=f"{path}.platforms"
      )
    platforms = PlatformBindings.from_dict(mapping["platforms"], f"{path}.platforms")

    return cls(
        schema_version=schema_version,
        id=usecase_id,
        title=title,
        version=version,
        created=created,
        updated=updated,
        author=author,
        license=license_id,
        description=description,
        tags=tags,
        environment=environment,
        telemetry=telemetry,
        platforms=platforms,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize SecurityUsecaseManifest to a plain dictionary."""
    return {
        "schema_version": self.schema_version,
        "id": self.id,
        "title": self.title,
        "version": self.version,
        "created": self.created,
        "updated": self.updated,
        "author": self.author,
        "license": self.license,
        "description": self.description,
        "tags": list(self.tags),
        "environment": self.environment.to_dict(),
        "telemetry": self.telemetry.to_dict(),
        "platforms": self.platforms.to_dict(),
    }


@dataclass
class ThreatContext:
  """Held-out adversary, advisory, CVE, and MITRE context for eval.yaml."""

  grounding_tier: GroundingTier
  difficulty_tier: DifficultyTier = DifficultyTier.INTERMEDIATE
  threat_actor: str | None = None
  actor_aliases: list[str] = field(default_factory=list)
  campaign_name: str | None = None
  cisa_advisories: list[str] = field(default_factory=list)
  cve_ids: list[str] = field(default_factory=list)
  mitre_tactics: list[str] = field(default_factory=list)
  mitre_techniques: list[str] = field(default_factory=list)
  release_day: int | None = None
  cohort: str | None = None
  notes: str = ""

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "threat_context"
  ) -> ThreatContext:
    """Validate and construct ThreatContext from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "grounding_tier",
            "difficulty_tier",
            "threat_actor",
            "actor_aliases",
            "campaign_name",
            "cisa_advisories",
            "cve_ids",
            "mitre_tactics",
            "mitre_techniques",
            "release_day",
            "cohort",
            "notes",
        },
        path,
    )
    if "grounding_tier" not in mapping or mapping["grounding_tier"] is None:
      raise SchemaValidationError(
          "Missing required field 'grounding_tier'",
          path=f"{path}.grounding_tier",
      )
    grounding_tier = _parse_enum(
        mapping["grounding_tier"], GroundingTier, f"{path}.grounding_tier"
    )
    raw_diff = mapping.get("difficulty_tier", DifficultyTier.INTERMEDIATE.value)
    difficulty_tier = _parse_enum(raw_diff, DifficultyTier, f"{path}.difficulty_tier")
    return cls(
        grounding_tier=grounding_tier,
        difficulty_tier=difficulty_tier,
        threat_actor=_optional_str(mapping, "threat_actor", path),
        actor_aliases=_str_list(mapping, "actor_aliases", path),
        campaign_name=_optional_str(mapping, "campaign_name", path),
        cisa_advisories=_str_list(mapping, "cisa_advisories", path),
        cve_ids=_str_list(mapping, "cve_ids", path),
        mitre_tactics=_str_list(mapping, "mitre_tactics", path),
        mitre_techniques=_str_list(mapping, "mitre_techniques", path),
        release_day=_optional_int(mapping, "release_day", path),
        cohort=_optional_str(mapping, "cohort", path),
        notes=_optional_str(mapping, "notes", path, default="") or "",
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize ThreatContext to a plain dictionary."""
    result: dict[str, Any] = {
        "grounding_tier": self.grounding_tier.value,
        "difficulty_tier": self.difficulty_tier.value,
        "threat_actor": self.threat_actor,
        "actor_aliases": list(self.actor_aliases),
        "campaign_name": self.campaign_name,
        "cisa_advisories": list(self.cisa_advisories),
        "cve_ids": list(self.cve_ids),
        "mitre_tactics": list(self.mitre_tactics),
        "mitre_techniques": list(self.mitre_techniques),
    }
    if self.release_day is not None:
      result["release_day"] = self.release_day
    if self.cohort is not None:
      result["cohort"] = self.cohort
    if self.notes:
      result["notes"] = self.notes
    return result


@dataclass
class AlertTriageTask:
  """Alert triage evaluation task definition."""

  enabled: bool = True
  case_id: str | None = None
  alert_ids: list[str] = field(default_factory=list)
  prompt: str = ""
  expected_skill: str | None = None
  skill_bindings: dict[str, str] = field(default_factory=dict)
  time_horizon_hours: int = DEFAULT_TRIAGE_HORIZON_HOURS

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "tasks.alert_triage"
  ) -> AlertTriageTask:
    """Validate and construct AlertTriageTask from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "enabled",
            "case_id",
            "alert_ids",
            "prompt",
            "expected_skill",
            "skill_bindings",
            "time_horizon_hours",
        },
        path,
    )
    horizon = _optional_int(
        mapping,
        "time_horizon_hours",
        path,
        default=DEFAULT_TRIAGE_HORIZON_HOURS,
    )
    return cls(
        enabled=_optional_bool(mapping, "enabled", path, default=True),
        case_id=_optional_str(mapping, "case_id", path),
        alert_ids=_str_list(mapping, "alert_ids", path),
        prompt=_optional_str(mapping, "prompt", path, default="") or "",
        expected_skill=_optional_str(mapping, "expected_skill", path),
        skill_bindings=_str_dict(mapping, "skill_bindings", path),
        time_horizon_hours=(
            DEFAULT_TRIAGE_HORIZON_HOURS if horizon is None else horizon
        ),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize AlertTriageTask to a plain dictionary."""
    return {
        "enabled": self.enabled,
        "case_id": self.case_id,
        "alert_ids": list(self.alert_ids),
        "prompt": self.prompt,
        "expected_skill": self.expected_skill,
        "skill_bindings": dict(self.skill_bindings),
        "time_horizon_hours": self.time_horizon_hours,
    }


@dataclass
class ThreatHuntTask:
  """Unalerted and intelligence-driven threat hunt evaluation task."""

  enabled: bool = True
  prompt_unalerted: str = ""
  prompt_intel_driven: str | None = None
  expected_patient_zero: str | None = None
  expected_skill: str | None = None
  skill_bindings: dict[str, str] = field(default_factory=dict)
  time_horizon_hours: int = DEFAULT_HUNT_HORIZON_HOURS

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "tasks.threat_hunt"
  ) -> ThreatHuntTask:
    """Validate and construct ThreatHuntTask from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "enabled",
            "prompt_unalerted",
            "prompt_intel_driven",
            "expected_patient_zero",
            "expected_skill",
            "skill_bindings",
            "time_horizon_hours",
        },
        path,
    )
    horizon = _optional_int(
        mapping,
        "time_horizon_hours",
        path,
        default=DEFAULT_HUNT_HORIZON_HOURS,
    )
    return cls(
        enabled=_optional_bool(mapping, "enabled", path, default=True),
        prompt_unalerted=(
            _optional_str(mapping, "prompt_unalerted", path, default="") or ""
        ),
        prompt_intel_driven=_optional_str(mapping, "prompt_intel_driven", path),
        expected_patient_zero=_optional_str(mapping, "expected_patient_zero", path),
        expected_skill=_optional_str(mapping, "expected_skill", path),
        skill_bindings=_str_dict(mapping, "skill_bindings", path),
        time_horizon_hours=(DEFAULT_HUNT_HORIZON_HOURS if horizon is None else horizon),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize ThreatHuntTask to a plain dictionary."""
    result: dict[str, Any] = {
        "enabled": self.enabled,
        "prompt_unalerted": self.prompt_unalerted,
        "prompt_intel_driven": self.prompt_intel_driven,
        "expected_patient_zero": self.expected_patient_zero,
        "time_horizon_hours": self.time_horizon_hours,
    }
    if self.expected_skill is not None:
      result["expected_skill"] = self.expected_skill
    if self.skill_bindings:
      result["skill_bindings"] = dict(self.skill_bindings)
    return result


@dataclass
class DetectionEngineeringTask:
  """Detection rule authoring and false-positive evaluation task."""

  enabled: bool = True
  prompt: str = ""
  target_techniques: list[str] = field(default_factory=list)
  reference_rules: list[str] = field(default_factory=list)
  expected_rule_count_min: int = 1
  max_false_positives_on_paired_baseline: int = 0

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "tasks.detection_engineering"
  ) -> DetectionEngineeringTask:
    """Validate and construct DetectionEngineeringTask from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "enabled",
            "prompt",
            "target_techniques",
            "reference_rules",
            "expected_rule_count_min",
            "max_false_positives_on_paired_baseline",
        },
        path,
    )
    min_rules = _optional_int(mapping, "expected_rule_count_min", path, default=1)
    max_fp = _optional_int(
        mapping, "max_false_positives_on_paired_baseline", path, default=0
    )
    return cls(
        enabled=_optional_bool(mapping, "enabled", path, default=True),
        prompt=_optional_str(mapping, "prompt", path, default="") or "",
        target_techniques=_str_list(mapping, "target_techniques", path),
        reference_rules=_str_list(mapping, "reference_rules", path),
        expected_rule_count_min=1 if min_rules is None else min_rules,
        max_false_positives_on_paired_baseline=(0 if max_fp is None else max_fp),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize DetectionEngineeringTask to a plain dictionary."""
    return {
        "enabled": self.enabled,
        "prompt": self.prompt,
        "target_techniques": list(self.target_techniques),
        "reference_rules": list(self.reference_rules),
        "expected_rule_count_min": self.expected_rule_count_min,
        "max_false_positives_on_paired_baseline": (
            self.max_false_positives_on_paired_baseline
        ),
    }


@dataclass
class EvaluationTasks:
  """Multi-task evaluation definitions for Blue Team benchmarking."""

  alert_triage: AlertTriageTask | None = None
  threat_hunt: ThreatHuntTask | None = None
  detection_engineering: DetectionEngineeringTask | None = None

  @classmethod
  def from_dict(cls, data: dict[str, Any], path: str = "tasks") -> EvaluationTasks:
    """Validate and construct EvaluationTasks from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {"alert_triage", "threat_hunt", "detection_engineering"},
        path,
    )
    triage = (
        AlertTriageTask.from_dict(mapping["alert_triage"], f"{path}.alert_triage")
        if mapping.get("alert_triage") is not None
        else None
    )
    hunt = (
        ThreatHuntTask.from_dict(mapping["threat_hunt"], f"{path}.threat_hunt")
        if mapping.get("threat_hunt") is not None
        else None
    )
    det_eng = (
        DetectionEngineeringTask.from_dict(
            mapping["detection_engineering"], f"{path}.detection_engineering"
        )
        if mapping.get("detection_engineering") is not None
        else None
    )
    return cls(
        alert_triage=triage,
        threat_hunt=hunt,
        detection_engineering=det_eng,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize EvaluationTasks to a plain dictionary."""
    result: dict[str, Any] = {}
    if self.alert_triage is not None:
      result["alert_triage"] = self.alert_triage.to_dict()
    if self.threat_hunt is not None:
      result["threat_hunt"] = self.threat_hunt.to_dict()
    if self.detection_engineering is not None:
      result["detection_engineering"] = self.detection_engineering.to_dict()
    return result


@dataclass
class KillChainStage:
  """Single chronological stage in an attack scenario's kill chain."""

  stage: str
  stream_id: str
  timestamp_utc: str | None = None
  tactic: str | None = None
  technique_id: str | None = None
  summary: str = ""
  key_evidence: list[str] = field(default_factory=list)

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "ground_truth.kill_chain"
  ) -> KillChainStage:
    """Validate and construct KillChainStage from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "stage",
            "stream_id",
            "timestamp_utc",
            "tactic",
            "technique_id",
            "summary",
            "key_evidence",
        },
        path,
    )
    stage = _require_non_empty_str(mapping, "stage", path)
    stream_id = _require_non_empty_str(mapping, "stream_id", path)
    return cls(
        stage=stage,
        stream_id=stream_id,
        timestamp_utc=_optional_str(mapping, "timestamp_utc", path),
        tactic=_optional_str(mapping, "tactic", path),
        technique_id=_optional_str(mapping, "technique_id", path),
        summary=_optional_str(mapping, "summary", path, default="") or "",
        key_evidence=_str_list(mapping, "key_evidence", path),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize KillChainStage to a plain dictionary."""
    return {
        "stage": self.stage,
        "stream_id": self.stream_id,
        "timestamp_utc": self.timestamp_utc,
        "tactic": self.tactic,
        "technique_id": self.technique_id,
        "summary": self.summary,
        "key_evidence": list(self.key_evidence),
    }


@dataclass
class AffectedAsset:
  """Ground-truth affected asset with criticality tier and blast-radius costs."""

  hostname: str
  criticality_tier: CriticalityTier = CriticalityTier.TIER_2_WORKSTATION
  ip_addresses: list[str] = field(default_factory=list)
  role: str = ""
  patient_zero: bool = False
  blast_radius_fp_usd: float = 0.0
  blast_radius_fn_usd: float = 0.0

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "ground_truth.entities_and_iocs.affected_assets",
  ) -> AffectedAsset:
    """Validate and construct AffectedAsset from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "hostname",
            "criticality_tier",
            "ip_addresses",
            "role",
            "patient_zero",
            "blast_radius_fp_usd",
            "blast_radius_fn_usd",
        },
        path,
    )
    hostname = _require_non_empty_str(mapping, "hostname", path)
    raw_tier = mapping.get("criticality_tier", CriticalityTier.TIER_2_WORKSTATION.value)
    criticality_tier = _parse_enum(
        raw_tier, CriticalityTier, f"{path}.criticality_tier"
    )
    return cls(
        hostname=hostname,
        criticality_tier=criticality_tier,
        ip_addresses=_str_list(mapping, "ip_addresses", path),
        role=_optional_str(mapping, "role", path, default="") or "",
        patient_zero=_optional_bool(mapping, "patient_zero", path, default=False),
        blast_radius_fp_usd=_optional_float(
            mapping, "blast_radius_fp_usd", path, default=0.0
        ),
        blast_radius_fn_usd=_optional_float(
            mapping, "blast_radius_fn_usd", path, default=0.0
        ),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize AffectedAsset to a plain dictionary."""
    return {
        "hostname": self.hostname,
        "criticality_tier": self.criticality_tier.value,
        "ip_addresses": list(self.ip_addresses),
        "role": self.role,
        "patient_zero": self.patient_zero,
        "blast_radius_fp_usd": self.blast_radius_fp_usd,
        "blast_radius_fn_usd": self.blast_radius_fn_usd,
    }


@dataclass
class MaliciousIoc:
  """Ground-truth malicious indicator of compromise."""

  type: str
  value: str
  role: str = ""
  notes: str = ""

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "ground_truth.entities_and_iocs.malicious_iocs",
  ) -> MaliciousIoc:
    """Validate and construct MaliciousIoc from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"type", "value", "role", "notes"}, path)
    ioc_type = _require_non_empty_str(mapping, "type", path)
    value = _require_non_empty_str(mapping, "value", path)
    role = _optional_str(mapping, "role", path, default="") or ""
    notes = _optional_str(mapping, "notes", path, default="") or ""
    return cls(type=ioc_type, value=value, role=role, notes=notes)

  def to_dict(self) -> dict[str, Any]:
    """Serialize MaliciousIoc to a plain dictionary."""
    return {
        "type": self.type,
        "value": self.value,
        "role": self.role,
        "notes": self.notes,
    }


@dataclass
class ChangeWindow:
  """Maintenance or change management ticket context."""

  ticket_id: str
  approved: bool = True
  start_utc: str | None = None
  end_utc: str | None = None
  summary: str = ""

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "ground_truth.entities_and_iocs.benign_confusers.change_window",
  ) -> ChangeWindow:
    """Validate and construct ChangeWindow from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {"ticket_id", "approved", "start_utc", "end_utc", "summary"},
        path,
    )
    ticket_id = _require_non_empty_str(mapping, "ticket_id", path)
    return cls(
        ticket_id=ticket_id,
        approved=_optional_bool(mapping, "approved", path, default=True),
        start_utc=_optional_str(mapping, "start_utc", path),
        end_utc=_optional_str(mapping, "end_utc", path),
        summary=_optional_str(mapping, "summary", path, default="") or "",
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize ChangeWindow to a plain dictionary."""
    return {
        "ticket_id": self.ticket_id,
        "approved": self.approved,
        "start_utc": self.start_utc,
        "end_utc": self.end_utc,
        "summary": self.summary,
    }


@dataclass
class BenignConfusers:
  """Benign confusers (signed LOLBins, internal IPs, change windows)."""

  signed_lolbins: list[str] = field(default_factory=list)
  internal_ips: list[str] = field(default_factory=list)
  change_window: ChangeWindow | None = None
  admin_tools: list[str] = field(default_factory=list)

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "ground_truth.entities_and_iocs.benign_confusers",
  ) -> BenignConfusers:
    """Validate and construct BenignConfusers from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {"signed_lolbins", "internal_ips", "change_window", "admin_tools"},
        path,
    )
    raw_cw = mapping.get("change_window")
    change_window = (
        ChangeWindow.from_dict(raw_cw, f"{path}.change_window")
        if raw_cw is not None
        else None
    )
    return cls(
        signed_lolbins=_str_list(mapping, "signed_lolbins", path),
        internal_ips=_str_list(mapping, "internal_ips", path),
        change_window=change_window,
        admin_tools=_str_list(mapping, "admin_tools", path),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize BenignConfusers to a plain dictionary."""
    result: dict[str, Any] = {
        "signed_lolbins": list(self.signed_lolbins),
        "internal_ips": list(self.internal_ips),
        "change_window": (
            self.change_window.to_dict() if self.change_window is not None else None
        ),
    }
    if self.admin_tools:
      result["admin_tools"] = list(self.admin_tools)
    return result


@dataclass
class EntitiesAndIocs:
  """Ground-truth entities, IOCs, and benign confusers for an evaluation."""

  compromised_accounts: list[str] = field(default_factory=list)
  affected_assets: list[AffectedAsset] = field(default_factory=list)
  malicious_iocs: list[MaliciousIoc] = field(default_factory=list)
  benign_confusers: BenignConfusers = field(default_factory=BenignConfusers)

  @classmethod
  def from_dict(
      cls,
      data: dict[str, Any],
      path: str = "ground_truth.entities_and_iocs",
  ) -> EntitiesAndIocs:
    """Validate and construct EntitiesAndIocs from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "compromised_accounts",
            "affected_assets",
            "malicious_iocs",
            "benign_confusers",
        },
        path,
    )
    compromised_accounts = _str_list(mapping, "compromised_accounts", path)

    raw_assets = mapping.get("affected_assets", []) or []
    if not isinstance(raw_assets, list):
      raise SchemaValidationError(
          "Field 'affected_assets' must be a list",
          path=f"{path}.affected_assets",
      )
    affected_assets = [
        AffectedAsset.from_dict(item, f"{path}.affected_assets[{idx}]")
        for idx, item in enumerate(raw_assets)
    ]

    raw_iocs = mapping.get("malicious_iocs", []) or []
    if not isinstance(raw_iocs, list):
      raise SchemaValidationError(
          "Field 'malicious_iocs' must be a list",
          path=f"{path}.malicious_iocs",
      )
    malicious_iocs = [
        MaliciousIoc.from_dict(item, f"{path}.malicious_iocs[{idx}]")
        for idx, item in enumerate(raw_iocs)
    ]

    raw_confusers = mapping.get("benign_confusers")
    benign_confusers = (
        BenignConfusers.from_dict(raw_confusers, f"{path}.benign_confusers")
        if raw_confusers is not None
        else BenignConfusers()
    )

    return cls(
        compromised_accounts=compromised_accounts,
        affected_assets=affected_assets,
        malicious_iocs=malicious_iocs,
        benign_confusers=benign_confusers,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize EntitiesAndIocs to a plain dictionary."""
    return {
        "compromised_accounts": list(self.compromised_accounts),
        "affected_assets": [a.to_dict() for a in self.affected_assets],
        "malicious_iocs": [ioc.to_dict() for ioc in self.malicious_iocs],
        "benign_confusers": self.benign_confusers.to_dict(),
    }


@dataclass
class GroundTruth:
  """Held-out ground-truth verdict, disposition, kill chain, and entities."""

  expected_disposition: ExpectedDisposition
  expected_verdict: ExpectedVerdict
  severity: str = "HIGH"
  patient_zero_host: str | None = None
  patient_zero_account: str | None = None
  root_cause_summary: str = ""
  kill_chain: list[KillChainStage] = field(default_factory=list)
  entities_and_iocs: EntitiesAndIocs = field(default_factory=EntitiesAndIocs)

  @classmethod
  def from_dict(cls, data: dict[str, Any], path: str = "ground_truth") -> GroundTruth:
    """Validate and construct GroundTruth from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "expected_disposition",
            "expected_verdict",
            "severity",
            "patient_zero_host",
            "patient_zero_account",
            "root_cause_summary",
            "kill_chain",
            "entities_and_iocs",
        },
        path,
    )
    if "expected_disposition" not in mapping or mapping["expected_disposition"] is None:
      raise SchemaValidationError(
          "Missing required field 'expected_disposition'",
          path=f"{path}.expected_disposition",
      )
    expected_disposition = _parse_enum(
        mapping["expected_disposition"],
        ExpectedDisposition,
        f"{path}.expected_disposition",
    )

    if "expected_verdict" not in mapping or mapping["expected_verdict"] is None:
      raise SchemaValidationError(
          "Missing required field 'expected_verdict'",
          path=f"{path}.expected_verdict",
      )
    expected_verdict = _parse_enum(
        mapping["expected_verdict"],
        ExpectedVerdict,
        f"{path}.expected_verdict",
    )

    severity = _optional_str(mapping, "severity", path, default="HIGH") or "HIGH"
    patient_zero_host = _optional_str(mapping, "patient_zero_host", path)
    patient_zero_account = _optional_str(mapping, "patient_zero_account", path)
    root_cause_summary = (
        _optional_str(mapping, "root_cause_summary", path, default="") or ""
    )

    raw_kc = mapping.get("kill_chain", []) or []
    if not isinstance(raw_kc, list):
      raise SchemaValidationError(
          "Field 'kill_chain' must be a list", path=f"{path}.kill_chain"
      )
    kill_chain = [
        KillChainStage.from_dict(item, f"{path}.kill_chain[{idx}]")
        for idx, item in enumerate(raw_kc)
    ]

    raw_entities = mapping.get("entities_and_iocs")
    entities_and_iocs = (
        EntitiesAndIocs.from_dict(raw_entities, f"{path}.entities_and_iocs")
        if raw_entities is not None
        else EntitiesAndIocs()
    )

    return cls(
        expected_disposition=expected_disposition,
        expected_verdict=expected_verdict,
        severity=severity,
        patient_zero_host=patient_zero_host,
        patient_zero_account=patient_zero_account,
        root_cause_summary=root_cause_summary,
        kill_chain=kill_chain,
        entities_and_iocs=entities_and_iocs,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize GroundTruth to a plain dictionary."""
    return {
        "expected_disposition": self.expected_disposition.value,
        "expected_verdict": self.expected_verdict.value,
        "severity": self.severity,
        "patient_zero_host": self.patient_zero_host,
        "patient_zero_account": self.patient_zero_account,
        "root_cause_summary": self.root_cause_summary,
        "kill_chain": [stage.to_dict() for stage in self.kill_chain],
        "entities_and_iocs": self.entities_and_iocs.to_dict(),
    }


@dataclass
class ExpectedActions:
  """Primary, secondary, and prohibited containment/response actions."""

  primary: list[str] = field(default_factory=list)
  secondary: list[str] = field(default_factory=list)
  prohibited: list[str] = field(default_factory=list)

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "compliance_gates.expected_actions"
  ) -> ExpectedActions:
    """Validate and construct ExpectedActions from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(mapping, {"primary", "secondary", "prohibited"}, path)
    return cls(
        primary=_str_list(mapping, "primary", path),
        secondary=_str_list(mapping, "secondary", path),
        prohibited=_str_list(mapping, "prohibited", path),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize ExpectedActions to a plain dictionary."""
    return {
        "primary": list(self.primary),
        "secondary": list(self.secondary),
        "prohibited": list(self.prohibited),
    }


@dataclass
class ComplianceGates:
  """Operational safety and SOP compliance gates for agent evaluation."""

  requires_pre_containment_verification: bool = True
  requires_168h_horizon_widening: bool = False
  forbid_external_cti_on_internal_ips: bool = True
  forbid_lolbin_hash_blocking: bool = True
  respect_change_window: bool = False
  expected_actions: ExpectedActions = field(default_factory=ExpectedActions)

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "compliance_gates"
  ) -> ComplianceGates:
    """Validate and construct ComplianceGates from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "requires_pre_containment_verification",
            "requires_168h_horizon_widening",
            "forbid_external_cti_on_internal_ips",
            "forbid_lolbin_hash_blocking",
            "respect_change_window",
            "expected_actions",
        },
        path,
    )
    raw_actions = mapping.get("expected_actions")
    expected_actions = (
        ExpectedActions.from_dict(raw_actions, f"{path}.expected_actions")
        if raw_actions is not None
        else ExpectedActions()
    )
    return cls(
        requires_pre_containment_verification=_optional_bool(
            mapping,
            "requires_pre_containment_verification",
            path,
            default=True,
        ),
        requires_168h_horizon_widening=_optional_bool(
            mapping, "requires_168h_horizon_widening", path, default=False
        ),
        forbid_external_cti_on_internal_ips=_optional_bool(
            mapping, "forbid_external_cti_on_internal_ips", path, default=True
        ),
        forbid_lolbin_hash_blocking=_optional_bool(
            mapping, "forbid_lolbin_hash_blocking", path, default=True
        ),
        respect_change_window=_optional_bool(
            mapping, "respect_change_window", path, default=False
        ),
        expected_actions=expected_actions,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize ComplianceGates to a plain dictionary."""
    return {
        "requires_pre_containment_verification": (
            self.requires_pre_containment_verification
        ),
        "requires_168h_horizon_widening": self.requires_168h_horizon_widening,
        "forbid_external_cti_on_internal_ips": self.forbid_external_cti_on_internal_ips,
        "forbid_lolbin_hash_blocking": self.forbid_lolbin_hash_blocking,
        "respect_change_window": self.respect_change_window,
        "expected_actions": self.expected_actions.to_dict(),
    }


@dataclass
class CounterfactualPair:
  """Signal Detection Theory counterfactual pairing between twin usecases."""

  paired_usecase_id: str
  pair_relationship: PairRelationship
  shared_entities: list[str] = field(default_factory=list)
  shared_telemetry_streams: list[str] = field(default_factory=list)
  discriminating_invariant: str = ""

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "counterfactual_pair"
  ) -> CounterfactualPair:
    """Validate and construct CounterfactualPair from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "paired_usecase_id",
            "pair_relationship",
            "shared_entities",
            "shared_telemetry_streams",
            "discriminating_invariant",
        },
        path,
    )
    paired_id = _require_non_empty_str(mapping, "paired_usecase_id", path)
    if "pair_relationship" not in mapping or mapping["pair_relationship"] is None:
      raise SchemaValidationError(
          "Missing required field 'pair_relationship'",
          path=f"{path}.pair_relationship",
      )
    relationship = _parse_enum(
        mapping["pair_relationship"],
        PairRelationship,
        f"{path}.pair_relationship",
    )
    return cls(
        paired_usecase_id=paired_id,
        pair_relationship=relationship,
        shared_entities=_str_list(mapping, "shared_entities", path),
        shared_telemetry_streams=_str_list(mapping, "shared_telemetry_streams", path),
        discriminating_invariant=(
            _optional_str(mapping, "discriminating_invariant", path, default="") or ""
        ),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize CounterfactualPair to a plain dictionary."""
    return {
        "paired_usecase_id": self.paired_usecase_id,
        "pair_relationship": self.pair_relationship.value,
        "shared_entities": list(self.shared_entities),
        "shared_telemetry_streams": list(self.shared_telemetry_streams),
        "discriminating_invariant": self.discriminating_invariant,
    }


@dataclass
class ReferenceQueries:
  """Held-out reference queries and rules across supported platforms."""

  google_secops_udm: list[str] = field(default_factory=list)
  google_secops_yaral: list[str] = field(default_factory=list)
  databricks_sql: list[str] = field(default_factory=list)
  sigma: list[str] = field(default_factory=list)
  splunk_spl: list[str] = field(default_factory=list)

  @classmethod
  def from_dict(
      cls, data: dict[str, Any], path: str = "reference_queries"
  ) -> ReferenceQueries:
    """Validate and construct ReferenceQueries from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "google_secops_udm",
            "google_secops_yaral",
            "databricks_sql",
            "sigma",
            "splunk_spl",
        },
        path,
    )
    return cls(
        google_secops_udm=_str_list(mapping, "google_secops_udm", path),
        google_secops_yaral=_str_list(mapping, "google_secops_yaral", path),
        databricks_sql=_str_list(mapping, "databricks_sql", path),
        sigma=_str_list(mapping, "sigma", path),
        splunk_spl=_str_list(mapping, "splunk_spl", path),
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize ReferenceQueries to a plain dictionary."""
    return {
        "google_secops_udm": list(self.google_secops_udm),
        "google_secops_yaral": list(self.google_secops_yaral),
        "databricks_sql": list(self.databricks_sql),
        "sigma": list(self.sigma),
        "splunk_spl": list(self.splunk_spl),
    }


@dataclass
class SecurityUsecaseEval:
  """Top-level v2 eval.yaml held-out Blue Team benchmark specification."""

  schema_version: str
  usecase_id: str
  threat_context: ThreatContext
  tasks: EvaluationTasks
  ground_truth: GroundTruth
  compliance_gates: ComplianceGates = field(default_factory=ComplianceGates)
  counterfactual_pair: CounterfactualPair | None = None
  reference_queries: ReferenceQueries = field(default_factory=ReferenceQueries)

  @classmethod
  def from_dict(cls, data: dict[str, Any], path: str = "eval") -> SecurityUsecaseEval:
    """Validate and construct SecurityUsecaseEval from a dictionary."""
    mapping = _ensure_mapping(data, path)
    _reject_unknown_keys(
        mapping,
        {
            "schema_version",
            "usecase_id",
            "threat_context",
            "tasks",
            "ground_truth",
            "compliance_gates",
            "counterfactual_pair",
            "reference_queries",
        },
        path,
    )
    schema_version = _require_non_empty_str(mapping, "schema_version", path)
    if schema_version != SCHEMA_VERSION_V2:
      raise SchemaValidationError(
          f"Unsupported eval schema_version {schema_version!r}; expected '2.0'",
          path=f"{path}.schema_version",
      )
    usecase_id = _require_non_empty_str(mapping, "usecase_id", path)
    if not _USECASE_ID_RE.match(usecase_id):
      raise SchemaValidationError(
          f"usecase_id {usecase_id!r} must match {USECASE_ID_PATTERN}",
          path=f"{path}.usecase_id",
      )

    if "threat_context" not in mapping or mapping["threat_context"] is None:
      raise SchemaValidationError(
          "Missing required field 'threat_context'",
          path=f"{path}.threat_context",
      )
    threat_context = ThreatContext.from_dict(
        mapping["threat_context"], f"{path}.threat_context"
    )

    if "tasks" not in mapping or mapping["tasks"] is None:
      raise SchemaValidationError(
          "Missing required field 'tasks'", path=f"{path}.tasks"
      )
    tasks = EvaluationTasks.from_dict(mapping["tasks"], f"{path}.tasks")

    if "ground_truth" not in mapping or mapping["ground_truth"] is None:
      raise SchemaValidationError(
          "Missing required field 'ground_truth'", path=f"{path}.ground_truth"
      )
    ground_truth = GroundTruth.from_dict(
        mapping["ground_truth"], f"{path}.ground_truth"
    )

    raw_gates = mapping.get("compliance_gates")
    compliance_gates = (
        ComplianceGates.from_dict(raw_gates, f"{path}.compliance_gates")
        if raw_gates is not None
        else ComplianceGates()
    )

    raw_pair = mapping.get("counterfactual_pair")
    counterfactual_pair = (
        CounterfactualPair.from_dict(raw_pair, f"{path}.counterfactual_pair")
        if raw_pair is not None
        else None
    )

    raw_queries = mapping.get("reference_queries")
    reference_queries = (
        ReferenceQueries.from_dict(raw_queries, f"{path}.reference_queries")
        if raw_queries is not None
        else ReferenceQueries()
    )

    return cls(
        schema_version=schema_version,
        usecase_id=usecase_id,
        threat_context=threat_context,
        tasks=tasks,
        ground_truth=ground_truth,
        compliance_gates=compliance_gates,
        counterfactual_pair=counterfactual_pair,
        reference_queries=reference_queries,
    )

  def to_dict(self) -> dict[str, Any]:
    """Serialize SecurityUsecaseEval to a plain dictionary."""
    return {
        "schema_version": self.schema_version,
        "usecase_id": self.usecase_id,
        "threat_context": self.threat_context.to_dict(),
        "tasks": self.tasks.to_dict(),
        "ground_truth": self.ground_truth.to_dict(),
        "compliance_gates": self.compliance_gates.to_dict(),
        "counterfactual_pair": (
            self.counterfactual_pair.to_dict()
            if self.counterfactual_pair is not None
            else None
        ),
        "reference_queries": self.reference_queries.to_dict(),
    }


@dataclass
class ParsedUsecasePackage:
  """Parsed representation of a usecase directory on disk."""

  usecase_dir: Path
  schema_version: str
  manifest: SecurityUsecaseManifest | None
  raw_frontmatter: dict[str, Any]
  public_markdown_body: str
  solution_markdown_body: str | None
  eval_data: SecurityUsecaseEval | None

  def to_dict(self, blind: bool = False) -> dict[str, Any]:
    """Serialize ParsedUsecasePackage to a JSON-compatible dictionary."""
    return {
        "usecase_dir": str(self.usecase_dir),
        "schema_version": self.schema_version,
        "manifest": (
            self.manifest.to_dict()
            if self.manifest is not None
            else dict(self.raw_frontmatter)
        ),
        "public_markdown_body": self.public_markdown_body,
        "solution_markdown_body": None if blind else self.solution_markdown_body,
        "eval_data": (
            None if blind or self.eval_data is None else self.eval_data.to_dict()
        ),
    }


def split_frontmatter_and_body(content: str) -> tuple[dict[str, Any], str]:
  """Split a Markdown file into YAML frontmatter dict and Markdown body.

  Args:
    content: Raw text content of `<USECASE>.md`.

  Returns:
    Tuple of `(frontmatter_dict, markdown_body)`.

  Raises:
    SchemaValidationError: If frontmatter delimiters or YAML syntax are invalid.
  """
  normalized = content.replace("\r\n", "\n")
  if normalized.startswith("\n---\n"):
    normalized = normalized[1:]
  if not normalized.startswith("---\n"):
    raise SchemaValidationError(
        "Markdown file is missing leading YAML frontmatter delimiter '---'",
        path="frontmatter",
    )

  parts = normalized.split("---\n", 2)
  if len(parts) < MIN_FRONTMATTER_PARTS:
    raise SchemaValidationError(
        "Markdown file is missing closing YAML frontmatter delimiter '---'",
        path="frontmatter",
    )

  frontmatter_yaml = parts[1]
  body = parts[2]
  try:
    loaded = yaml.safe_load(frontmatter_yaml)
  except yaml.YAMLError as exc:
    raise SchemaValidationError(
        f"Invalid YAML syntax in frontmatter: {exc}", path="frontmatter"
    ) from exc

  if not isinstance(loaded, dict):
    raise SchemaValidationError(
        "YAML frontmatter must be a key-value mapping", path="frontmatter"
    )
  return _normalize_yaml_scalars(loaded), body


def split_solution_section(markdown_body: str) -> tuple[str, str | None]:
  """Split Markdown body on `<!-- BEGIN_SOLUTION -->`.

  Args:
    markdown_body: Markdown text following the YAML frontmatter.

  Returns:
    Tuple of `(public_markdown_body, solution_markdown_body)`. When the
    delimiter is absent, `solution_markdown_body` is `None`.
  """
  if SOLUTION_DELIMITER not in markdown_body:
    return markdown_body.strip(), None
  public_part, solution_part = markdown_body.split(SOLUTION_DELIMITER, 1)
  return public_part.strip(), solution_part.strip()


def parse_usecase_package(
    usecase_dir: Path, blind: bool = False
) -> ParsedUsecasePackage:
  """Parse `<USECASE>/<USECASE>.md` and optional `eval.yaml` from a directory.

  Args:
    usecase_dir: Path to the `<USECASE>` directory.
    blind: When True, omits content below `<!-- BEGIN_SOLUTION -->` and does
      not load `eval.yaml`.

  Returns:
    Populated `ParsedUsecasePackage`.
  """
  resolved_dir = Path(usecase_dir)
  usecase_name = resolved_dir.name
  md_path = resolved_dir / f"{usecase_name}.md"
  if not md_path.is_file():
    raise SchemaValidationError(
        f"Missing required usecase manifest file: {md_path}",
        path=str(md_path),
    )

  raw_text = md_path.read_text(encoding="utf-8")
  raw_frontmatter, markdown_body = split_frontmatter_and_body(raw_text)
  public_body, solution_body = split_solution_section(markdown_body)

  schema_version = str(raw_frontmatter.get("schema_version", SCHEMA_VERSION_V1))
  manifest: SecurityUsecaseManifest | None = None
  if schema_version == SCHEMA_VERSION_V2:
    manifest = SecurityUsecaseManifest.from_dict(raw_frontmatter)

  eval_data: SecurityUsecaseEval | None = None
  if not blind:
    eval_path = resolved_dir / "eval.yaml"
    if eval_path.is_file():
      try:
        raw_eval = yaml.safe_load(eval_path.read_text(encoding="utf-8"))
      except yaml.YAMLError as exc:
        raise SchemaValidationError(
            f"Invalid YAML syntax in eval.yaml: {exc}", path="eval.yaml"
        ) from exc
      eval_data = SecurityUsecaseEval.from_dict(
          _normalize_yaml_scalars(raw_eval), path="eval"
      )

  return ParsedUsecasePackage(
      usecase_dir=resolved_dir,
      schema_version=schema_version,
      manifest=manifest,
      raw_frontmatter=raw_frontmatter,
      public_markdown_body=public_body,
      solution_markdown_body=None if blind else solution_body,
      eval_data=None if blind else eval_data,
  )


def build_usecase_json_schema() -> dict[str, Any]:
  """Build Draft 2020-12 JSON Schema for `<USECASE>.md` frontmatter."""
  return {
      "$schema": JSON_SCHEMA_DRAFT_2020_12,
      "$id": "https://chronicle.github.io/logstory/schemas/usecase.schema.json",
      "title": "SecurityUsecaseManifest",
      "description": (
          "Open Security Scenario & Logstory Usecase Manifest Schema (v2.0) "
          "combining OKF v0.2 provenance, OCSF telemetry streams, and "
          "multi-platform bindings."
      ),
      "type": "object",
      "additionalProperties": False,
      "required": [
          "schema_version",
          "id",
          "title",
          "version",
          "created",
          "updated",
          "author",
          "license",
          "description",
          "tags",
          "environment",
          "telemetry",
          "platforms",
      ],
      "properties": {
          "schema_version": {
              "type": "string",
              "const": SCHEMA_VERSION_V2,
              "description": "Usecase manifest schema version ('2.0').",
          },
          "id": {
              "type": "string",
              "pattern": USECASE_ID_PATTERN,
              "description": "Canonical uppercase usecase identifier.",
          },
          "title": {
              "type": "string",
              "minLength": 1,
              "description": "Human-readable blind-safe package title.",
          },
          "version": {
              "type": "string",
              "minLength": 1,
              "description": "Semantic version of the usecase package.",
          },
          "created": {
              "type": "string",
              "pattern": ISO_DATE_PATTERN,
              "description": "Initial authoring date (YYYY-MM-DD).",
          },
          "updated": {
              "type": "string",
              "pattern": ISO_DATE_PATTERN,
              "description": "Last modification date (YYYY-MM-DD).",
          },
          "author": {
              "type": "string",
              "minLength": 1,
              "description": "Package author or organization.",
          },
          "license": {
              "type": "string",
              "minLength": 1,
              "description": "SPDX license identifier (e.g., Apache-2.0).",
          },
          "description": {
              "type": "string",
              "minLength": 1,
              "description": (
                  "Blind-safe summary of the telemetry streams and scenario "
                  "context (no spoilers)."
              ),
          },
          "tags": {
              "type": "array",
              "minItems": 1,
              "items": {"type": "string"},
              "description": "Discovery tags for the usecase package.",
          },
          "environment": {"$ref": "#/$defs/EnvironmentContext"},
          "telemetry": {"$ref": "#/$defs/TelemetrySection"},
          "platforms": {"$ref": "#/$defs/PlatformBindings"},
      },
      "$defs": {
          "TimestampPolicy": {
              "type": "object",
              "additionalProperties": False,
              "description": "Replay timestamp adjustment policy.",
              "properties": {
                  "base_date": {
                      "type": "string",
                      "description": "Base date of synthetic logs (YYYY-MM-DD).",
                  },
                  "preserve_relative_offsets": {
                      "type": "boolean",
                      "description": (
                          "Whether relative inter-event offsets are preserved."
                      ),
                  },
                  "default_delta": {
                      "type": "string",
                      "description": "Default timestamp shift expression.",
                  },
                  "entity_offset_days": {
                      "type": "integer",
                      "description": (
                          "Days prior to events to replay entity context logs."
                      ),
                  },
                  "window_start": {
                      "type": ["string", "null"],
                      "description": "Optional UTC window start timestamp.",
                  },
                  "window_end": {
                      "type": ["string", "null"],
                      "description": "Optional UTC window end timestamp.",
                  },
              },
          },
          "EnvironmentContext": {
              "type": "object",
              "additionalProperties": False,
              "description": (
                  "Simulated organization, scenario classification, and "
                  "composable paired baselines."
              ),
              "properties": {
                  "organization": {
                      "type": "string",
                      "description": "Simulated enterprise domain name.",
                  },
                  "scenario_type": {
                      "type": "string",
                      "enum": [e.value for e in ScenarioType],
                      "description": "High-level scenario classification.",
                  },
                  "paired_baselines": {
                      "type": "array",
                      "items": {"type": "string"},
                      "description": (
                          "Composable benign baseline usecase IDs to co-replay."
                      ),
                  },
                  "timestamp_policy": {"$ref": "#/$defs/TimestampPolicy"},
                  "notes": {
                      "type": "string",
                      "description": "Optional environment notes.",
                  },
              },
          },
          "TelemetryStream": {
              "type": "object",
              "additionalProperties": False,
              "required": ["stream_id", "path", "log_type"],
              "description": "Vendor-neutral event or entity telemetry stream.",
              "properties": {
                  "stream_id": {
                      "type": "string",
                      "minLength": 1,
                      "description": "Stable identifier for the stream.",
                  },
                  "path": {
                      "type": "string",
                      "minLength": 1,
                      "description": (
                          "Relative path to the log file inside the usecase."
                      ),
                  },
                  "log_type": {
                      "type": "string",
                      "minLength": 1,
                      "description": "Canonical ingestion log type identifier.",
                  },
                  "vendor_name": {
                      "type": "string",
                      "description": "Telemetry vendor name.",
                  },
                  "product_name": {
                      "type": "string",
                      "description": "Telemetry product name.",
                  },
                  "ocsf_category_uid": {
                      "type": ["integer", "null"],
                      "description": "OCSF v1.3+ category UID.",
                  },
                  "ocsf_class_uid": {
                      "type": ["integer", "null"],
                      "description": "OCSF v1.3+ class UID.",
                  },
                  "ocsf_class_name": {
                      "type": ["string", "null"],
                      "description": "OCSF v1.3+ class name.",
                  },
                  "notes": {
                      "type": "string",
                      "description": "Blind-safe stream notes.",
                  },
              },
          },
          "TelemetrySection": {
              "type": "object",
              "additionalProperties": False,
              "description": "Event and entity telemetry streams.",
              "properties": {
                  "events": {
                      "type": "array",
                      "items": {"$ref": "#/$defs/TelemetryStream"},
                      "description": "Event log streams under EVENTS/.",
                  },
                  "entities": {
                      "type": "array",
                      "items": {"$ref": "#/$defs/TelemetryStream"},
                      "description": "Entity context streams under ENTITIES/.",
                  },
              },
          },
          "GoogleSecOpsRunFrequency": {
              "type": "object",
              "additionalProperties": False,
              "required": ["events"],
              "description": "Recommended Google SecOps replay cadence.",
              "properties": {
                  "events": {
                      "type": "string",
                      "description": "Replay frequency for event streams.",
                  },
                  "entities": {
                      "type": ["string", "null"],
                      "description": "Replay frequency for entity streams.",
                  },
              },
          },
          "GoogleSecOpsDetection": {
              "type": "object",
              "additionalProperties": False,
              "required": ["name"],
              "description": "Google SecOps YARA-L 2.0 detection rule entry.",
              "properties": {
                  "name": {
                      "type": "string",
                      "minLength": 1,
                      "description": "Rule name.",
                  },
                  "path": {
                      "type": ["string", "null"],
                      "description": "Optional relative path to .yl2 file.",
                  },
                  "live": {
                      "type": "boolean",
                      "description": "Whether live rule evaluation is enabled.",
                  },
                  "alerting": {
                      "type": "boolean",
                      "description": "Whether alerting is enabled.",
                  },
                  "notes": {
                      "type": "string",
                      "description": "Rule notes.",
                  },
              },
          },
          "GoogleSecOpsSavedSearch": {
              "type": "object",
              "additionalProperties": False,
              "required": ["name"],
              "description": "Saved UDM search definition.",
              "properties": {
                  "name": {"type": "string", "minLength": 1},
                  "creator": {"type": "string"},
                  "notes": {"type": "string"},
                  "query": {"type": ["string", "null"]},
              },
          },
          "GoogleSecOpsReferenceList": {
              "type": "object",
              "additionalProperties": False,
              "required": ["name"],
              "description": "Google SecOps reference list metadata.",
              "properties": {
                  "name": {"type": "string", "minLength": 1},
                  "type": {"type": "string"},
                  "notes": {"type": "string"},
              },
          },
          "GoogleSecOpsPlatform": {
              "type": "object",
              "additionalProperties": False,
              "description": "Google Security Operations platform bindings.",
              "properties": {
                  "run_frequency": {"$ref": "#/$defs/GoogleSecOpsRunFrequency"},
                  "data_rbac": {"type": ["string", "null"]},
                  "log_type_mappings": {
                      "type": "object",
                      "additionalProperties": {"type": "string"},
                  },
                  "detections": {
                      "type": "array",
                      "items": {"$ref": "#/$defs/GoogleSecOpsDetection"},
                  },
                  "saved_searches": {
                      "type": "array",
                      "items": {"$ref": "#/$defs/GoogleSecOpsSavedSearch"},
                  },
                  "reference_lists": {
                      "type": "array",
                      "items": {"$ref": "#/$defs/GoogleSecOpsReferenceList"},
                  },
                  "parser_extensions": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
              },
          },
          "DatabricksPlatform": {
              "type": "object",
              "additionalProperties": False,
              "description": "Databricks Unity Catalog OCSF Lakehouse bindings.",
              "properties": {
                  "catalog": {"type": "string"},
                  "schema_name": {"type": "string"},
                  "table_mappings": {
                      "type": "object",
                      "additionalProperties": {"type": "string"},
                  },
                  "detections": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "notes": {"type": "string"},
              },
          },
          "SigmaPlatform": {
              "type": "object",
              "additionalProperties": False,
              "description": "Sigma detection rule bindings.",
              "properties": {
                  "rules": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "notes": {"type": "string"},
              },
          },
          "SplunkPlatform": {
              "type": "object",
              "additionalProperties": False,
              "description": "Splunk sourcetype and search bindings.",
              "properties": {
                  "sourcetypes": {
                      "type": "object",
                      "additionalProperties": {"type": "string"},
                  },
                  "saved_searches": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "notes": {"type": "string"},
              },
          },
          "PlatformBindings": {
              "type": "object",
              "additionalProperties": False,
              "description": "Multi-platform ingestion and detection bindings.",
              "properties": {
                  "google_secops": {"$ref": "#/$defs/GoogleSecOpsPlatform"},
                  "databricks": {"$ref": "#/$defs/DatabricksPlatform"},
                  "sigma": {"$ref": "#/$defs/SigmaPlatform"},
                  "splunk": {"$ref": "#/$defs/SplunkPlatform"},
              },
          },
      },
  }


def build_eval_json_schema() -> dict[str, Any]:
  """Build Draft 2020-12 JSON Schema for `eval.yaml` benchmark specifications."""
  return {
      "$schema": JSON_SCHEMA_DRAFT_2020_12,
      "$id": "https://chronicle.github.io/logstory/schemas/eval.schema.json",
      "title": "SecurityUsecaseEval",
      "description": (
          "Held-out Blue Team Evaluation & Answer Key Schema (v2.0) for "
          "autonomous SOC agent benchmarking across Alert Triage, Threat "
          "Hunting, and Detection Engineering."
      ),
      "type": "object",
      "additionalProperties": False,
      "required": [
          "schema_version",
          "usecase_id",
          "threat_context",
          "tasks",
          "ground_truth",
          "compliance_gates",
      ],
      "properties": {
          "schema_version": {
              "type": "string",
              "const": SCHEMA_VERSION_V2,
              "description": "Evaluation schema version ('2.0').",
          },
          "usecase_id": {
              "type": "string",
              "pattern": USECASE_ID_PATTERN,
              "description": "Usecase identifier matching <USECASE>.md id.",
          },
          "threat_context": {"$ref": "#/$defs/ThreatContext"},
          "tasks": {"$ref": "#/$defs/EvaluationTasks"},
          "ground_truth": {"$ref": "#/$defs/GroundTruth"},
          "compliance_gates": {"$ref": "#/$defs/ComplianceGates"},
          "counterfactual_pair": {
              "oneOf": [
                  {"$ref": "#/$defs/CounterfactualPair"},
                  {"type": "null"},
              ],
              "description": "Optional Signal Detection Theory twin pairing.",
          },
          "reference_queries": {"$ref": "#/$defs/ReferenceQueries"},
      },
      "$defs": {
          "ThreatContext": {
              "type": "object",
              "additionalProperties": False,
              "required": ["grounding_tier"],
              "description": "Adversary, advisory, and MITRE ATT&CK context.",
              "properties": {
                  "grounding_tier": {
                      "type": "string",
                      "enum": [e.value for e in GroundingTier],
                  },
                  "difficulty_tier": {
                      "type": "string",
                      "enum": [e.value for e in DifficultyTier],
                  },
                  "threat_actor": {"type": ["string", "null"]},
                  "actor_aliases": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "campaign_name": {"type": ["string", "null"]},
                  "cisa_advisories": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "cve_ids": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "mitre_tactics": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "mitre_techniques": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "release_day": {"type": ["integer", "null"]},
                  "cohort": {"type": ["string", "null"]},
                  "notes": {"type": "string"},
              },
          },
          "AlertTriageTask": {
              "type": "object",
              "additionalProperties": False,
              "description": "Alert triage benchmark task configuration.",
              "properties": {
                  "enabled": {"type": "boolean"},
                  "case_id": {"type": ["string", "null"]},
                  "alert_ids": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "prompt": {"type": "string"},
                  "expected_skill": {"type": ["string", "null"]},
                  "skill_bindings": {
                      "type": "object",
                      "additionalProperties": {"type": "string"},
                  },
                  "time_horizon_hours": {"type": "integer"},
              },
          },
          "ThreatHuntTask": {
              "type": "object",
              "additionalProperties": False,
              "description": "Proactive threat hunt task configuration.",
              "properties": {
                  "enabled": {"type": "boolean"},
                  "prompt_unalerted": {"type": "string"},
                  "prompt_intel_driven": {"type": ["string", "null"]},
                  "expected_patient_zero": {"type": ["string", "null"]},
                  "expected_skill": {"type": ["string", "null"]},
                  "skill_bindings": {
                      "type": "object",
                      "additionalProperties": {"type": "string"},
                  },
                  "time_horizon_hours": {"type": "integer"},
              },
          },
          "DetectionEngineeringTask": {
              "type": "object",
              "additionalProperties": False,
              "description": "Detection engineering task configuration.",
              "properties": {
                  "enabled": {"type": "boolean"},
                  "prompt": {"type": "string"},
                  "target_techniques": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "reference_rules": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "expected_rule_count_min": {"type": "integer"},
                  "max_false_positives_on_paired_baseline": {"type": "integer"},
              },
          },
          "EvaluationTasks": {
              "type": "object",
              "additionalProperties": False,
              "description": "Multi-task Blue Team benchmark suite.",
              "properties": {
                  "alert_triage": {"$ref": "#/$defs/AlertTriageTask"},
                  "threat_hunt": {"$ref": "#/$defs/ThreatHuntTask"},
                  "detection_engineering": {"$ref": "#/$defs/DetectionEngineeringTask"},
              },
          },
          "KillChainStage": {
              "type": "object",
              "additionalProperties": False,
              "required": ["stage", "stream_id"],
              "description": "Single chronological attack stage.",
              "properties": {
                  "stage": {"type": "string", "minLength": 1},
                  "stream_id": {"type": "string", "minLength": 1},
                  "timestamp_utc": {"type": ["string", "null"]},
                  "tactic": {"type": ["string", "null"]},
                  "technique_id": {"type": ["string", "null"]},
                  "summary": {"type": "string"},
                  "key_evidence": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
              },
          },
          "AffectedAsset": {
              "type": "object",
              "additionalProperties": False,
              "required": ["hostname"],
              "description": "Affected enterprise asset and blast-radius cost.",
              "properties": {
                  "hostname": {"type": "string", "minLength": 1},
                  "criticality_tier": {
                      "type": "string",
                      "enum": [e.value for e in CriticalityTier],
                  },
                  "ip_addresses": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "role": {"type": "string"},
                  "patient_zero": {"type": "boolean"},
                  "blast_radius_fp_usd": {"type": "number"},
                  "blast_radius_fn_usd": {"type": "number"},
              },
          },
          "MaliciousIoc": {
              "type": "object",
              "additionalProperties": False,
              "required": ["type", "value"],
              "description": "Ground-truth malicious indicator of compromise.",
              "properties": {
                  "type": {"type": "string", "minLength": 1},
                  "value": {"type": "string", "minLength": 1},
                  "role": {"type": "string"},
                  "notes": {"type": "string"},
              },
          },
          "ChangeWindow": {
              "type": "object",
              "additionalProperties": False,
              "required": ["ticket_id"],
              "description": "Maintenance or change window record.",
              "properties": {
                  "ticket_id": {"type": "string", "minLength": 1},
                  "approved": {"type": "boolean"},
                  "start_utc": {"type": ["string", "null"]},
                  "end_utc": {"type": ["string", "null"]},
                  "summary": {"type": "string"},
              },
          },
          "BenignConfusers": {
              "type": "object",
              "additionalProperties": False,
              "description": "Benign confusers and signed OS LOLBins.",
              "properties": {
                  "signed_lolbins": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "internal_ips": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "change_window": {
                      "oneOf": [
                          {"$ref": "#/$defs/ChangeWindow"},
                          {"type": "null"},
                      ]
                  },
                  "admin_tools": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
              },
          },
          "EntitiesAndIocs": {
              "type": "object",
              "additionalProperties": False,
              "description": "Ground-truth entities, IOCs, and confusers.",
              "properties": {
                  "compromised_accounts": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "affected_assets": {
                      "type": "array",
                      "items": {"$ref": "#/$defs/AffectedAsset"},
                  },
                  "malicious_iocs": {
                      "type": "array",
                      "items": {"$ref": "#/$defs/MaliciousIoc"},
                  },
                  "benign_confusers": {"$ref": "#/$defs/BenignConfusers"},
              },
          },
          "GroundTruth": {
              "type": "object",
              "additionalProperties": False,
              "required": ["expected_disposition", "expected_verdict"],
              "description": "Ground-truth disposition, verdict, and timeline.",
              "properties": {
                  "expected_disposition": {
                      "type": "string",
                      "enum": [e.value for e in ExpectedDisposition],
                  },
                  "expected_verdict": {
                      "type": "string",
                      "enum": [e.value for e in ExpectedVerdict],
                  },
                  "severity": {"type": "string"},
                  "patient_zero_host": {"type": ["string", "null"]},
                  "patient_zero_account": {"type": ["string", "null"]},
                  "root_cause_summary": {"type": "string"},
                  "kill_chain": {
                      "type": "array",
                      "items": {"$ref": "#/$defs/KillChainStage"},
                  },
                  "entities_and_iocs": {"$ref": "#/$defs/EntitiesAndIocs"},
              },
          },
          "ExpectedActions": {
              "type": "object",
              "additionalProperties": False,
              "description": "Primary, secondary, and prohibited response actions.",
              "properties": {
                  "primary": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "secondary": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "prohibited": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
              },
          },
          "ComplianceGates": {
              "type": "object",
              "additionalProperties": False,
              "description": "Safety and SOP compliance requirements.",
              "properties": {
                  "requires_pre_containment_verification": {"type": "boolean"},
                  "requires_168h_horizon_widening": {"type": "boolean"},
                  "forbid_external_cti_on_internal_ips": {"type": "boolean"},
                  "forbid_lolbin_hash_blocking": {"type": "boolean"},
                  "respect_change_window": {"type": "boolean"},
                  "expected_actions": {"$ref": "#/$defs/ExpectedActions"},
              },
          },
          "CounterfactualPair": {
              "type": "object",
              "additionalProperties": False,
              "required": ["paired_usecase_id", "pair_relationship"],
              "description": "Counterfactual benign/malicious twin link.",
              "properties": {
                  "paired_usecase_id": {"type": "string", "minLength": 1},
                  "pair_relationship": {
                      "type": "string",
                      "enum": [e.value for e in PairRelationship],
                  },
                  "shared_entities": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "shared_telemetry_streams": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "discriminating_invariant": {"type": "string"},
              },
          },
          "ReferenceQueries": {
              "type": "object",
              "additionalProperties": False,
              "description": "Reference investigative queries by platform.",
              "properties": {
                  "google_secops_udm": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "google_secops_yaral": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "databricks_sql": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "sigma": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
                  "splunk_spl": {
                      "type": "array",
                      "items": {"type": "string"},
                  },
              },
          },
      },
  }


def export_json_schemas(output_dir: Path) -> tuple[Path, Path]:
  """Write `usecase.schema.json` and `eval.schema.json` to `output_dir`.

  Args:
    output_dir: Directory where JSON Schema files will be written.

  Returns:
    Tuple of `(usecase_schema_path, eval_schema_path)`.
  """
  target_dir = Path(output_dir)
  target_dir.mkdir(parents=True, exist_ok=True)
  usecase_path = target_dir / "usecase.schema.json"
  eval_path = target_dir / "eval.schema.json"

  usecase_path.write_text(
      json.dumps(build_usecase_json_schema(), indent=2) + "\n",
      encoding="utf-8",
  )
  eval_path.write_text(
      json.dumps(build_eval_json_schema(), indent=2) + "\n",
      encoding="utf-8",
  )
  return usecase_path, eval_path
