# LogStory Internal Docs

The public-facing documentation is in `docs/`. This document is for notes on contributing, deveoping, building, distribution, etc.

#
# Build PyPI Package
#

The packaging machinery is in `src/logstory/` and the resulting source and wheel packages are in `dist/`

To build a new soure tarball and Python wheel, from git top-level run:
```
make build
```

The wheel to be published is in: dist/logstory-0.1.0-py3-none-any.whl

That would then be published to Test PyPI with:

```
twine upload --repository testpypi dist/*
```

Test that with:
```
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ logstory
```

When tested, that would then be published to PyPI with:
```
twine upload dist/*
```

#
# Publish a Usecase
#

To add a new usecase to the public Storage Bucket:
```
gsutil rsync -r \
/usr/local/google/home/dandye/Projects/pkg101/logstory/usecases/RULES_SEARCH_WORKSHOP \
gs://logstory-usecases-20241216/RULES_SEARCH_WORKSHOP
```

#
# Edit and Publish Docs
#

To edit the docs, use `cd docs/ && make livehtml` and then view the docs at localhost:8000

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## License

Apache 2.0; see [`LICENSE`](LICENSE) for details.

## Disclaimer

This project is not an official Google project. It is not supported by
Google and Google specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
