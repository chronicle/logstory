# Open Security Usecase & Blue Team Benchmark Metadata Standard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the vendor-neutral Open Security Usecase & Blue Team Evaluation Metadata Standard (`schema_version: "2.0"`) in `logstory` (models, JSON Schema Draft 2020-12 exporter, 5-gate validator with anti-spoiler verification, v1/v2 doc generator shim, CLI subcommands `validate`, `inspect`, `export-schemas`, and `replay usecase --with-paired-baselines`) and migrate the two built-in `logstory` usecases plus all 47 usecases in `logstory_usecases` to v2 `<USECASE>.md` + `eval.yaml`.

**Architecture:** Two-file physical split per usecase package (`<USECASE>/<USECASE>.md` for telemetry/replay/platform bindings with `<!-- BEGIN_SOLUTION -->` anti-spoiler boundary, and `<USECASE>/eval.yaml` for held-out multi-task Blue Team ground truth and Signal Detection Theory counterfactual pairs). Implemented in pure Python 3.10+ stdlib (`dataclasses`, `enum`, `typing`, `json`, `re`, `pathlib`) + `yaml` / `typer` so `logstory` requires zero additional third-party runtime dependencies.

**Tech Stack:** Python 3.10+, `dataclasses`, `oyaml`/`PyYAML`, `typer`, `pytest`, `ruff`, `pyink` (2-space indentation, 88-character line length, Google-style docstrings).

**Spec:** `docs/superpowers/specs/2026-11-05-usecase-metadata-standard-design.md`

---

## Global Constraints

1. **No emojis anywhere:** Never use emojis in code, comments, CLI output, documentation, tests, or commit messages.
2. **Formatting & Linting:** All Python files in `logstory` MUST use **2-space indentation**, `line-length = 88`, and Google-style docstrings (`pyink` + `ruff check`).
3. **Git Staging Hygiene:** Never run `git add .`, `git add -A`, or `git add --all`. Always check `git status` and stage explicit file paths (`git add <file1> <file2>`).
4. **Zero New Runtime Dependencies:** `.venv` in `logstory` has `typer`, `oyaml`/`yaml`, and `pytest` installed (`pydantic`, `jsonschema`, and `jinja2` are not installed in the base virtualenv). Implement `src/logstory/schema/models.py` and `src/logstory/schema/validator.py` using stdlib `dataclasses`, `enum`, `typing`, `json`, and `re` plus `yaml`, and provide a built-in Jinja2-free fallback renderer in `usecases/generate_usecase_docs.py` when `jinja2` is not installed.
5. **Product Naming:** Use **Google Security Operations** (or **SecOps**) in documentation and descriptions; reserve `"Chronicle"` only for API/IAM technical identifiers.

---

## File Structure

### `logstory` Worktree (`/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2`)
- **Create:** `src/logstory/schema/__init__.py` - Public package exports for schema models, parser, JSON Schema exporter, and 5-gate validator.
- **Create:** `src/logstory/schema/models.py` - Strongly typed Python dataclasses, enums, dict validation/serialization, `parse_usecase_package`, and Draft 2020-12 JSON Schema generation (`export_json_schemas`).
- **Create:** `src/logstory/schema/validator.py` - 5-gate validator (`validate_usecase_package`, `validate_usecase_corpus`) including anti-spoiler leakage detection (`<!-- BEGIN_SOLUTION -->`) and counterfactual pair verification.
- **Create:** `schemas/usecase.schema.json` - Exported JSON Schema (Draft 2020-12) for `<USECASE>.md` YAML frontmatter.
- **Create:** `schemas/eval.schema.json` - Exported JSON Schema (Draft 2020-12) for `eval.yaml`.
- **Modify:** `usecases/generate_usecase_docs.py` - Add `normalize_frontmatter_for_template(frontmatter: dict) -> dict` v1/v2 compatibility shim and a stdlib fallback renderer when `jinja2` is not installed.
- **Modify:** `usecases/usecase_template.j2` - Render OCSF stream mappings, paired baselines, and multi-platform (`google_secops`, `databricks`, `sigma`, `splunk`) sections alongside legacy tables.
- **Modify:** `usecases/NETWORK_ANALYSIS/NETWORK_ANALYSIS.md` and create `usecases/NETWORK_ANALYSIS/eval.yaml` (plus symlink in `src/logstory/usecases/NETWORK_ANALYSIS/eval.yaml`).
- **Modify:** `usecases/RULES_SEARCH_WORKSHOP/RULES_SEARCH_WORKSHOP.md` and create `usecases/RULES_SEARCH_WORKSHOP/eval.yaml`.
- **Modify:** `src/logstory/logstory.py` - Add `usecases validate`, `usecases inspect`, `usecases export-schemas`, and `--with-paired-baselines` on `replay usecase`.
- **Modify:** `pyproject.toml` - Include `"usecases/**/*.yaml"`, `"usecases/**/*.j2"`, and `"schemas/*.json"` in `[tool.setuptools.package-data]`.
- **Create:** `tests/test_usecase_schema_models.py` - Unit tests for schema models, v1/v2 parsing, `<!-- BEGIN_SOLUTION -->` splitting, and JSON Schema export.
- **Create:** `tests/test_usecase_validator.py` - Unit tests for all 5 validation gates and anti-spoiler checks.
- **Create:** `tests/test_generate_usecase_docs.py` - Unit tests for v1/v2 doc generation and normalization shim.
- **Create:** `tests/test_usecase_cli_metadata.py` - CLI tests for `usecases validate`, `usecases inspect --blind`, `usecases export-schemas`, and `replay usecase --with-paired-baselines`.

### `logstory_usecases` Worktree (`/usr/local/google/home/dandye/Projects/logstory_usecases__worktrees/schema__usecase-metadata-v2`)
- **Create:** `scripts/migrate_usecases_v2.py` - Deterministic migration script transforming all 43 attack scenarios and 4 `CYMBAL_BASELINE_*` composable baselines to v2 `<USECASE>.md` + `eval.yaml`.
- **Create:** `schemas/usecase.schema.json` and `schemas/eval.schema.json` - Synchronized JSON Schemas.
- **Modify/Create:** `<USECASE>/<USECASE>.md` and `<USECASE>/eval.yaml` across all 47 usecase directories.

---

### Task 1: Core Schema Models, Parser, and JSON Schema Exporter

**Files:**
- Create: `src/logstory/schema/__init__.py`
- Create: `src/logstory/schema/models.py`
- Create: `schemas/usecase.schema.json`
- Create: `schemas/eval.schema.json`
- Test: `tests/test_usecase_schema_models.py`

- [ ] **Step 1: Write the failing unit tests in `tests/test_usecase_schema_models.py`**

Create `tests/test_usecase_schema_models.py` testing:
1. Validating and serializing a complete v2 `SecurityUsecaseManifest` (including OKF v0.2 provenance fields `schema_version`, `id`, `title`, `version`, `created`, `updated`, `author`, `license`, `description`, `tags`, `environment`, `telemetry`, and `platforms` for `google_secops`, `databricks`, `sigma`, `splunk`).
2. Validating and serializing a complete v2 `SecurityUsecaseEval` (including `threat_context`, `tasks`, `ground_truth`, `compliance_gates`, `counterfactual_pair`, and `reference_queries`).
3. Rejecting unknown/extra keys and invalid enum values with descriptive `SchemaValidationError` exceptions.
4. Splitting `<USECASE>.md` on `<!-- BEGIN_SOLUTION -->` via `parse_usecase_package(usecase_dir, blind=True)` vs `blind=False`.
5. Generating deterministic Draft 2020-12 JSON Schemas (`usecase.schema.json` and `eval.schema.json`) via `export_json_schemas(output_dir)`.

- [ ] **Step 2: Run pytest to verify the new test file fails**

Run:
```bash
/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2/.venv/bin/pytest tests/test_usecase_schema_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'logstory.schema'`

- [ ] **Step 3: Implement `src/logstory/schema/models.py` and `src/logstory/schema/__init__.py`, and export `schemas/*.schema.json`**

Implement in `src/logstory/schema/models.py`:
- Custom `SchemaValidationError(ValueError)` with field path reporting.
- Enum classes (`ScenarioType`, `GroundingTier`, `ExpectedDisposition`, `ExpectedVerdict`, `CriticalityTier`, `PairRelationship`, `DifficultyTier`).
- Dataclasses with `.from_dict(data: dict)` (enforcing required fields, types, and rejecting unknown keys) and `.to_dict() -> dict`:
  - Manifest models: `EnvironmentContext`, `TimestampPolicy`, `TelemetryStream`, `TelemetrySection`, `GoogleSecOpsRunFrequency`, `GoogleSecOpsDetection`, `GoogleSecOpsSavedSearch`, `GoogleSecOpsReferenceList`, `GoogleSecOpsPlatform`, `DatabricksPlatform`, `SigmaPlatform`, `SplunkPlatform`, `PlatformBindings`, `SecurityUsecaseManifest`.
  - Eval models: `ThreatContext`, `AlertTriageTask`, `ThreatHuntTask`, `DetectionEngineeringTask`, `EvaluationTasks`, `KillChainStage`, `AffectedAsset`, `MaliciousIoc`, `ChangeWindow`, `BenignConfusers`, `EntitiesAndIocs`, `GroundTruth`, `ExpectedActions`, `ComplianceGates`, `CounterfactualPair`, `ReferenceQueries`, `SecurityUsecaseEval`.
  - Package container: `ParsedUsecasePackage` (`usecase_dir`, `schema_version`, `manifest`, `raw_frontmatter`, `public_markdown_body`, `solution_markdown_body`, `eval_data`).
- Functions:
  - `split_frontmatter_and_body(content: str) -> tuple[dict[str, Any], str]`
  - `split_solution_section(markdown_body: str) -> tuple[str, str | None]` (splits on `<!-- BEGIN_SOLUTION -->`)
  - `parse_usecase_package(usecase_dir: Path, blind: bool = False) -> ParsedUsecasePackage`
  - `build_usecase_json_schema() -> dict[str, Any]` and `build_eval_json_schema() -> dict[str, Any]` (Draft 2020-12 JSON Schemas with `$schema: "https://json-schema.org/draft/2020-12/schema"`, `additionalProperties: false`, enum constraints, and property descriptions)
  - `export_json_schemas(output_dir: Path) -> tuple[Path, Path]`

- [ ] **Step 4: Run pytest, ruff, and pyink on Task 1 files**

Run:
```bash
WORKTREE_DIR="/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2"
"$WORKTREE_DIR/.venv/bin/pytest" "$WORKTREE_DIR/tests/test_usecase_schema_models.py" -v
"$WORKTREE_DIR/.venv/bin/ruff" check "$WORKTREE_DIR/src/logstory/schema" "$WORKTREE_DIR/tests/test_usecase_schema_models.py"
"$WORKTREE_DIR/.venv/bin/pyink" --check "$WORKTREE_DIR/src/logstory/schema" "$WORKTREE_DIR/tests/test_usecase_schema_models.py"
```
Expected: All tests pass, 0 ruff warnings, pyink formatted cleanly.

- [ ] **Step 5: Stage and commit Task 1 files explicitly**

Run:
```bash
git status
git add src/logstory/schema/__init__.py src/logstory/schema/models.py schemas/usecase.schema.json schemas/eval.schema.json tests/test_usecase_schema_models.py
git commit -m "Add v2 security usecase and Blue Team eval schema models and JSON schemas"
```

---

### Task 2: 5-Gate Validator and Anti-Spoiler Checker

**Files:**
- Create: `src/logstory/schema/validator.py`
- Modify: `src/logstory/schema/__init__.py`
- Test: `tests/test_usecase_validator.py`

- [ ] **Step 1: Write failing unit tests in `tests/test_usecase_validator.py`**

Create `tests/test_usecase_validator.py` covering:
1. **Gate 1 (Schema & Provenance):** Valid v2 package passes; missing required OKF v0.2 fields (`license`, `version`, `author`) or invalid `eval.yaml` enum fails with `gate="G1_SCHEMA"`.
2. **Gate 2 (Stream & File Integrity):** Missing on-disk log file referenced by `telemetry.events[].path`, missing detection rule referenced by `platforms.google_secops.detections[].path`, or `kill_chain[].stream_id` referencing an unknown `stream_id` fails with `gate="G2_INTEGRITY"`.
3. **Gate 3 (Anti-Spoiler Leakage):**
   - Ground-truth key (`ground_truth`, `kill_chain`, `malicious_iocs`, `compliance_gates`) placed in `<USECASE>.md` frontmatter fails with `gate="G3_ANTI_SPOILER"`.
   - Any non-trivial IOC value from `eval.yaml -> ground_truth.entities_and_iocs.malicious_iocs[].value`, compromised account from `compromised_accounts`, or CISA advisory ID from `threat_context.cisa_advisories` appearing in `<USECASE>.md` frontmatter (`title`, `description`, `tags`, `notes`) or in the Markdown body above `<!-- BEGIN_SOLUTION -->` fails with `gate="G3_ANTI_SPOILER"`.
   - The same IOC/advisory appearing *below* `<!-- BEGIN_SOLUTION -->` passes Gate 3.
4. **Gate 4 (Counterfactual Twin Consistency):**
   - When `eval.yaml` specifies `counterfactual_pair.paired_usecase_id` with `pair_relationship == "malicious_variant_of_benign_baseline"`, `<USECASE>.md` must include that baseline in `environment.paired_baselines` (unless the paired usecase is an attack variant and this usecase is a `benign_baseline`).
   - When `corpus_root` is provided, verify that the paired directory exists on disk.
5. **Gate 5 (v1 Legacy Compatibility Mode):**
   - A legacy v1 `<USECASE>.md` (without `schema_version: "2.0"`) passes with a warning when `strict_v2=False`, and fails with `gate="G5_LEGACY_V1"` when `strict_v2=True`.

- [ ] **Step 2: Run pytest to verify `tests/test_usecase_validator.py` fails**

Run:
```bash
/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2/.venv/bin/pytest tests/test_usecase_validator.py -v
```
Expected: `ImportError` / `ModuleNotFoundError`.

- [ ] **Step 3: Implement `src/logstory/schema/validator.py` and export from `src/logstory/schema/__init__.py`**

Implement in `src/logstory/schema/validator.py`:
- `ValidationFinding` (`gate: str`, `severity: Literal["ERROR", "WARNING"]`, `message: str`, `path: str | None = None`)
- `UsecaseValidationResult` (`usecase_id: str`, `usecase_dir: Path`, `schema_version: str`, `findings: list[ValidationFinding]`, property `is_valid -> bool`, property `errors -> list[ValidationFinding]`, property `warnings -> list[ValidationFinding]`, `.to_dict() -> dict`)
- `validate_usecase_package(usecase_dir: Path, strict_v2: bool = False, corpus_root: Path | None = None) -> UsecaseValidationResult`
- `validate_usecase_corpus(corpus_dir: Path, strict_v2: bool = False) -> list[UsecaseValidationResult]`

- [ ] **Step 4: Run pytest, ruff, and pyink on Task 2 files**

Run:
```bash
WORKTREE_DIR="/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2"
"$WORKTREE_DIR/.venv/bin/pytest" "$WORKTREE_DIR/tests/test_usecase_validator.py" -v
"$WORKTREE_DIR/.venv/bin/ruff" check "$WORKTREE_DIR/src/logstory/schema" "$WORKTREE_DIR/tests/test_usecase_validator.py"
"$WORKTREE_DIR/.venv/bin/pyink" --check "$WORKTREE_DIR/src/logstory/schema" "$WORKTREE_DIR/tests/test_usecase_validator.py"
```
Expected: All tests pass, 0 lint or formatting errors.

- [ ] **Step 5: Stage and commit Task 2 files explicitly**

Run:
```bash
git status
git add src/logstory/schema/__init__.py src/logstory/schema/validator.py tests/test_usecase_validator.py
git commit -m "Add 5-gate usecase package validator and anti-spoiler checker"
```

---

### Task 3: Documentation Generator v1/v2 Shim and Built-in `logstory` Usecase Migration

**Files:**
- Modify: `usecases/generate_usecase_docs.py`
- Modify: `usecases/usecase_template.j2`
- Modify: `usecases/NETWORK_ANALYSIS/NETWORK_ANALYSIS.md`
- Create: `usecases/NETWORK_ANALYSIS/eval.yaml`
- Create: `src/logstory/usecases/NETWORK_ANALYSIS/eval.yaml` (symlink to `../../../../usecases/NETWORK_ANALYSIS/eval.yaml`)
- Modify: `usecases/RULES_SEARCH_WORKSHOP/RULES_SEARCH_WORKSHOP.md`
- Create: `usecases/RULES_SEARCH_WORKSHOP/eval.yaml`
- Test: `tests/test_generate_usecase_docs.py`

- [ ] **Step 1: Write failing unit tests in `tests/test_generate_usecase_docs.py`**

Create `tests/test_generate_usecase_docs.py` testing:
1. `normalize_frontmatter_for_template(frontmatter)` converts a v2 `SecurityUsecaseManifest` dict into backwards-compatible template variables (`events`, `entities`, `rules`, `saved_searches`, `reference_lists`, `run_frequency`, `data_rbac`) while preserving `telemetry`, `platforms`, `environment`, `schema_version`, `version`, `author`, and `license`.
2. `generate_usecase_doc` works for both v1 and v2 frontmatter (using Jinja2 if installed, or the built-in stdlib template renderer fallback when Jinja2 is absent) and renders OCSF classes, paired baselines, and platform bindings (`Google SecOps`, `Databricks`, `Sigma`, `Splunk`) without spoilers.
3. Both built-in usecases (`usecases/NETWORK_ANALYSIS` and `usecases/RULES_SEARCH_WORKSHOP`) validate cleanly under `validate_usecase_package(..., strict_v2=True)`.

- [ ] **Step 2: Run pytest to verify `tests/test_generate_usecase_docs.py` fails**

Run:
```bash
/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2/.venv/bin/pytest tests/test_generate_usecase_docs.py -v
```
Expected: Fails because `normalize_frontmatter_for_template` does not exist yet and built-in usecases are still v1.

- [ ] **Step 3: Update `usecases/generate_usecase_docs.py`, `usecases/usecase_template.j2`, and migrate `NETWORK_ANALYSIS` and `RULES_SEARCH_WORKSHOP` to v2**

In `usecases/generate_usecase_docs.py`:
- Add `normalize_frontmatter_for_template(frontmatter: dict) -> dict` mapping v2 `telemetry.events`, `telemetry.entities`, and `platforms.google_secops` into legacy keys when `schema_version == "2.0"`.
- Make `from jinja2 import Environment, FileSystemLoader` conditional (`try ... except ImportError`) and implement `_render_without_jinja2(normalized: dict) -> str` producing identical Markdown tables and sections when `jinja2` is not installed in `.venv`.
- Migrate `usecases/NETWORK_ANALYSIS/NETWORK_ANALYSIS.md` and `usecases/RULES_SEARCH_WORKSHOP/RULES_SEARCH_WORKSHOP.md` to `schema_version: "2.0"`, placing any detailed exercise notes below `<!-- BEGIN_SOLUTION -->`, and create `usecases/NETWORK_ANALYSIS/eval.yaml` (plus symlink in `src/logstory/usecases/NETWORK_ANALYSIS/eval.yaml`) and `usecases/RULES_SEARCH_WORKSHOP/eval.yaml`.

- [ ] **Step 4: Run pytest, ruff, and pyink on Task 3 files**

Run:
```bash
WORKTREE_DIR="/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2"
"$WORKTREE_DIR/.venv/bin/pytest" "$WORKTREE_DIR/tests/test_generate_usecase_docs.py" "$WORKTREE_DIR/tests/test_cli.py" -v
"$WORKTREE_DIR/.venv/bin/ruff" check "$WORKTREE_DIR/usecases/generate_usecase_docs.py" "$WORKTREE_DIR/tests/test_generate_usecase_docs.py"
"$WORKTREE_DIR/.venv/bin/pyink" --check "$WORKTREE_DIR/usecases/generate_usecase_docs.py" "$WORKTREE_DIR/tests/test_generate_usecase_docs.py"
```
Expected: All tests pass, 0 lint/format errors.

- [ ] **Step 5: Stage and commit Task 3 files explicitly**

Run:
```bash
git status
git add usecases/generate_usecase_docs.py usecases/usecase_template.j2 usecases/NETWORK_ANALYSIS/NETWORK_ANALYSIS.md usecases/NETWORK_ANALYSIS/eval.yaml src/logstory/usecases/NETWORK_ANALYSIS/eval.yaml usecases/RULES_SEARCH_WORKSHOP/RULES_SEARCH_WORKSHOP.md usecases/RULES_SEARCH_WORKSHOP/eval.yaml tests/test_generate_usecase_docs.py
git commit -m "Upgrade generate_usecase_docs for v2 manifests and migrate built-in usecases"
```

---

### Task 4: CLI Subcommands (`validate`, `inspect`, `export-schemas`) and `--with-paired-baselines`

**Files:**
- Modify: `src/logstory/logstory.py`
- Modify: `pyproject.toml`
- Test: `tests/test_usecase_cli_metadata.py`

- [ ] **Step 1: Write failing CLI tests in `tests/test_usecase_cli_metadata.py`**

Create `tests/test_usecase_cli_metadata.py` testing via `CliRunner`:
1. `logstory usecases validate <path>` on a single usecase directory and on a corpus directory, with `--strict-v2` and `--format json` / `--format text`. Verify exit code `0` on valid packages and exit code `1` when any gate fails.
2. `logstory usecases inspect <usecase_or_path> --blind --format json` returns `manifest` and `public_markdown_body` (with zero content from below `<!-- BEGIN_SOLUTION -->` and `eval_data: null`), whereas `--include-eval` includes `eval_data` and `solution_markdown_body`.
3. `logstory usecases export-schemas --output-dir <tmp_dir>` writes `usecase.schema.json` and `eval.schema.json`.
4. `logstory replay usecase <USECASE> --with-paired-baselines --local-file-output --no-get` reads `environment.paired_baselines` from `<USECASE>.md` and replays each paired baseline usecase prior to (or alongside) the target usecase, deduplicating baselines if multiple are listed.

- [ ] **Step 2: Run pytest to verify `tests/test_usecase_cli_metadata.py` fails**

Run:
```bash
/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2/.venv/bin/pytest tests/test_usecase_cli_metadata.py -v
```
Expected: Fails because the new CLI subcommands and `--with-paired-baselines` option do not exist yet.

- [ ] **Step 3: Implement CLI subcommands in `src/logstory/logstory.py` and update `pyproject.toml`**

In `src/logstory/logstory.py`:
- Add `@usecases_app.command("validate")` accepting `path: str | None = typer.Argument(None)`, `--strict-v2: bool = typer.Option(False, "--strict-v2")`, `--format: str = typer.Option("text", "--format")` (`text` or `json`). Resolves either a filesystem path or an installed usecase name (or all installed usecases if omitted).
- Add `@usecases_app.command("inspect")` accepting `usecase: str = typer.Argument(...)`, `--blind/--include-eval: bool = typer.Option(True, "--blind/--include-eval")`, `--format: str = typer.Option("json", "--format")` (`json` or `text`).
- Add `@usecases_app.command("export-schemas")` accepting `--output-dir: str = typer.Option("schemas", "--output-dir")`.
- Add `with_paired_baselines: bool = typer.Option(False, "--with-paired-baselines", help="Also replay composable paired baselines declared in environment.paired_baselines")` to `@replay_app.command("usecase")`. Add helper `_get_paired_baselines(usecase: str) -> list[str]` that reads `<USECASE>/<USECASE>.md` frontmatter and returns `environment.paired_baselines`.
- In `pyproject.toml`, update `[tool.setuptools.package-data]` to include `"usecases/**/*.yaml"`, `"usecases/**/*.j2"`, and `"schemas/*.json"`.

- [ ] **Step 4: Run full pytest suite, ruff, and pyink in `logstory`**

Run:
```bash
WORKTREE_DIR="/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2"
"$WORKTREE_DIR/.venv/bin/pytest" "$WORKTREE_DIR/tests" -v
"$WORKTREE_DIR/.venv/bin/ruff" check "$WORKTREE_DIR/src" "$WORKTREE_DIR/tests" "$WORKTREE_DIR/usecases/generate_usecase_docs.py"
"$WORKTREE_DIR/.venv/bin/pyink" --check "$WORKTREE_DIR/src" "$WORKTREE_DIR/tests" "$WORKTREE_DIR/usecases/generate_usecase_docs.py"
```
Expected: All unit and CLI tests pass with coverage >= 80%, 0 ruff or pyink errors.

- [ ] **Step 5: Stage and commit Task 4 files explicitly**

Run:
```bash
git status
git add pyproject.toml src/logstory/logstory.py tests/test_usecase_cli_metadata.py
git commit -m "Add usecases validate, inspect, export-schemas CLI and --with-paired-baselines"
```

---

### Task 5: Migrate All 47 Scenarios in `logstory_usecases` to v2 `<USECASE>.md` + `eval.yaml`

**Files (in `/usr/local/google/home/dandye/Projects/logstory_usecases__worktrees/schema__usecase-metadata-v2`):**
- Create: `scripts/migrate_usecases_v2.py`
- Create: `schemas/usecase.schema.json`
- Create: `schemas/eval.schema.json`
- Modify/Create: `<USECASE>/<USECASE>.md` and `<USECASE>/eval.yaml` across all 47 usecase directories (`43` attack scenarios + `4` `CYMBAL_BASELINE_*` composable baselines)
- Test (in `logstory`): `tests/test_logstory_usecases_corpus_v2.py`

- [ ] **Step 1: Create isolated Git worktree `/usr/local/google/home/dandye/Projects/logstory_usecases__worktrees/schema__usecase-metadata-v2`**

Run:
```bash
USECASES_MAIN="/usr/local/google/home/dandye/Projects/logstory_usecases__worktrees/main"
USECASES_WT="/usr/local/google/home/dandye/Projects/logstory_usecases__worktrees/schema__usecase-metadata-v2"
git -C "$USECASES_MAIN" worktree add -b schema__usecase-metadata-v2 "$USECASES_WT" main
```

- [ ] **Step 2: Write `scripts/migrate_usecases_v2.py` in `logstory_usecases__worktrees/schema__usecase-metadata-v2`**

Write `scripts/migrate_usecases_v2.py` that:
1. Parses existing `<USECASE>/<USECASE>.md` frontmatter and Markdown body, `RULES/*.yl2` metadata (`meta:` section including MITRE `ta`, `t1`, `author`, `severity`, `priority`, and events/outcomes), `THREAT_ACTORS.md`, `CYMBAL_BASELINE.md`, `RELEASE_PLAN.md`, and the 47-scenario metadata table (`expected_skills`, `forbid_lolbin_hashes`, `requires_168h_horizon`, `change_window`, `compromised_accounts`, `affected_assets`, `malicious_iocs`, `kill_chain`).
2. Maps every Google SecOps log type (`POWERSHELL`, `WINDOWS_SYSMON`, `WINDOWS_DEFENDER_AV`, `WINEVTLOG`, `WINDOWS_AD`, `GCP_CLOUDAUDIT`, `WORKSPACE_ACTIVITY`, `WORKSPACE_USERS`, `SURICATA_EVE`, `BRO_JSON`, `LIN_AUDITD`, `OSQUERY`, `PAN_FIREWALL`, `OKTA`, `OFFICE_365`, `AWS_CLOUDTRAIL`, `AZURE_AD`, `AZURE_AD_CONTEXT`, `ASSET_CONTEXT`, `USER_CONTEXT`, `CROWDSTRIKE_FALCON`, `FIREEYE_HX`, etc.) to its canonical OCSF v1.3+ category/class (`ocsf_category_uid`, `ocsf_class_uid`, `ocsf_class_name`) and Databricks Unity Catalog OCSF table (`secops_ocsf.<table_name>`).
3. Rewrites `<USECASE>/<USECASE>.md` with `schema_version: "2.0"` frontmatter, neutral `description` (scrubbing spoiler IOCs/actor names/CISA advisory IDs from the public description and placing the full analyst walkthrough and IOC tables below `<!-- BEGIN_SOLUTION -->`), and writes `<USECASE>/eval.yaml` for each of the 47 directories.
4. Copies `schemas/usecase.schema.json` and `schemas/eval.schema.json` into `logstory_usecases/schemas/`.

- [ ] **Step 3: Run `scripts/migrate_usecases_v2.py` and validate all 47 usecases with `logstory usecases validate --strict-v2`**

Run:
```bash
WORKTREE_DIR="/usr/local/google/home/dandye/Projects/logstory__worktrees/schema__usecase-metadata-v2"
USECASES_WT="/usr/local/google/home/dandye/Projects/logstory_usecases__worktrees/schema__usecase-metadata-v2"
"$WORKTREE_DIR/.venv/bin/python" "$USECASES_WT/scripts/migrate_usecases_v2.py" "$USECASES_WT"
"$WORKTREE_DIR/.venv/bin/logstory" usecases validate "$USECASES_WT" --strict-v2
```
Expected: `47/47 usecases passed all 5 validation gates (0 errors, 0 warnings)`.

- [ ] **Step 4: Add corpus integration test `tests/test_logstory_usecases_corpus_v2.py` in `logstory` and run full test suites**

Create `tests/test_logstory_usecases_corpus_v2.py` in `logstory` (skipping cleanly if `logstory_usecases` directory is not mounted, and validating all 47 scenarios when present) and run `pytest`, `ruff`, and `pyink`.

- [ ] **Step 5: Stage and commit changes in both worktrees explicitly**

In `logstory_usecases__worktrees/schema__usecase-metadata-v2`:
- Stage `schemas/usecase.schema.json`, `schemas/eval.schema.json`, `scripts/migrate_usecases_v2.py`, and all 47 `<USECASE>/<USECASE>.md` and `<USECASE>/eval.yaml` files by explicit path and commit.
In `logstory__worktrees/schema__usecase-metadata-v2`:
- Stage `tests/test_logstory_usecases_corpus_v2.py` and commit.
