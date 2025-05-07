# LogStory Internal Docs

The public-facing documentation is in `docs/`. This document is for internal notes.

NOTE: if we decide to move the repo from internal GitLab to public GitHub, this will need to change.

#
# Build PyPI Package
#

The packaging machinery is in `src/logstory/` and the resulting source and wheel packages are in `dist/`

To build a new soure tarball and Python wheel, from git top-level run:
```
make build
```

The wheel to be published is in: dist/logstory-0.1.0-py3-none-any.whl

That would normally be published to PyPI with:
```
twine upload dist/*
```

Until we have approval for that publication, we are using [GCP Artifact Registry](https://cloud.google.com/artifact-registry/)

To configure it:
```
gcloud artifacts print-settings python \
    --project=secops-demo-env \
    --repository=logstory-20241218 \
    --location=us-central1
```

To upload the source and wheel to that registry run this in Cloud Shell:
```
ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
twine upload --repository-url https://us-central1-python.pkg.dev/secops-demo-env/logstory-20241218/ -u oauth2accesstoken -p $ACCESS_TOKEN dist/*
Uploading distributions to https://us-central1-python.pkg.dev/secops-demo-env/logstory-20241218/
Uploading logstory-0.1.0-py3-none-any.whl
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.4/1.4 MB • 00:00 • 4.1 MB/s
Uploading logstory-0.1.0.tar.gz
100% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.3/1.3 MB • 00:00 • 209.7 MB/s
```

## List contents of the Artifact Registry

```
(twine) admin_@cloudshell:~ (secops-demo-env)$ gcloud artifacts files list \
    --project="secops-demo-env" \
    --location="us-central1" \
    --repository="logstory-20241218"
FILE: logstory/logstory-0.1.0-py3-none-any.whl
CREATE_TIME: 2024-12-18T14:10:16
UPDATE_TIME: 2024-12-18T14:10:16
SIZE (MB): 1.296
OWNER: projects/secops-demo-env/locations/us-central1/repositories/logstory-20241218/packages/logstory/versions/0.1.0
ANNOTATIONS:

FILE: logstory/logstory-0.1.0.tar.gz
CREATE_TIME: 2024-12-18T14:10:16
UPDATE_TIME: 2024-12-18T14:10:16
SIZE (MB): 1.249
OWNER: projects/secops-demo-env/locations/us-central1/repositories/logstory-20241218/packages/logstory/versions/0.1.0
ANNOTATIONS:
```

## Download Wheel from the Artifact Registry
```
gcloud artifacts files download \
    --project="secops-demo-env" \
    --location="us-central1" \
    --repository="logstory-20241218" \
    --destination=logstory_dist \
    logstory/logstory-0.1.0-py3-none-any.whl
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
