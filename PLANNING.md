# PLANNING.md - Next Steps for Typer Migration PR

This document outlines the remaining tasks and next steps for completing the Typer CLI migration Pull Request (#28).

## Current Status

**Branch**: `typer`
**PR**: #28 - feat: migrate CLI from Abseil to Typer with environment file support
**Status**: DRAFT

### Completed Items ✅

- [x] Complete migration from Abseil to Typer CLI framework
- [x] Restructured command organization with logical groups (`usecases` and `replay`)
- [x] Added comprehensive environment file support with `--env-file` option
- [x] Enhanced user experience with progressive disclosure and VS Code integration
- [x] Updated documentation (README.md, docs/index.md)
- [x] Added comprehensive .env file documentation (`docs/env-file.md`)
- [x] Created .env.example template file
- [x] Updated PR description with all changes

## Remaining Tasks

### High Priority - Required for Merge

#### 1. Code Quality & Pre-commit Issues
- [ ] **Fix security warnings in logstory.py** (src/logstory/logstory.py:245-257)
  - Address subprocess security warnings (B603, B607)
  - Fix exception handling patterns (B904)
  - Add proper error handling with `raise ... from err`
- [ ] **Address bandit security findings**
  - Resolve hardcoded temp directory usage (B108)
  - Review subprocess module usage patterns
- [ ] **Ensure all pre-commit hooks pass**
  - Run `make pre-commit-run` and fix any remaining issues
  - Verify pyink formatting is consistent

#### 2. Testing & Validation
- [ ] **Comprehensive functionality testing**
  - Test all migrated commands work correctly
  - Verify environment file loading in various scenarios
  - Test priority order: CLI options > env vars > .env file
  - Validate VS Code integration (`--open` flag)
- [ ] **Edge case testing**
  - Test with missing .env files
  - Test with invalid environment file formats
  - Test with missing credentials or invalid UUIDs
  - Test mixed environment sources (local + GCS)

#### 3. Documentation Review
- [ ] **Verify migration guide accuracy**
  - Test all example commands in migration guide
  - Ensure old command mappings are correct
  - Add any missing command mappings
- [ ] **Update CHANGELOG.md**
  - Document breaking changes clearly
  - Add migration instructions
  - Note new features and improvements

### Medium Priority - Nice to Have

#### 4. User Experience Improvements
- [ ] **Add command aliases for backward compatibility** (optional)
  - Consider adding deprecated aliases for common old commands
  - Show deprecation warnings for old usage patterns
- [ ] **Enhanced error messages**
  - Improve error messages for common misconfigurations
  - Add helpful hints for environment file issues
- [ ] **Auto-completion support**
  - Test bash/zsh completion generation
  - Document how to enable shell completion

#### 5. Extended Documentation
- [ ] **Add troubleshooting section to docs/env-file.md**
  - Common error scenarios and solutions
  - Debug commands and techniques
- [ ] **Create video or GIF demos** (optional)
  - Show new CLI workflow in action
  - Demonstrate environment file usage

### Low Priority - Future Enhancements

#### 6. Advanced Features
- [ ] **Configuration validation command**
  - Add `logstory config validate` command
  - Check .env file syntax and credential access
- [ ] **Interactive configuration setup**
  - Add `logstory config init` for guided setup
  - Generate .env files interactively

## Testing Strategy

### Manual Testing Checklist
```bash
# Basic functionality
logstory usecases list-installed
logstory usecases list-installed --details
logstory usecases list-installed --logtypes
logstory usecases list-available

# Environment file testing
logstory usecases list-available --env-file .env.example
logstory replay usecase TEST_CASE --env-file .env.example --local-file-output

# VS Code integration
logstory usecases list-installed --open SOME_USECASE

# Error handling
logstory replay usecase NONEXISTENT
logstory usecases list-available --env-file nonexistent.env
```

### Automated Testing
- [ ] Add unit tests for environment file loading logic
- [ ] Add integration tests for CLI command structure
- [ ] Test help text generation and formatting

## Pre-Merge Checklist

Before marking the PR as ready for review:

- [ ] All high-priority tasks completed
- [ ] Pre-commit hooks pass without `--no-verify`
- [ ] Manual testing checklist completed
- [ ] Documentation reviewed and accurate
- [ ] Version bump in pyproject.toml is appropriate (0.1.4 → 0.2.0)
- [ ] CHANGELOG.md updated with breaking changes
- [ ] All team members who need to be aware have been notified

## Post-Merge Tasks

After the PR is merged:

- [ ] Update any internal documentation that references old CLI commands
- [ ] Notify users of breaking changes and migration path
- [ ] Monitor for issues and user feedback
- [ ] Consider creating follow-up issues for medium/low priority items

## Notes

- **Breaking Changes**: This PR introduces breaking changes to the CLI interface
- **Version**: Bump to 0.2.0 reflects the breaking nature of changes
- **Backward Compatibility**: No backward compatibility for CLI commands (by design)
- **Migration Path**: Clear migration guide provided in PR description and README

## Contact

For questions about this planning document or the migration:
- Review PR #28 comments and discussions
- Check commit history on `typer` branch for recent changes
- Reference the comprehensive .env documentation in `docs/env-file.md`

---

*Last updated: 2025-07-28*
*PR Status: DRAFT - In Progress*
