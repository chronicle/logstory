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

That would then be published to PyPI with:
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

To edit the docs, use `cd docs/ && make livehtml` and then view the docs at localhost:9000


NOTE: if you are working on a CloudTop, you can port forward 8000 with:
```
ssh -L 8000:localhost:8000 ${cloudtop_hosthame}.c.googlers.com
```


The docs are temporarily hosted in a GCP bucket for dev and review. To publish to that bucket:
```
cd docs/_build/
gsutil rsync -r \
. \
gs://logstory-usecases-20241216/docs/
```

You may then view the docs at:
https://storage.googleapis.com/logstory-usecases-20241216/docs/index.html


## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## License

Apache 2.0; see [`LICENSE`](LICENSE) for details.

## Disclaimer

This project is not an official Google project. It is not supported by
Google and Google specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.
