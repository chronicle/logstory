# LogStory Internal Docs

The public-facing documentation is in `docs/`. This document is for notes on contributing, deveoping, building, distribution, etc.

#
# Build PyPI Package
#

The packaging machinery is in `src/logstory/` and the resulting source and wheel packages are in `dist/`

To build a new source tarball and Python wheel, from git top-level run:
```bash
just package-build
```

The wheel to be published is in: `dist/logstory-*.whl`

That can then be published to Test PyPI with:

```bash
just pypi-publish-test
```

Test that with:
```bash
just pypi-test-install
```

When tested, that can then be published to PyPI with:
```bash
just pypi-publish
```

#
# Publish a Usecase
#

To add a new usecase to the public Storage Bucket:
```bash
just usecase-publish RULES_SEARCH_WORKSHOP
```

Or publish all usecases:
```bash
just usecase-publish-all
```

#
# Dependency Management
#

`pyproject.toml` is the single source of truth for all dependencies:
- **Runtime**: `[project.dependencies]`
- **Development**: `[project.optional-dependencies] dev`
- **Documentation**: `[project.optional-dependencies] docs`

### Workflows:
- **Lock dependencies**: `just deps-lock` (or `uv lock --upgrade`)
- **Sync local environment**: `uv sync --all-extras`
- **Compile deploy requirements**: `just deps-compile` (or `uv pip compile pyproject.toml -o src/logstory/requirements.txt`)

#
# Edit and Publish Docs
#

To edit and live-preview the docs:
```bash
just docs-live
```
and then view the docs at http://localhost:8000 (or build static docs with `just docs-build`).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## License

Apache 2.0; see [`LICENSE`](LICENSE) for details.

## Disclaimer

This project is not an official Google project. It is not supported by
Google and Google specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
