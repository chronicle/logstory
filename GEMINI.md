# Agent Guidelines & Memory

## Style & Presentation Rules
- **No Emojis**: NEVER use emojis anywhere (code, CLI output, help messages, documentation, commit messages, or responses). Keep all formatting clean, professional, and text-only with standard ASCII characters.
- **No Meta Jargon in Help**: Do NOT mention the phrase "Big-Endian" or other internal preference labels in user-facing CLI help, UI output, or documentation.

## Command & Recipe Naming Conventions
- **Big-Endian / Hierarchical Naming**: Always use big-endian naming where entity/noun precedes action/verb (`noun-verb` or `entity-subentity-action`).
  - Google Cloud: `auth-login`, `auth-adc`, `project-set`, `project-get`, `apis-enable`
  - Secrets: `secret-create`, `secret-describe`, `secret-list`, `secret-iam`
  - Cloud Run: `cloudrun-job-deploy`, `cloudrun-service-deploy`, `cloudrun-schedule-all`, `cloudrun-schedule-custom`, `cloudrun-job-run`, `cloudrun-job-test`, `cloudrun-service-test`, `cloudrun-status`, `cloudrun-logs`, `cloudrun-service-logs`, `cloudrun-delete-all`, `cloudrun-env-check`, `cloudrun-help`
  - Permissions: `permissions-setup`
  - Usecases: `usecase-publish`, `usecase-publish-all`, `usecase-list-gcs`
  - PyPI: `pypi-publish`, `pypi-publish-test`, `pypi-test-install`
  - Docker: `docker-build`, `docker-build-pypi`, `docker-build-local`, `docker-run-local`
  - Documentation: `docs-build`, `docs-live`, `docs-clean`
  - Pre-commit: `pre-commit-install`, `pre-commit-run`, `pre-commit-update`
  - Virtual Environment: `venv-create`, `venv-clean`
  - Maintain backward-compatible aliases for common shorthands.
