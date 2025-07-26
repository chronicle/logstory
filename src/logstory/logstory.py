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
import uuid

import typer
from dotenv import load_dotenv
from google.cloud import storage
from google.oauth2 import service_account

UTC = datetime.UTC

# Create Typer app and command groups
app = typer.Typer(help="Logstory: Replay SecOps logs with updated timestamps")
usecases_app = typer.Typer(help="Manage and list usecases")
replay_app = typer.Typer(help="Replay log data")

app.add_typer(usecases_app, name="usecases")
app.add_typer(replay_app, name="replay")


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
  """Get credentials path from environment variable."""
  return os.getenv("LOGSTORY_CREDENTIALS_PATH")


def get_customer_id_default():
  """Get customer ID from environment variable."""
  return os.getenv("LOGSTORY_CUSTOMER_ID")


def get_region_default():
  """Get region from environment variable."""
  return os.getenv("LOGSTORY_REGION", "US")


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
    None,
    "--timestamp-delta",
    help=(
        "Determines how datetimes in logfiles are updated. "
        "Expressed in any/all: days, hours, minutes (d, h, m) (Default=1d). "
        "Examples: [1d, 1d1h, 1h1m, 1d1m, 1d1h1m, 1m1h, ...]. "
        "Setting only `Nd` preserves the original HH:MM:SS but updates date. "
        "Nh/Nm subtracts an additional offset from that datetime, to facilitate "
        "running logstory more than 1x per day."
    ),
)

UsecasesBucketOption = typer.Option(
    "logstory-usecases-20241216",
    "--usecases-bucket",
    help="GCP Cloud Storage bucket with additional usecases",
)


def _get_current_time():
  """Returns the current time in UTC."""
  return datetime.datetime.now(UTC)


@usecases_app.command("list-installed")
def usecases_list(
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
  # Handle --open flag as a special case
  if open_usecase:
    import subprocess

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
              subprocess.run(["code", md_file], check=True)
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
  logypes_map = {}
  markdown_map = {}
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


def _get_blobs(bucket_name, usecase=None):
  client = storage.Client.create_anonymous_client()
  bucket = client.bucket(bucket_name)
  if usecase:
    blobs = bucket.list_blobs(prefix=usecase)
  else:
    blobs = bucket.list_blobs(delimiter="/")
  return blobs


@usecases_app.command("list-available")
def list_bucket_directories(
    bucket: str = UsecasesBucketOption,
):
  """List usecases available for download from GCP bucket."""
  bucket_name = bucket
  blobs = _get_blobs(bucket_name)
  top_level_directories = []
  print(f"\nAvailable usecases in bucket '{bucket_name}':")
  for blob in blobs.pages:
    prefixes = blob.prefixes
    for prefix in prefixes:
      if "docs" in prefix:
        continue
      prefix = prefix.strip("/")
      print(f"- {prefix}")
      top_level_directories.append(prefix)
  return top_level_directories


def _get_bucket_directories(bucket_name: str) -> list[str]:
  """Helper function to get bucket directories without printing."""
  blobs = _get_blobs(bucket_name)
  top_level_directories = []
  for blob in blobs.pages:
    prefixes = blob.prefixes
    for prefix in prefixes:
      if "docs" in prefix:
        continue
      prefix = prefix.strip("/")
      top_level_directories.append(prefix)
  return top_level_directories


@usecases_app.command("get")
def usecase_get(
    usecase: str = typer.Argument(..., help="Name of the usecase to download"),
    bucket: str = UsecasesBucketOption,
):
  """Download a usecase from GCP bucket."""
  bucket_name = bucket

  # Validate usecase exists in bucket
  available_usecases = _get_bucket_directories(bucket_name)
  if usecase not in available_usecases:
    typer.echo(f"Error: Usecase '{usecase}' not found in bucket '{bucket_name}'")
    available = ", ".join(available_usecases)
    typer.echo(f"Available usecases: {available}")
    raise typer.Exit(1)
  blob_list = _get_blobs(bucket_name, usecase)
  for blob in blob_list:
    if blob.name.endswith("/"):
      continue
    destination_file_name = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "usecases/", blob.name
    )
    os.makedirs(os.path.dirname(destination_file_name), exist_ok=True)
    print(f"Downloading {blob.name} to {destination_file_name}")
    blob.download_to_filename(destination_file_name)


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
) -> tuple[str, str, str]:
  """Load environment file and validate/resolve required parameters."""
  # Load environment file first
  load_env_file(env_file)

  # Resolve parameters using environment variables as fallback
  final_credentials = credentials_path or get_credentials_default()
  final_customer_id = customer_id or get_customer_id_default()
  final_region = region or get_region_default()

  # Validate required parameters
  if not final_credentials or not final_customer_id:
    missing = []
    if not final_credentials:
      missing.append("--credentials-path (or LOGSTORY_CREDENTIALS_PATH)")
    if not final_customer_id:
      missing.append("--customer-id (or LOGSTORY_CUSTOMER_ID)")

    typer.echo(f"Error: Missing required parameters: {', '.join(missing)}")
    typer.echo("You can provide these via:")
    typer.echo("  1. Command line options: --credentials-path and --customer-id")
    typer.echo(
        "  2. Environment variables: LOGSTORY_CREDENTIALS_PATH and LOGSTORY_CUSTOMER_ID"
    )
    typer.echo("  3. .env file with --env-file option")
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


@replay_app.command("all")
def replay_all_usecases(
    env_file: str | None = EnvFileOption,
    credentials_path: str | None = CredentialsOption,
    customer_id: str | None = CustomerIdOption,
    region: str | None = RegionOption,
    entities: bool = EntitiesOption,
    timestamp_delta: str | None = TimestampDeltaOption,
):
  """Replay all usecases."""
  final_credentials, final_customer_id, final_region = _load_and_validate_params(
      env_file, credentials_path, customer_id, region
  )
  _set_environment_vars(final_credentials, final_customer_id, final_region)

  usecases = get_usecases()
  _replay_usecases(usecases, "*", entities, timestamp_delta)


@replay_app.command("usecase")
def replay_usecase(
    usecase: str = typer.Argument(..., help="Name of the usecase to replay"),
    env_file: str | None = EnvFileOption,
    credentials_path: str | None = CredentialsOption,
    customer_id: str | None = CustomerIdOption,
    region: str | None = RegionOption,
    entities: bool = EntitiesOption,
    timestamp_delta: str | None = TimestampDeltaOption,
):
  """Replay a specific usecase."""
  final_credentials, final_customer_id, final_region = _load_and_validate_params(
      env_file, credentials_path, customer_id, region
  )
  _set_environment_vars(final_credentials, final_customer_id, final_region)

  usecases = [usecase]
  logtypes = _get_logtypes(usecase, entities=entities)
  _replay_usecases(usecases, logtypes, entities, timestamp_delta)


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
):
  """Replay specific logtypes from a usecase."""
  final_credentials, final_customer_id, final_region = _load_and_validate_params(
      env_file, credentials_path, customer_id, region
  )
  _set_environment_vars(final_credentials, final_customer_id, final_region)

  usecases = [usecase]
  logtype_list = [lt.strip() for lt in logtypes.split(",")]
  _replay_usecases(usecases, logtype_list, entities, timestamp_delta)


def _replay_usecases(
    usecases: list[str],
    logtypes: list[str] | str,
    entities: bool,
    timestamp_delta: str | None,
):
  """Core replay logic shared by replay commands."""
  # Late import to avoid circular imports
  try:
    from . import main as imported_main
  except ImportError:
    import main as imported_main

  logstory_exe_time = _get_current_time()

  for use_case in usecases:
    if logtypes == "*":
      current_logtypes = _get_logtypes(use_case, entities=entities)
    else:
      current_logtypes = logtypes

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
      )

    typer.echo(f"""UDM Search for the loaded logs:
    metadata.ingested_timestamp.seconds >= {int(logstory_exe_time.timestamp())}
    metadata.ingestion_labels["log_replay"]="true"
    metadata.ingestion_labels["replayed_from"]="logstory"
    metadata.ingestion_labels["usecase_name"]="{use_case}"
    """)


def entry_point():
  """Main entry point for the CLI."""
  app()


if __name__ == "__main__":
  app()
