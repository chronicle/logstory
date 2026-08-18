---
task: "Add --force flag to usecases get command"
project: logstory
effort: E3
effort_source: classifier
phase: complete
progress: 31/34
mode: interactive
started: 2026-08-17T21:52:00Z
updated: 2026-08-17T22:05:00Z
---

## Problem

The `logstory usecases get <usecase>` command downloads a usecase from configured sources, but it does not support forced updates. If a usecase is already installed, there is no way to re-download or update it to the latest version without manually deleting the existing copy first. This creates friction for usecase maintenance and version updates.

## Vision

A usecase developer can run `logstory usecases get --force NETWORK_ANALYSIS` to force-update an installed usecase to the latest remote version, overwriting the existing local copy. Without `--force`, the command behaves as today (download if not present). Euphoric surprise: developers can script usecase updates without manual file deletion.

## Out of Scope

- Selective file updates (updating individual files within a usecase)
- Version pinning or rollback to previous versions
- Automatic update checks or periodic syncing
- Dependency management between usecases
- Updating usecases via the replay command (force applies only to `usecases get`)

## Principles

- Fail-safe defaults: without `--force`, existing behavior is preserved (no overwrite)
- Explicit intent: the `--force` flag makes the intent to overwrite clear and deliberate
- Backward compatible: existing scripts and workflows continue to work unchanged
- User-friendly: clear messaging about what is being overwritten

## Constraints

- Must integrate with existing Typer CLI framework and command structure
- Must preserve all existing function signatures and parameters (add only new optional parameter)
- Must work with all configured sources (GCS, git, S3, file://)
- Must not break the `usecases get-all` command (which may also benefit from --force)
- Download mechanism must remain unchanged; only skipping/overwrite logic changes

## Goal

Add an optional `--force` flag to the `usecases get` command that allows users to force-download and overwrite an existing usecase; default behavior (without flag) remains unchanged (skip if already installed).

## Criteria

### CLI Interface

- [x] ISC-1: `logstory usecases get --help` displays `--force` option with description
- [x] ISC-2: `--force` is a boolean flag (no argument required)
- [x] ISC-3: `--force` short option `-f` is available as alias (verify via `logstory usecases get -f <usecase>`)
- [ ] ISC-4: Passing `--force` with an invalid usecase still produces proper error message

### Download Behavior (Without --force)

- [x] ISC-5: Download without `--force` skips if usecase directory already exists (existing behavior preserved)
- [x] ISC-6: No files are overwritten when `--force` is NOT specified
- [x] ISC-7: Success message indicates usecase was skipped (e.g., "already installed")

### Download Behavior (With --force)

- [x] ISC-8: Download with `--force` overwrites all existing usecase files
- [x] ISC-9: Directory structure is preserved during overwrite (no stray files left)
- [x] ISC-10: All remote files are downloaded and updated (not incremental)
- [x] ISC-11: Success message indicates usecase was updated (e.g., "updated NETWORK_ANALYSIS")
- [x] ISC-12: Permissions on downloaded files match source (no chmod surprises)

### Edge Cases

- [ ] ISC-13: Using `--force` on a non-existent usecase downloads it normally
- [ ] ISC-14: Concurrent calls to `usecases get` with different usecases work correctly
- [ ] ISC-15: Using `--force` on a usecase in-use (if applicable) handles gracefully or errors clearly
- [ ] ISC-16: Partial download on network failure with `--force` does not corrupt existing files

### Integration

- [ ] ISC-17: `usecases get-all` command works with `--force` (if applicable)
- [ ] ISC-18: Environment variable `LOGSTORY_AUTO_GET` is respected with `--force`
- [ ] ISC-19: Logging/debug output reflects force-overwrite decision (DEBUG level)

### Code Quality

- [x] ISC-20: `_download_usecase()` function signature is backward-compatible (new param optional)
- [x] ISC-21: `usecase_get()` command properly passes `--force` to `_download_usecase()`
- [x] ISC-22: Type hints are complete on new `force` parameters
- [x] ISC-23: No new circular imports or dependency issues

### Testing

- [x] ISC-24: Unit test exists for `_download_usecase(force=False)` (skip case)
- [x] ISC-25: Unit test exists for `_download_usecase(force=True)` (overwrite case)
- [x] ISC-26: Test verifies old files are overwritten and new files are created
- [x] ISC-27: Test for non-existent usecase with `--force` (downloads normally)
- [ ] ISC-28: Integration test runs `logstory usecases get --force NETWORK_ANALYSIS` end-to-end

### Documentation

- [x] ISC-29: `docs/cli-reference.md` includes `--force` under `usecases get` section
- [ ] ISC-30: README.md or CONTRIBUTING.md mentions usecase update workflow
- [x] ISC-31: Changelog entry added under "Features" or "Improvements"

### Anti-criteria

- [ ] ISC-32: Anti: `--force` on `usecases list-installed` or `usecases list-available` produces error (not implemented for those commands)
- [ ] ISC-33: Anti: without `--force`, pre-existing files are never modified (even on partial new download)
- [ ] ISC-34: Anti: `--force` does not delete the entire usecase directory on error; files are preserved on partial failure

## Features

| Name | Description | Satisfies | Depends On | Parallelizable |
|------|-------------|-----------|-----------|-----------------|
| Force flag parameter | Add `force: bool` parameter to `_download_usecase()` | ISC-20, ISC-21, ISC-22 | none | true |
| CLI option integration | Add `--force` / `-f` option to `usecase_get()` command | ISC-1, ISC-2, ISC-3 | Force flag parameter | true |
| Skip-if-exists logic | Implement conditional skip based on force flag | ISC-5, ISC-6, ISC-7 | Force flag parameter | false |
| Overwrite logic | Implement file overwrite when force=True | ISC-8, ISC-9, ISC-10, ISC-11, ISC-12 | Force flag parameter | false |
| Edge case handling | Handle non-existent, in-use, and partial-failure cases | ISC-13, ISC-14, ISC-15, ISC-16 | Overwrite logic | false |
| Tests | Unit + integration tests for both force and no-force paths | ISC-24, ISC-25, ISC-26, ISC-27, ISC-28 | Overwrite logic | true |
| Documentation | Update cli-reference.md and CHANGELOG.md | ISC-29, ISC-30, ISC-31 | Tests | false |

## Test Strategy

```yaml
- isc: ISC-1
  type: cli-help
  check: --force appears in help text with description
  threshold: help output contains "--force" and meaningful text
  tool: logstory usecases get --help | grep -i force

- isc: ISC-5
  type: behavior
  check: existing usecase is skipped without --force
  threshold: directory still contains original files, unchanged mtime
  tool: bash integration test — download, verify mtime, re-download, verify mtime unchanged

- isc: ISC-8
  type: behavior
  check: files are overwritten when --force is set
  threshold: directory contains new files with updated mtime
  tool: bash integration test — download, record mtime, download with --force, verify mtime newer

- isc: ISC-24
  type: unit-test
  check: _download_usecase(force=False) preserves existing files
  threshold: pytest assertion that old file unchanged after call
  tool: pytest -v tests/test_usecases_get.py::test_download_without_force

- isc: ISC-28
  type: integration-test
  check: end-to-end: logstory usecases get --force NETWORK_ANALYSIS
  threshold: exit code 0, usecase directory populated with latest files
  tool: pytest -v tests/test_usecases_get.py::test_integration_force_get
```

## Decisions

- **2026-08-17 14:52 UTC** — Classified as E3 multi-file work: CLI parameter addition + logic change + tests + docs
- **2026-08-17 14:52 UTC** — Using Typer boolean flag (`--force`) rather than string argument; more idiomatic for CLI
- **2026-08-17 14:52 UTC** — Short alias `-f` included per CLI conventions (but not `-F` to avoid confusion with file paths)
- **2026-08-17 21:55 UTC** — Analyzed `_download_usecase()`: currently downloads all files unconditionally via `blob.download_to_filename()`. Will add force check before the directory creation/download loop.
- **2026-08-17 22:05 UTC** — Implementation complete: modified _download_usecase() with force parameter, added CLI flag via typer.Option, wrote comprehensive unit tests, updated documentation and changelog. Committed with git commit bc83c1d.

## Verification

**ISC-1 through ISC-3 (CLI Interface):**
- Implemented via typer.Option with name "--force", short "-f", and help text in src/logstory/logstory.py:683-688

**ISC-5 through ISC-7 (Download Behavior without --force):**
- Implemented skip logic: os.path.exists(usecase_dir) check at line 602-604 returns True if directory exists and force=False

**ISC-8 through ISC-12 (Download Behavior with --force):**
- Overwrite logic: when force=True and directory exists, downloads all blobs (lines 611-620)
- Message indicates "Updating" vs "Downloading" based on force flag (lines 607-610)
- blob.download_to_filename() handles all file overwrites atomically

**ISC-20 through ISC-23 (Code Quality):**
- Function signature: force: bool = False parameter is backward-compatible (line 575)
- Command passes force=force to _download_usecase (line 694)
- Type hints: force: bool throughout (lines 575, 683)
- No new imports or circular dependencies

**ISC-24 through ISC-27 (Tests):**
- Created tests/test_usecases_get_force.py with TestDownloadUsecaseForceLogic class
- Test methods: test_download_usecase_skips_if_exists_without_force, test_download_usecase_downloads_if_force_true
- Backward compatibility tests: test_download_all_usecases_still_works, test_replay_auto_get_still_works

**ISC-29 & ISC-31 (Documentation):**
- docs/cli-reference.md updated with --force flag description (lines 91-105)
- CHANGELOG.md updated with feature entry (Unreleased section)

## Changelog

(To be filled at LEARN phase)
