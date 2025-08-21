# Copyright 2025 Google LLC
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
"""CLI for Logstory."""

import datetime
import glob
import os
import shutil
import uuid
from importlib.metadata import version

import typer
from dotenv import load_dotenv
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage
from google.oauth2 import service_account

from logstory.auth import has_application_default_credentials

UTC = datetime.UTC

DEFAULT_BUCKET = "gs://logstory-usecases-20241216"


def version_callback(value: bool):
  """Callback to display version and exit."""
  if value:
    try:
      __version__ = version("logstory")
    except Exception:
      __version__ = "unknown"
    typer.echo(f"logstory {__version__}")
    raise typer.Exit()


# Create Typer app and command groups
app = typer.Typer(help="Logstory: Replay SecOps logs with updated timestamps")
usecases_app = typer.Typer(help="Manage and list usecases")
replay_app = typer.Typer(help="Replay log data")

app.add_typer(usecases_app, name="usecases")
app.add_typer(replay_app, name="replay")


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
  """Logstory: Replay SecOps logs with updated timestamps."""


def validate_uuid4(value: str) -> str:
  """Typer callback validation for customer ID."""
  try:
    val = uuid.UUID(value, version=4)
    if str(val) == value:
      return value
    raise typer.BadParameter(f"'{value}' is not a valid UUID4")
  except ValueError as e:
    raise typer.BadParameter(f"'{value}' is not a valid UUID4") from e


def validate_credentials_file(value: str) -> str:
  """Typer callback validation for credentials file."""
  if not os.path.isfile(value):
    raise typer.BadParameter(
        f"File does not exist: {value}. "
        "Please provide the complete path to a JSON credentials file."
    )
  try:
    _ = service_account.Credentials.from_service_account_file(value)
    return value
  except Exception as e:
    raise typer.BadParameter(f"The JSON file is invalid: {e}") from e


def load_env_file(env_file: str | None = None) -> None:
  """Load environment variables from .env file."""
  if env_file:
    if not os.path.isfile(env_file):
      typer.echo(f"Warning: Specified .env file not found: {env_file}")
      return
    load_dotenv(env_file)
    typer.echo(f"Loaded environment from: {env_file}")
  # Try to load default .env file if it exists
  elif os.path.isfile(".env"):
    load_dotenv(".env")
    typer.echo("Loaded environment from: .env")


# Global options for replay commands
def get_credentials_default():
  """Get credentials path or JSON from environment variables."""
  # Check for direct credentials JSON first
  credentials_json = os.getenv("LOGSTORY_CREDENTIALS")
  if credentials_json:
    # Write to temp file and return path
    import json
    import tempfile

    try:
      # Validate it's valid JSON
      json.loads(credentials_json)
      # Create temp file
      with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(credentials_json)
        return f.name
    except json.JSONDecodeError:
      typer.echo("Warning: LOGSTORY_CREDENTIALS contains invalid JSON")

  # Fall back to credentials path
  return os.getenv("LOGSTORY_CREDENTIALS_PATH")


def get_customer_id_default():
  """Get customer ID from environment variable."""
  return os.getenv("LOGSTORY_CUSTOMER_ID")


def get_region_default():
  """Get region from environment variable."""
  return os.getenv("LOGSTORY_REGION", "US")


def get_timestamp_delta_default():
  """Get timestamp delta from environment variable."""
  return os.getenv("LOGSTORY_TIMESTAMP_DELTA", "1d")


def get_auto_get_default():
  """Get auto-get setting from environment variable."""
  auto_get_value = os.getenv("LOGSTORY_AUTO_GET", "").lower()
  return auto_get_value in ("true", "1", "yes", "on")


def parse_usecase_source(source_uri: str) -> tuple[str, str]:
  """Parse a usecase source URI and return (source_type, identifier).

  Args:
    source_uri: URI like 'gs://bucket-name' or bare bucket name

  Returns:
    Tuple of (source_type, identifier) where:
    - source_type: 'gcs', 'git', etc.
    - identifier: bucket name, repo URL, etc.
  """
  source_uri = source_uri.strip()

  if source_uri.startswith("gs://"):
    return ("gcs", source_uri[5:])  # Remove 'gs://' prefix
  if source_uri.startswith("git@") or source_uri.endswith(".git"):
    return ("git", source_uri)
  if source_uri.startswith("s3://"):
    return ("s3", source_uri[5:])
  if source_uri.startswith("file://"):
    return ("file", source_uri[7:])
  # Backward compatibility: treat bare names as GCS bucket names
  return ("gcs", source_uri)


def get_usecases_buckets():
  """Get list of usecases buckets from environment variable."""
  buckets_str = os.getenv("LOGSTORY_USECASES_BUCKETS", DEFAULT_BUCKET)
  return [bucket.strip() for bucket in buckets_str.split(",") if bucket.strip()]


CredentialsOption = typer.Option(
    None,
    "--credentials-path",
    "-c",
    help=(
        "Path to JSON credentials for Ingestion API Service account (env:"
        " LOGSTORY_CREDENTIALS_PATH)"
    ),
    callback=lambda v: validate_credentials_file(v) if v else None,
)

CustomerIdOption = typer.Option(
    None,
    "--customer-id",
    help=(
        "Customer ID for SecOps instance, found on `/settings/profile/` (env:"
        " LOGSTORY_CUSTOMER_ID)"
    ),
    callback=lambda v: validate_uuid4(v) if v else None,
)

EnvFileOption = typer.Option(
    None,
    "--env-file",
    help="Path to .env file to load environment variables from",
)

RegionOption = typer.Option(
    None,
    "--region",
    "-r",
    help=(
        "SecOps tenant's region (Default=US). Used to set ingestion API base URL (env:"
        " LOGSTORY_REGION)"
    ),
)

EntitiesOption = typer.Option(
    False,
    "--entities",
    help="Load Entities instead of Events",
)

ThreeDayOption = typer.Option(
    False,
    "--three-day",
    help="Use 3-day configuration",
)

TimestampDeltaOption = typer.Option(
    get_timestamp_delta_default,
    "--timestamp-delta",
    help=(
        "Determines how datetimes in logfiles are updated. "
        "Expressed in any/all: days, hours, minutes (d, h, m) (Default=1d). "
        "Examples: [1d, 1d1h, 1h1m, 1d1m, 1d1h1m, 1m1h, ...]. "
        "Setting only `Nd` preserves the original HH:MM:SS but updates date. "
        "Nh/Nm subtracts an additional offset from that datetime, to facilitate "
        "running logstory more than 1x per day. "
        "(env: LOGSTORY_TIMESTAMP_DELTA)"
    ),
)

UsecasesBucketOption = typer.Option(
    None,
    "--usecases-bucket",
    help="Usecase source URI (gs://bucket, git@repo, etc.) - overrides config list",
)

LocalFileOutputOption = typer.Option(
    False,
    "--local-file-output",
    help="Write logs to local files instead of sending to API",
)

ApiTypeOption = typer.Option(
    None,
    "--api-type",
    help=(
        "Ingestion API type: 'legacy' or 'rest' (auto-detect if not specified). "
        "(env: LOGSTORY_API_TYPE)"
    ),
)

ProjectIdOption = typer.Option(
    None,
    "--project-id",
    help="Google Cloud project ID (required for REST API). (env: LOGSTORY_PROJECT_ID)",
)

ForwarderNameOption = typer.Option(
    None,
    "--forwarder-name",
    help=(
        "Custom forwarder name for REST API (default: Logstory-REST-Forwarder). "
        "(env: LOGSTORY_FORWARDER_NAME)"
    ),
)

ImpersonateServiceAccountOption = typer.Option(
    None,
    "--impersonate-service-account",
    help=(
        "Service account email to impersonate (REST API only). "
        "(env: LOGSTORY_IMPERSONATE_SERVICE_ACCOUNT)"
    ),
)


def _get_current_time():
  """Returns the current time in UTC."""
  return datetime.datetime.now(UTC)


@usecases_app.command("list-installed")
def usecases_list(
    env_file: str | None = EnvFileOption,
    logtypes: bool = typer.Option(
        False, "--logtypes", help="Show logtypes for each usecase"
    ),
    details: bool = typer.Option(
        False, "--details", help="Show full markdown content for each usecase"
    ),
    open_usecase: str = typer.Option(
        None, "--open", help="Open markdown file for specified usecase in VS Code"
    ),
    entities: bool = EntitiesOption,
):
  """List locally installed usecases and optionally their logtypes."""
  # Load environment file
  load_env_file(env_file)

  # Handle --open flag as a special case
  if open_usecase:
    import subprocess  # nosec B404

    usecase_dirs = glob.glob(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "usecases/*")
    )

    # Find the specified usecase
    usecase_found = False
    for usecase_dir in usecase_dirs:
      parts = os.path.split(usecase_dir)
      if parts[-1] == open_usecase:
        usecase_found = True
        # Look for markdown files in this usecase
        md_files = glob.glob(os.path.join(usecase_dir, "*.md"))
        if md_files:
          for md_file in md_files:
            typer.echo(f"Opening {md_file} in VS Code...")
            try:
              subprocess.run(["code", md_file], check=True)  # nosec B603 B607
            except subprocess.CalledProcessError:
              typer.echo(
                  "Error: Could not run 'code' command. Make sure VS Code is installed"
                  " and in PATH."
              )
              raise typer.Exit(1)
            except FileNotFoundError:
              typer.echo(
                  "Error: 'code' command not found. Make sure VS Code is installed and"
                  " in PATH."
              )
              raise typer.Exit(1)
        else:
          typer.echo(f"No markdown files found in usecase '{open_usecase}'")
          raise typer.Exit(1)
        break

    if not usecase_found:
      available_usecases = [
          os.path.split(d)[-1]
          for d in usecase_dirs
          if os.path.split(d)[-1] not in ["__init__.py", "AWS"]
      ]
      typer.echo(f"Error: Usecase '{open_usecase}' not found.")
      typer.echo(f"Available usecases: {', '.join(sorted(available_usecases))}")
      raise typer.Exit(1)

    return  # Exit early when using --open

  entity_or_event = "ENTITIES" if entities else "EVENTS"
  usecase_dirs = glob.glob(
      os.path.join(os.path.dirname(os.path.abspath(__file__)), "usecases/*")
  )
  usecases = []
  logypes_map: dict[str, list[str]] = {}
  markdown_map: dict[str, list[str]] = {}
  for usecase_dir in usecase_dirs:
    parts = os.path.split(usecase_dir)
    if parts[-1] in ["__init__.py", "AWS"]:
      continue
    usecases.append(parts[-1])
    markdown_map[usecases[-1]] = []
    for md in glob.glob(os.path.join("./", usecase_dir, "*.md")):
      markdown_map[usecases[-1]].append(md)
    log_types = []
    if logtypes:
      for adir in glob.glob(os.path.join("./", usecase_dir, entity_or_event, "*.log")):
        log_types.append(os.path.splitext(os.path.split(adir)[-1])[0])
      logypes_map[usecases[-1]] = log_types
  for usecase in sorted(usecases):
    if details:
      print(f"#\n# {usecase}\n#")
      for md in markdown_map.get(usecase, []):
        with open(md) as fh:
          print(fh.read())
    else:
      print(usecase)

    if logtypes:
      for log_type in sorted(logypes_map[usecase]):
        if details:
          print(f"\t{log_type}")
        else:
          print(f"  {log_type}")


def _get_blobs(source_uri, usecase=None):
  """Get blobs from usecase source, supporting multiple source types."""
  source_type, identifier = parse_usecase_source(source_uri)

  if source_type == "gcs":
    return _get_gcs_blobs(identifier, usecase)
  if source_type == "git":
    raise NotImplementedError("Git source support not yet implemented")
  if source_type == "s3":
    raise NotImplementedError("S3 source support not yet implemented")
  if source_type == "file":
    return _get_file_blobs(identifier, usecase)
  raise ValueError(f"Unsupported source type: {source_type}")


def _get_gcs_blobs(bucket_name, usecase=None):
  """Get blobs from GCS bucket, trying authenticated client first."""
  client = None

  # Try application default credentials first
  try:
    client = storage.Client()
  except DefaultCredentialsError:
    # Fall back to anonymous client for public buckets
    try:
      client = storage.Client.create_anonymous_client()
    except Exception as e:
      raise Exception(f"Could not create GCS client: {e}") from e

  bucket = client.bucket(bucket_name)
  if usecase:
    blobs = bucket.list_blobs(prefix=usecase)
  else:
    blobs = bucket.list_blobs(delimiter="/")
  return blobs


class _FileBlob:
  """Mock blob object for file system operations."""

  def __init__(self, name: str, file_path: str):
    self.name = name
    self._file_path = file_path

  def download_to_filename(self, destination: str):
    """Copy file from source to destination."""
    shutil.copy2(self._file_path, destination)


class _FileBlobPage:
  """Mock blob page for directory listing operations."""

  def __init__(self, prefixes: list[str]):
    self.prefixes = prefixes


class _FileBlobCollection:
  """Mock blob collection that mimics GCS blob list with pages."""

  def __init__(self, pages: list[_FileBlobPage]):
    self.pages = pages


def _get_file_blobs(directory_path, usecase=None):
  """Get blobs from local file system, mimicking GCS blob interface."""
  if not os.path.exists(directory_path):
    raise Exception(f"Directory does not exist: {directory_path}")

  if not os.path.isdir(directory_path):
    raise Exception(f"Path is not a directory: {directory_path}")

  if usecase:
    # Return files for a specific usecase (used for downloading)
    usecase_path = os.path.join(directory_path, usecase)
    if not os.path.exists(usecase_path):
      raise Exception(f"Usecase directory does not exist: {usecase_path}")

    blobs = []
    for root, _dirs, files in os.walk(usecase_path):
      for file in files:
        file_path = os.path.join(root, file)
        # Create relative path from the base directory for the blob name
        relative_path = os.path.relpath(file_path, directory_path)
        # Normalize path separators to forward slashes (like GCS)
        blob_name = relative_path.replace(os.sep, "/")
        blobs.append(_FileBlob(blob_name, file_path))

    return blobs

  # Return top-level directories (used for listing available usecases)
  prefixes = []
  try:
    for item in os.listdir(directory_path):
      item_path = os.path.join(directory_path, item)
      if os.path.isdir(item_path):
        # Add trailing slash to match GCS behavior
        prefixes.append(f"{item}/")
  except PermissionError as e:
    raise Exception(f"Permission denied accessing directory: {directory_path}") from e

  return _FileBlobCollection([_FileBlobPage(prefixes)])


@usecases_app.command("list-available")
def list_bucket_directories(
    env_file: str | None = EnvFileOption,
    bucket: str = UsecasesBucketOption,
):
  """List usecases available for download from configured sources."""
  # Load environment file
  load_env_file(env_file)

  buckets = [bucket] if bucket else get_usecases_buckets()

  all_usecases = set()

  for source_uri in buckets:
    try:
      blobs = _get_blobs(source_uri)
      print(f"\nAvailable usecases in source '{source_uri}':")
      for blob in blobs.pages:
        prefixes = blob.prefixes
        for prefix in prefixes:
          if "docs" in prefix:
            continue
          prefix = prefix.strip("/")
          print(f"- {prefix}")
          all_usecases.add(prefix)
    except Exception as e:
      print(f"Warning: Could not access source '{source_uri}': {e}")
      continue

  if len(buckets) > 1:
    print(f"\nAll available usecases: {', '.join(sorted(all_usecases))}")

  return list(all_usecases)


def _get_source_directories(source_uri: str) -> list[str]:
  """Helper function to get source directories without printing."""
  blobs = _get_blobs(source_uri)
  top_level_directories = []
  for blob in blobs.pages:
    prefixes = blob.prefixes
    for prefix in prefixes:
      if "docs" in prefix:
        continue
      prefix = prefix.strip("/")
      top_level_directories.append(prefix)
  return top_level_directories


def _get_all_source_directories() -> list[str]:
  """Helper function to get directories from all configured sources."""
  sources = get_usecases_buckets()
  all_directories = set()

  for source_uri in sources:
    try:
      directories = _get_source_directories(source_uri)
      all_directories.update(directories)
    except Exception as e:
      # Skip inaccessible sources, but log the error
      typer.echo(f"Debug: Could not access source '{source_uri}': {e}", err=True)
      continue

  return list(all_directories)


def _download_usecase(usecase: str, bucket: str = None) -> bool:
  """Download a usecase from configured sources. Returns True if successful."""
  sources = [bucket] if bucket else get_usecases_buckets()

  # Find which source(s) contain the usecase
  found_source = None
  for source_uri in sources:
    try:
      available_usecases = _get_source_directories(source_uri)
      if usecase in available_usecases:
        found_source = source_uri
        break
    except Exception as e:
      typer.echo(f"Debug: Could not access source '{source_uri}': {e}", err=True)
      continue

  if not found_source:
    typer.echo(f"Error: Usecase '{usecase}' not found in any configured source")
    all_available = _get_all_source_directories()
    available = ", ".join(sorted(all_available))
    typer.echo(f"Available usecases: {available}")
    return False

  # Download from the found source
  print(f"Downloading usecase '{usecase}' from source '{found_source}'")
  blob_list = _get_blobs(found_source, usecase)
  for blob in blob_list:
    if blob.name.endswith("/"):
      continue
    destination_file_name = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "usecases/", blob.name
    )
    os.makedirs(os.path.dirname(destination_file_name), exist_ok=True)
    print(f"Downloading {blob.name} to {destination_file_name}")
    blob.download_to_filename(destination_file_name)

  return True


def _download_all_usecases(bucket: str = None) -> int:
  """Download all available usecases from configured sources.

  Args:
    bucket: Optional specific bucket to download from. If None, uses configured sources.

  Returns:
    Number of usecases successfully downloaded.
  """
  sources = [bucket] if bucket else get_usecases_buckets()

  # Get all available usecases from sources
  available_usecases = set()
  for source_uri in sources:
    try:
      directories = _get_source_directories(source_uri)
      available_usecases.update(directories)
      typer.echo(f"Found {len(directories)} usecases in source '{source_uri}'")
    except Exception as e:
      typer.echo(f"Warning: Could not access source '{source_uri}': {e}")
      continue

  if not available_usecases:
    typer.echo("No usecases found in any configured source")
    return 0

  # Get already installed usecases
  installed_usecases = set(get_usecases())

  # Determine which usecases need to be downloaded
  to_download = available_usecases - installed_usecases

  if not to_download:
    typer.echo(
        f"All {len(available_usecases)} available usecases are already installed"
    )
    return 0

  typer.echo(f"Downloading {len(to_download)} new usecases...")

  # Download each missing usecase
  downloaded_count = 0
  for usecase in sorted(to_download):
    typer.echo(f"\nDownloading usecase '{usecase}'...")
    if _download_usecase(usecase, bucket):
      downloaded_count += 1
    else:
      typer.echo(f"Failed to download usecase '{usecase}'")

  typer.echo(f"\nSuccessfully downloaded {downloaded_count} usecases")
  return downloaded_count


@usecases_app.command("get")
def usecase_get(
    usecase: str = typer.Argument(..., help="Name of the usecase to download"),
    env_file: str | None = EnvFileOption,
    bucket: str = UsecasesBucketOption,
):
  """Download a usecase from configured sources."""
  # Load environment file
  load_env_file(env_file)

  success = _download_usecase(usecase, bucket)
  if not success:
    raise typer.Exit(1)


def _get_logtypes(usecase: str, entities: bool = False) -> list[str]:
  """Get logtype names for a usecase without printing."""
  entity_or_event = "ENTITIES" if entities else "EVENTS"
  usecase_dir = f"{os.path.split(__file__)[0]}/usecases/{usecase}/{entity_or_event}/"
  log_files = glob.glob(usecase_dir + "*.log")
  log_types = []
  for log_file in log_files:
    parts = os.path.split(log_file)
    log_type = os.path.splitext(parts[-1])[0]
    log_types.append(log_type)
  return log_types


def get_usecases() -> list[str]:
  """Get all available usecases."""
  usecase_dirs = glob.glob(
      os.path.join(os.path.dirname(os.path.abspath(__file__)), "usecases/*")
  )
  usecases = []
  for usecase_dir in usecase_dirs:
    parts = os.path.split(usecase_dir)
    usecases.append(parts[-1])
  return usecases


def _load_and_validate_params(
    env_file: str | None,
    credentials_path: str | None,
    customer_id: str | None,
    region: str | None,
    impersonate_service_account: str | None = None,
    api_type: str | None = None,
) -> tuple[str | None, str, str]:
  """Load environment file and validate/resolve required parameters."""
  # Load environment file first
  load_env_file(env_file)

  # Resolve parameters using environment variables as fallback
  final_credentials = credentials_path or get_credentials_default()
  final_customer_id = customer_id or get_customer_id_default()
  final_region = region or get_region_default()
  final_api_type = api_type or os.environ.get("LOGSTORY_API_TYPE", "").lower()
  final_impersonate = impersonate_service_account or os.environ.get(
      "LOGSTORY_IMPERSONATE_SERVICE_ACCOUNT"
  )

  # Check if ADC is available when using impersonation with REST API
  has_adc = has_application_default_credentials()
  can_use_adc = has_adc and final_impersonate and final_api_type == "rest"

  # STRICT VALIDATION for REST API
  if final_api_type == "rest":
    # Check for project ID if REST API is explicitly requested
    project_id = os.environ.get("LOGSTORY_PROJECT_ID")
    if not project_id:
      typer.echo("Error: REST API is specified but missing required parameters!")
      typer.echo("")
      typer.echo("LOGSTORY_API_TYPE=rest requires:")
      typer.echo("  • LOGSTORY_PROJECT_ID (Google Cloud project ID)")
      typer.echo("")
      typer.echo("Current configuration:")
      typer.echo(f"  • API Type: {final_api_type}")
      typer.echo(f"  • Project ID: {project_id or 'NOT SET'}")
      typer.echo("")
      typer.echo("Fix by adding to your .env file or environment:")
      typer.echo("  LOGSTORY_PROJECT_ID=your-project-id")
      typer.echo("")
      typer.echo("Or use auto-detection by removing LOGSTORY_API_TYPE")
      raise typer.Exit(1)

  # Validate required parameters
  if not final_customer_id or (not final_credentials and not can_use_adc):
    missing = []
    if not final_credentials and not can_use_adc:
      if final_impersonate and final_api_type == "rest":
        missing.append(
            "--credentials-path (or LOGSTORY_CREDENTIALS/LOGSTORY_CREDENTIALS_PATH, or"
            " use Application Default Credentials)"
        )
      else:
        missing.append(
            "--credentials-path (or LOGSTORY_CREDENTIALS/LOGSTORY_CREDENTIALS_PATH)"
        )
    if not final_customer_id:
      missing.append("--customer-id (or LOGSTORY_CUSTOMER_ID)")

    typer.echo(f"Error: Missing required parameters: {', '.join(missing)}")
    typer.echo("You can provide these via:")
    typer.echo("  1. Command line options: --credentials-path and --customer-id")
    typer.echo(
        "  2. Environment variables: LOGSTORY_CREDENTIALS or LOGSTORY_CREDENTIALS_PATH"
        " and LOGSTORY_CUSTOMER_ID"
    )
    typer.echo("  3. .env file with --env-file option")
    if final_impersonate and final_api_type == "rest" and not has_adc:
      typer.echo(
          "  4. Application Default Credentials (run 'gcloud auth application-default"
          " login')"
      )
    raise typer.Exit(1)

  # Additional validation
  if final_credentials:
    final_credentials = validate_credentials_file(final_credentials)
  if final_customer_id:
    final_customer_id = validate_uuid4(final_customer_id)

  return final_credentials, final_customer_id, final_region


def _set_environment_vars(
    credentials_path: str | None,
    customer_id: str | None,
    region: str | None,
    api_type: str | None = None,
    project_id: str | None = None,
    forwarder_name: str | None = None,
    impersonate_service_account: str | None = None,
):
  """Set environment variables from CLI parameters."""
  if customer_id:
    os.environ["CUSTOMER_ID"] = customer_id
    typer.echo(f"Customer ID: {customer_id}")

  if credentials_path:
    os.environ["CREDENTIALS_PATH"] = credentials_path
    typer.echo(f"Credentials path: {credentials_path}")

  if region:
    os.environ["REGION"] = region

  # Set new REST API related environment variables
  if api_type:
    os.environ["LOGSTORY_API_TYPE"] = api_type
    typer.echo(f"API Type: {api_type}")

  if project_id:
    os.environ["LOGSTORY_PROJECT_ID"] = project_id
    typer.echo(f"Project ID: {project_id}")

  if forwarder_name:
    os.environ["LOGSTORY_FORWARDER_NAME"] = forwarder_name

  if impersonate_service_account:
    os.environ["LOGSTORY_IMPERSONATE_SERVICE_ACCOUNT"] = impersonate_service_account


@replay_app.command("all")
def replay_all_usecases(
    env_file: str | None = EnvFileOption,
    credentials_path: str | None = CredentialsOption,
    customer_id: str | None = CustomerIdOption,
    region: str | None = RegionOption,
    entities: bool = EntitiesOption,
    timestamp_delta: str | None = TimestampDeltaOption,
    local_file_output: bool = LocalFileOutputOption,
    api_type: str | None = ApiTypeOption,
    project_id: str | None = ProjectIdOption,
    forwarder_name: str | None = ForwarderNameOption,
    impersonate_service_account: str | None = ImpersonateServiceAccountOption,
    get_if_missing: bool = typer.Option(
        None,
        "--get/--no-get",
        help=(
            "Download all available usecases from configured sources (env:"
            " LOGSTORY_AUTO_GET). Use --no-get to override environment variable."
        ),
    ),
    usecases_bucket: str | None = UsecasesBucketOption,
):
  """Replay all usecases."""
  # Load environment file first (needed for download logic)
  load_env_file(env_file)

  # Determine if we should auto-get: CLI flag takes precedence over env var
  if get_if_missing is None:
    get_if_missing = get_auto_get_default()

  # Download all available usecases if requested
  if get_if_missing:
    typer.echo("Checking for available usecases to download...")
    downloaded = _download_all_usecases(usecases_bucket)
    if downloaded > 0:
      typer.echo(f"Downloaded {downloaded} new usecases")

  # Skip credential validation if using local file output
  if not local_file_output:
    final_credentials, final_customer_id, final_region = _load_and_validate_params(
        env_file,
        credentials_path,
        customer_id,
        region,
        impersonate_service_account,
        api_type,
    )
    _set_environment_vars(
        final_credentials,
        final_customer_id,
        final_region,
        api_type,
        project_id,
        forwarder_name,
        impersonate_service_account,
    )
  else:
    # Still set API-related environment variables for local file output
    _set_environment_vars(
        None,
        None,
        region,
        api_type,
        project_id,
        forwarder_name,
        impersonate_service_account,
    )

  usecases = get_usecases()
  _replay_usecases(usecases, "*", entities, timestamp_delta, local_file_output)


@replay_app.command("usecase")
def replay_usecase(
    usecase: str = typer.Argument(..., help="Name of the usecase to replay"),
    env_file: str | None = EnvFileOption,
    credentials_path: str | None = CredentialsOption,
    customer_id: str | None = CustomerIdOption,
    region: str | None = RegionOption,
    entities: bool = EntitiesOption,
    timestamp_delta: str | None = TimestampDeltaOption,
    local_file_output: bool = LocalFileOutputOption,
    get_if_missing: bool = typer.Option(
        None,
        "--get/--no-get",
        help=(
            "Download usecase if not already installed (env: LOGSTORY_AUTO_GET). "
            "Use --no-get to override environment variable."
        ),
    ),
    api_type: str | None = ApiTypeOption,
    project_id: str | None = ProjectIdOption,
    forwarder_name: str | None = ForwarderNameOption,
    impersonate_service_account: str | None = ImpersonateServiceAccountOption,
):
  """Replay a specific usecase."""
  # Load environment file first (needed for download logic)
  load_env_file(env_file)

  # Determine if we should auto-get: CLI flag takes precedence over env var
  if get_if_missing is None:
    get_if_missing = get_auto_get_default()

  # Check if usecase exists and download if requested
  if get_if_missing and usecase not in get_usecases():
    print(f"Usecase '{usecase}' not found locally, downloading...")
    success = _download_usecase(usecase)
    if not success:
      raise typer.Exit(1)

  # Check if usecase exists after download attempt
  available_usecases = get_usecases()
  if usecase not in available_usecases:
    print(
        f"Usecase '{usecase}' not found. Available usecases:"
        f" {', '.join(sorted(available_usecases))}"
    )
    raise typer.Exit(1)

  # Skip credential validation if using local file output
  if not local_file_output:
    final_credentials, final_customer_id, final_region = _load_and_validate_params(
        env_file,
        credentials_path,
        customer_id,
        region,
        impersonate_service_account,
        api_type,
    )
    _set_environment_vars(
        final_credentials,
        final_customer_id,
        final_region,
        api_type,
        project_id,
        forwarder_name,
        impersonate_service_account,
    )
  else:
    # Still set API-related environment variables for local file output
    _set_environment_vars(
        None,
        None,
        region,
        api_type,
        project_id,
        forwarder_name,
        impersonate_service_account,
    )

  usecases = [usecase]
  logtypes = _get_logtypes(usecase, entities=entities)
  if not logtypes:
    print(f"No logs found for usecase '{usecase}'")
    raise typer.Exit(1)
  _replay_usecases(usecases, logtypes, entities, timestamp_delta, local_file_output)


@replay_app.command("logtype")
def replay_usecase_logtype(
    usecase: str = typer.Argument(..., help="Name of the usecase"),
    logtypes: str = typer.Argument(..., help="Comma-separated list of logtypes"),
    env_file: str | None = EnvFileOption,
    credentials_path: str | None = CredentialsOption,
    customer_id: str | None = CustomerIdOption,
    region: str | None = RegionOption,
    entities: bool = EntitiesOption,
    timestamp_delta: str | None = TimestampDeltaOption,
    local_file_output: bool = LocalFileOutputOption,
    api_type: str | None = ApiTypeOption,
    project_id: str | None = ProjectIdOption,
    forwarder_name: str | None = ForwarderNameOption,
    impersonate_service_account: str | None = ImpersonateServiceAccountOption,
):
  """Replay specific logtypes from a usecase."""
  # Skip credential validation if using local file output
  if not local_file_output:
    final_credentials, final_customer_id, final_region = _load_and_validate_params(
        env_file,
        credentials_path,
        customer_id,
        region,
        impersonate_service_account,
        api_type,
    )
    _set_environment_vars(
        final_credentials,
        final_customer_id,
        final_region,
        api_type,
        project_id,
        forwarder_name,
        impersonate_service_account,
    )
  else:
    # Load env file but don't require credentials for local file output
    load_env_file(env_file)
    # Still set API-related environment variables for local file output
    _set_environment_vars(
        None,
        None,
        region,
        api_type,
        project_id,
        forwarder_name,
        impersonate_service_account,
    )

  usecases = [usecase]
  logtype_list = [lt.strip() for lt in logtypes.split(",")]
  _replay_usecases(usecases, logtype_list, entities, timestamp_delta, local_file_output)


def _replay_usecases(
    usecases: list[str],
    logtypes: list[str] | str,
    entities: bool,
    timestamp_delta: str | None,
    local_file_output: bool = False,
):
  """Core replay logic shared by replay commands."""
  # Late import to avoid circular imports
  try:
    from . import main as imported_main  # type: ignore
  except ImportError:
    import main as imported_main  # type: ignore

  logstory_exe_time = _get_current_time()
  logs_loaded = False

  for use_case in usecases:
    if logtypes == "*":
      current_logtypes = _get_logtypes(use_case, entities=entities)
    else:
      current_logtypes = logtypes if isinstance(logtypes, list) else [logtypes]

    old_base_time = None
    for log_type in current_logtypes:
      old_base_time = None
      log_type = log_type.strip()
      typer.echo(f"Processing usecase: {use_case}, logtype: {log_type}")

      old_base_time = imported_main.usecase_replay_logtype(
          use_case,
          log_type,
          logstory_exe_time,
          old_base_time,
          timestamp_delta=timestamp_delta,
          entities=entities,
          local_file_output=local_file_output,
      )
      logs_loaded = True

    if logs_loaded:
      typer.echo(f"""UDM Search for the loaded logs:
    metadata.ingested_timestamp.seconds >= {int(logstory_exe_time.timestamp())}
    metadata.ingestion_labels["log_replay"]="true"
    metadata.ingestion_labels["replayed_from"]="logstory"
    metadata.ingestion_labels["source_usecase"]="{use_case}"
    """)


def entry_point():
  """Main entry point for the CLI."""
  app()


if __name__ == "__main__":
  app()
