# LogStory

LogStory is used to update timestamps in telemetry (i.e. logs) and then replay them into a [Google Security Operations (SecOps)](https://cloud.google.com/security/products/security-operations?hl=en) tenant. Each usecase tells an infosec story, a "Log Story".

## Usecases

The stories are organized as "usecases", which always contain events and may contain entities, reference lists, and/or Yara-L 2.0 Detection Rules. Each usecase includes a ReadMe to describe its use.

Only the RULES_SEARCH_WORKSHOP is included with the PyPI package. Learning about and installing addition usecases is described in [usecases](./usecase_docs/ReadMe.md).

```{tip} It is strongly recommended to review each usecase before ingestion rather than importing them all at once.
```

## Documentation

For comprehensive documentation on using Logstory:

- **[CLI Reference](cli-reference.md)** - Complete command reference with all options and examples
- **[Configuration](configuration.md)** - Detailed configuration guide for all environments  
- **[.env File Reference](env-file.md)** - Complete guide to .env file format and all supported variables
- **[Local File System Sources](file-sources.md)** - Using `file://` URIs for Chronicle replay use cases and local development

## Installation

Logstory has a command line interface (CLI), written in Python, that is most easily installed from the Python Package Index (PyPI):

```bash
$ pip install logstory
```

The `logstory` CLI interface uses command groups and subcommands with arguments like so:
```
logstory replay usecase RULES_SEARCH_WORKSHOP
```

These are explained in depth later in this doc.

## Configuration

After the subcommand, Logstory uses [Typer](https://typer.tiangolo.com/) for modern CLI argument and option handling. You can provide configuration in several ways:

**1. Command Line Options:**
```
logstory replay usecase RULES_SEARCH_WORKSHOP \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/usr/local/google/home/dandye/.ssh/malachite-787fa7323a7d_bk_and_ing.json \
  --timestamp-delta=1d
```

**2. Environment Files (.env):**
All commands support the `--env-file` option to load environment variables from a file:
```bash
# For usecases commands
logstory usecases list-available --env-file .env.prod
logstory usecases get MY_USECASE --env-file .env.dev

# For replay commands
logstory replay usecase RULES_SEARCH_WORKSHOP --env-file .env
```

```{tip}
For complete .env file syntax, all supported variables, and example configurations, see the [.env File Reference](env-file.md).
```

### Usecase Sources

Logstory can source usecases from multiple sources using URI-style prefixes. Configure sources using the `LOGSTORY_USECASES_BUCKETS` environment variable:

```bash
# Single bucket (default)
export LOGSTORY_USECASES_BUCKETS=gs://logstory-usecases-20241216

# Multiple sources (comma-separated)  
export LOGSTORY_USECASES_BUCKETS=gs://logstory-usecases-20241216,gs://my-custom-bucket,gs://team-bucket

# Mix GCS and local file system sources
export LOGSTORY_USECASES_BUCKETS=gs://logstory-usecases-20241216,file:///path/to/local/usecases

# Local file system only
export LOGSTORY_USECASES_BUCKETS=file:///path/to/chronicle/usecases

# Backward compatibility (bare bucket names auto-prefixed with gs://)
export LOGSTORY_USECASES_BUCKETS=logstory-usecases-20241216,my-custom-bucket
```

**Supported Source Types:**
- **`gs://bucket-name`**: Google Cloud Storage buckets
- **`file://path`**: Local file system directories
- **Future support planned**: `git@github.com:user/repo.git`, `s3://bucket-name`

**Authentication:**
- **GCS public buckets**: Accessed anonymously (no authentication required)
- **GCS private buckets**: Requires `gcloud application-default login` credentials
- **Local file system**: No authentication required (uses file system permissions)
- The system automatically tries authenticated access first, then falls back to anonymous access

**URI-Style Prefixes:**
- Use `gs://` prefix for explicit GCS bucket specification
- Use `file://` prefix for local file system directories (absolute paths required)
- Bare bucket names automatically treated as GCS buckets (backward compatibility)
- Future Git support: `git@github.com:user/usecases.git` or `https://github.com/user/usecases.git`

**Commands:**
```bash
# List usecases from all configured sources
logstory usecases list-available

# Override source configuration for a single command
logstory usecases list-available --usecases-bucket gs://my-specific-bucket

# Download usecase (searches all configured sources)
logstory usecases get MY_USECASE

# Examples with different source types
logstory usecases list-available --usecases-bucket file:///path/to/local/usecases
logstory usecases get USECASE_NAME --usecases-bucket file:///path/to/local/usecases

# Future Git support (when supported)
logstory usecases list-available --usecases-bucket git@github.com:myorg/usecases.git
```

#### Migration from Pre-URI Configuration

If you're upgrading from a version without URI-style prefixes:

**Before:**
```bash
export LOGSTORY_USECASES_BUCKETS=logstory-usecases-20241216,my-bucket
```

**After (recommended):**
```bash
# GCS buckets with explicit prefixes
export LOGSTORY_USECASES_BUCKETS=gs://logstory-usecases-20241216,gs://my-bucket

# Or mix with local file system
export LOGSTORY_USECASES_BUCKETS=gs://logstory-usecases-20241216,file:///path/to/local/usecases
```

**Note:** The old format still works (backward compatibility), but using explicit URI prefixes (`gs://`, `file://`) is recommended for clarity and future compatibility.

```{tip}
For advanced configuration scenarios, environment files, CI/CD integration, and troubleshooting, see the comprehensive [Configuration Guide](configuration.md).
```

### Customer ID

(Required) This is your Google SecOps tenant's UUID4, which can be found at:

https://${code}.backstory.chronicle.security/settings/profile

### Credentials Path)

(Required)  The credentials provided use the [Google Security Operations Ingestion API](https://cloud.google.com/chronicle/docs/reference/ingestion-api). This is *NOT* the newer RESTful v1alpha Ingestion API (yet, but that is future work).

**Getting API authentication credentials**

"Your Google Security Operations representative will provide you with a Google Developer Service Account Credential to enable the API client to communicate with the API."[[reference](https://cloud.google.com/chronicle/docs/reference/ingestion-api#getting_api_authentication_credentials)]


### Timestamp BTS

(Optional, default=1d) Updating timestamps for security telemetry is tricky. The .log files in the usecases have timestamps in many formats and we need to update them all to be recent while simultaneously preserving the relative differences between them. For each usecase, LogStory determines the base timestamp "bts" for the first timestamp in the first logfile and all updates are relative to it.


The image below shows that original timestamps on 2023-06-23 (top two subplots) were updated to 2023-09-24, the relative differences between the three timestamps on the first line of the first log file before (top left) and the last line of the logfile (top right) are preserved both interline and intraline on the bottom two subplots. The usecase spans an interval of 5 minutes and 55 seconds both before and after updates.

![Visualize timestamp updates](https://raw.githubusercontent.com/chronicle/logstory/refs/heads/main/docs/img/bts_update.jpg)

### Timestamp Delta

When timestamp_delta is set to 0d (zero days), only year, month, and day are updated (to today) and the hours, minutes, seconds, and milliseconds are preserved. That hour may be in the future, so when timestamp_delta is set to 1d the year, month, and day are set to today minus 1 day and the hours, minutes, seconds, and milliseconds are preserved.

```{tip}
For best results, use a cron jobs to run the usecase daily at 12:01am with `--timestamp-delta=1d`.
```

You may also provide `Nh` for offsetting by the hour, which is mainly useful if you want to replay the same log file multiple times per day (and prevent deduplication). Likewise, `Nm` offsets by minutes. These can be combined. For example, on the day of writing (Dec 13, 2024)`--timestamp-delta=1d1h1m` changes an original timestamp from/to:
```
2021-12-01T13:37:42.123Z1
2024-12-12T12:36:42.123Z1
```

The hour and minute were each offset by -1 and the date is the date of execution -1.

## Timestamp Configuration

LogStory uses YAML configuration files to define how timestamps are parsed and processed for each log type:

- `logtypes_entities_timestamps.yaml` - Configuration for entity timestamps
- `logtypes_events_timestamps.yaml` - Configuration for event timestamps

### Timestamp Entry Structure

Each log type defines timestamps with the following fields:

**Required fields:**
- `name`: String identifier for the timestamp field
- `pattern`: Regular expression to match the timestamp
- `epoch`: Boolean indicating timestamp format (`true` for Unix epoch, `false` for formatted dates)
- `group`: Integer specifying which regex group contains the timestamp

**Optional fields:**
- `base_time`: Boolean marking the primary timestamp (exactly one per log type)
- `dateformat`: Format string for non-epoch timestamps (required when `epoch: false`)

### Epoch vs Formatted Timestamps

LogStory supports two timestamp formats:

**Unix Epoch Timestamps** (`epoch: true`):
```yaml
- name: event_time
  base_time: true
  epoch: true
  group: 2
  pattern: '(\s*?)(\d{10})(.\d+\s*)'
```

**Formatted Timestamps** (`epoch: false`):
```yaml
- name: gcp_timestamp
  base_time: true
  epoch: false
  dateformat: '%Y-%m-%dT%H:%M:%S'
  group: 2
  pattern: '("timestamp":\s*"?)(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'
```

### Configuration Validation

LogStory automatically validates timestamp configurations at runtime to ensure:

- Each log type has exactly one `base_time: true` timestamp
- All required fields are present with correct data types
- Epoch and dateformat fields are logically consistent:
  - `epoch: true` timestamps should not have `dateformat` fields
  - `epoch: false` timestamps must have `dateformat` fields
- All timestamps follow consistent naming and structure patterns

If configuration validation fails, LogStory will provide clear error messages indicating the specific log type, timestamp, and issue found.

## Command Structure

Logstory uses a modern CLI structure with command groups. You can replay specific logtypes like this:

```
logstory replay logtype RULES_SEARCH_WORKSHOP POWERSHELL \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json
```

That updates timestamps and uploads from a single logfile in a single usecase. The following updates timestamps and uploads only entities (rather than events):

```
logstory replay logtype RULES_SEARCH_WORKSHOP POWERSHELL \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json \
  --timestamp-delta=0d \
  --entities
```

You can increase verbosity by prepending the python log level:
```
PYTHONLOGLEVEL=DEBUG logstory replay usecase RULES_SEARCH_WORKSHOP \
  --customer-id=01234567-0123-4321-abcd-01234567890a \
  --credentials-path=/path/to/credentials.json \
  --timestamp-delta=0d
```

For more usage, see `logstory --help`


## Usecases

Usecases are meant to be self-describing, so check out the metadata in each one.

```{tip} It is strongly recommended to review each usecase before ingestion rather than importing them all at once.
```

As shown in the [ReadMe for the Rules Search Workshop](https://storage.googleapis.com/logstory-usecases-20241216/RULES_SEARCH_WORKSHOP/RULES_SEARCH_WORKSHOP.md),


If your usecases were distributed via PyPI (rather than git clone), they will be installed in `<venv>/site-packages/logstory/usecases`

You can find the absolute path to that usecase dir with:
```
python -c 'import os; import logstory; print(os.path.split(logstory.__file__)[0])'
/usr/local/google/home/dandye/miniconda3/envs/venv/lib/python3.13/site-packages/logstory
```

### Adding more usecases

We've chosen to distribute only a small subset of the available usecases. Should you choose to add more, you should read the metadata and understand the purpose of each one before adding them.


For the PyPI installed package, simply curl the new usecase into the `<venv>/site-packages/logstory/usecases` directory.

For example, first review the ReadMe for the EDR Workshop usecase:
https://storage.googleapis.com/logstory-usecases-20241216/EDR_WORKSHOP/EDR_WORKSHOP.md

Then download the usecase into that dir. For example:

```
gsutil rsync -r \
gs://logstory-usecases-20241216/EDR_WORKSHOP \
~/miniconda3/envs/pkg101_20241212_0453/lib/python3.13/site-packages/logstory/usecases/
```

To make that easier:
```
❯ logstory usecases list-available

Available usecases in source 'gs://logstory-usecases-20241216':
- EDR_WORKSHOP
- RULES_SEARCH_WORKSHOP
```

For multiple sources:
```
❯ export LOGSTORY_USECASES_BUCKETS=gs://logstory-usecases-20241216,gs://my-private-bucket  
❯ logstory usecases list-available

Available usecases in source 'gs://logstory-usecases-20241216':
- EDR_WORKSHOP
- RULES_SEARCH_WORKSHOP

Available usecases in source 'gs://my-private-bucket':
- CUSTOM_USECASE
- TEAM_ANALYSIS

All available usecases: CUSTOM_USECASE, EDR_WORKSHOP, RULES_SEARCH_WORKSHOP, TEAM_ANALYSIS
```

```
❯ logstory usecases get EDR_WORKSHOP
Downloading usecase 'EDR_WORKSHOP' from source 'gs://logstory-usecases-20241216'
Downloading EDR_WORKSHOP/EDR_WORKSHOP.md to [redacted]/logstory/usecases/EDR_WORKSHOP/EDR_WORKSHOP.md
Downloading EDR_WORKSHOP/EVENTS/CS_DETECTS.log to [redacted]/logstory/src/logstory/usecases/EDR_WORKSHOP/EVENTS/CS_DETECTS.log
Downloading EDR_WORKSHOP/EVENTS/CS_EDR.log to [redacted]/logstory/src/logstory/usecases/EDR_WORKSHOP/EVENTS/CS_EDR.log
Downloading EDR_WORKSHOP/EVENTS/WINDOWS_SYSMON.log to [redacted]/logstory/src/logstory/usecases/EDR_WORKSHOP/EVENTS/WINDOWS_SYSMON.log
```

```
❯ logstory usecases list-installed
#
# EDR_WORKSHOP
#
...
```

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

For detailed development and release documentation, see [Development Documentation](./development/).

## License

`logstory` was created by Google Cloud Security. It is licensed under the terms of the Apache License 2.0 license.



## Development and re-building for publication on PyPI

```
git clone git@gitlab.com:google-cloud-ce/googlers/dandye/logstory.git
# Edit, edit, edit...
make build
# ToDo: pub to PyPI command
```

### Testing

LogStory includes comprehensive validation tests for timestamp configurations:

```bash
# Run YAML validation tests
cd tests/
python test_yaml.py
```

The test suite validates all timestamp configurations in both entities and events files, ensuring:
- Proper field structure and data types
- Logical consistency between epoch and dateformat fields  
- Required field presence
- Base time configuration correctness

All 55 log types across both configuration files are automatically tested for compliance with LogStory's timestamp standards.


# GCP Cloud Run functions

The `cloudfunctions/` subdirectory contains Terraform configuration for deploying
the project to GCP Cloud Run functions. This includes:
 * Functions for loading Entities and Events on 3 day and 24 hour schedules
 * Scheduler for the above
 * GCP Cloud Storage bucket for the usecases
 * ...

## Prerequisites

```{warning}
Do not use GCP CloudShell to run Terraform, use your local machine, a Cloudtop instance (for Googlers), or a Linux VM in GCP.*
```

### Chronicle (Malachite) Google Cloud project configuration

The ingestion API used by LogStory is the [Google Security Operations Ingestion API](https://cloud.google.com/chronicle/docs/reference/ingestion-api).

```{seealso}
Reference documentation for the [Google Security Operations Ingestion API](https://cloud.google.com/chronicle/docs/reference/ingestion-api)
```

```{note}
Your Google Security Operations representative will provide you with a Google Developer Service Account Credential to enable the API client to communicate with the API.
```

- A Service Account is required in the `malachite-gglxxxx` Google Cloud project for your Chronicle tenant. Create a new Service Account if needed.
  - The Service Account needs the `Malachite Ingestion Collector` role assigned to it in order to forward events to Chronicle.
  - If you want to use Logstory's sample rules with Chronicle, the service account also needs the `Backstory Rules Engine API User` role.

### Google Cloud project configuration

Authenticate to the [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects) that is bound to your Chronicle tenant.

~~~bash
gcloud auth login
PROJECT_ID=your_project_id_here
gcloud config set project $PROJECT_ID
~~~

Create a Service Account for use with Terraform and grant it the appropriate permissions.

~~~bash
gcloud iam service-accounts create terraform --display-name="terraform" --description="terraform"
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:terraform@$PROJECT_ID.iam.gserviceaccount.com --role  roles/cloudfunctions.admin
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:terraform@$PROJECT_ID.iam.gserviceaccount.com --role  roles/cloudscheduler.admin
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:terraform@$PROJECT_ID.iam.gserviceaccount.com --role  roles/iam.securityAdmin
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:terraform@$PROJECT_ID.iam.gserviceaccount.com --role  roles/iam.serviceAccountCreator
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:terraform@$PROJECT_ID.iam.gserviceaccount.com --role  roles/iam.serviceAccountDeleter
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:terraform@$PROJECT_ID.iam.gserviceaccount.com --role  roles/iam.serviceAccountUser
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:terraform@$PROJECT_ID.iam.gserviceaccount.com --role  roles/secretmanager.admin
gcloud projects add-iam-policy-binding $PROJECT_ID --member serviceAccount:terraform@$PROJECT_ID.iam.gserviceaccount.com --role  roles/storage.admin
~~~

Enable the Google APIs in your project that are required to run Logstory.

~~~bash
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
~~~

In the Google Cloud console, create a key for the newly created `terraform` Service Account. You will update the Terraform configuration files to use this key in an upcoming step.

A working [Terraform installation](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/install-cli) is required.

## Configuration

- [Clone this repository](https://docs.gitlab.com/ee/gitlab-basics/start-using-git.html#clone-a-repository).
- If you have your own use cases to replay, add them to the [usecases](./usecases/) folder. By default, Logstory will replay all of the use cases in [usecases](./usecases/).
    - Open the [cloudfunction-code](./cloudfunction-code/) folder and review the `usecases_events_logtype_map.yaml` and `usecases_entities_logtype_map.yaml` files under each folder. If you want to disable a use case, just flip the `enabled` flag to **0**.
    - If you have new use cases, add them to corresponding *.yaml* files under each folder depending on the replay frequency.
- [Create a GCS Bucket](https://console.cloud.google.com/storage/) to save the Terraform state such as `TLA-chronicle-logstory-replay-tfstate`.
- Open [`backend.tf`](./backend.tf) with your favorite text editor and change both `credentials` and `bucket` values to yours.
    - `credentials` should be set to the path to your Terraform Service Account key file.
    - The bucket must have been created previously as it is where you will be storing your Terraform's state files.
- Open `variables.tf` with your favorite text editor and change the default values to yours including the Chronicle Ingestion API key.
    - Note, the **numeric** Google Cloud project number is required for the `gcp_project_number` variable. You can execute the following `gcloud` command to find it.

    ```bash
    gcloud projects list
    me:~/chronicle-logstory$ gcloud projects list
    PROJECT_ID        NAME       PROJECT_NUMBER
    chronicle-123456  chronicle  101010101010
    ```

## Deployment

- Run `sh bash.sh` to generate the latest version of Cloud Function codes
- Run the following Terraform commands to initialize, plan, and apply the configuration.

~~~bash
# Verify that the Terraform state file has been uploaded to the GCS bucket after running 'terraform init'.
terraform init
terraform plan
terraform apply
~~~

Navigate to the Cloud Functions and Cloud Scheduler pages in the Google Cloud console and verify that the Logstory artifacts were created.

## Cloud Schedulers

Logstory deploys a number of different Cloud Schedulers. Some data is ingested every 24hours and others every 3 days. If you want to ingest data immediately, you can force a run of the Cloud Scheduler job manually. However, we suggest you to run the logs in a specific order, first run the entities and after couple of hours, run the events.

There are some sample rules in this repo that can be deployed into your Chronicle as well. See [rules](./rules/) folder. If you want to deploy the sample rules, just force run the job named `TLA-chronicle-rule-creator-XXX` from Cloud Schedulers.

## Destruction

- Run `terraform destroy`
- Delete the GCS Bucket created to store the Terraform state.
- Delete the rules created in your Chronicle SIEM using [Delete Rule API](https://cloud.google.com/chronicle/docs/reference/detection-engine-api#deleterule)

## Authors and acknowledgment
security-adoption-eng@google.com



## Contents

```{toctree}
---
maxdepth: 2
---
usecase_docs/ReadMe
usecase_docs/index
development/releases
```
