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
import sys
import uuid

from absl import app, flags
from google.cloud import storage
from google.oauth2 import service_account

UTC = datetime.UTC


# Validation function to check if the string is a valid UUID4
def is_valid_uuid4(value):
  """Abseil flag validation for customer id."""
  try:
    val = uuid.UUID(value, version=4)
    # Check if the string conforms to the UUID4 format
    return str(val) == value
  except ValueError:
    return False


def validate_service_account_json(json_path):
  """Abseil flag validation for credentials file."""
  # Check if the file exists
  if not os.path.isfile(json_path):
    raise FileNotFoundError(
        f"File does not exist: {json_path}.\n"
        "Please provide the complete path to a JSON credentials file.\n"
    )
  try:
    # Attempt to load the service account credentials
    _ = service_account.Credentials.from_service_account_file(json_path)
    # If it loads successfully, the path is valid
    return True, "The JSON file is valid."
  except Exception as e:
    # If an error occurs, return False and the error message
    # pylint: disable-next=broad-exception-raised
    raise Exception(f"The JSON file is invalid: {e}") from e


FLAGS = flags.FLAGS
flags.DEFINE_string(
    "credentials_path",
    None,
    "Path to JSON credentials for Ingestion API Service account.",
    short_name="c",
    required=False,  # conditionally req. depending on subcommand
)
flags.DEFINE_string(
    "customer_id",
    None,
    "Customer ID for SecOps instance, found on `/settings/profile/`.",
    required=False,  # conditionally req. depending on subcommand
)
flags.DEFINE_string(
    "region",
    None,  # "US" (default) is a regionless base url, so None works here.
    "SecOps tenant's region (Default=US). Used to set ingestion API base URL.",
    short_name="r",
    required=False,
)
flags.DEFINE_bool("entities", False, "Load Entities instead of Events")
flags.DEFINE_bool("three_day", False, "Load Entities instead of Events")
flags.DEFINE_string(
    "timestamp_delta",
    None,
    "Determines how datetimes in logfiles are updated. "
    "It is expressed in any/all: days, hours, minutes (d, h, m) (Default=1d) "
    "Examples: [1d, 1d1h, 1h1m, 1d1m, 1d1h1m, 1m1h, ...] "
    "Setting only `Nd` preserves the original HH:MM:SS but updates date. "
    "Nh/Nm subtracts an additional offset from that datetime, to facilitate "
    "running logstory more than 1x per day. ",
    required=False,
)
flags.DEFINE_string(
    "usecases_bucket",
    "logstory-usecases-20241216",  # default public bucket with usecases
    "GCP Cloud Storage bucket with additional usecases.",
    required=False,
)


def _get_current_time():
  """Returns the current time in UTC."""
  return datetime.datetime.now(UTC)


def usecases_list_logtypes():
  usecases_list(print_logtypes=True)


def get_usecases():
  """NOTE: this is *all* usecases, not just enabled in `events-24h`"""
  usecase_dirs = glob.glob(
      os.path.join(os.path.dirname(os.path.abspath(__file__)), "usecases/*")
  )
  usecases = []
  for usecase_dir in usecase_dirs:
    parts = os.path.split(usecase_dir)
    usecases.append(parts[-1])
  return usecases


def _get_blobs(bucket_name, usecase=None):
  client = storage.Client.create_anonymous_client()
  bucket = client.bucket(bucket_name)
  if usecase:
    blobs = bucket.list_blobs(prefix=usecase)
  else:
    blobs = bucket.list_blobs(delimiter="/")
  return blobs


def list_bucket_directories(bucket_name):
  """Lists the top-level directories in a GCP bucket."""
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


def usecase_get(bucket_name, usecase):
  """Download usecase from GCP bucket."""
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


# Define subcommands
def usecases_list(print_logtypes=False, entities=False):
  """Walk the usecases/ dir and print the dir names."""
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
    if print_logtypes:
      for adir in glob.glob(os.path.join("./", usecase_dir, entity_or_event, "*.log")):
        log_types.append(os.path.splitext(os.path.split(adir)[-1])[0])
      logypes_map[usecases[-1]] = log_types
  for usecase in sorted(usecases):
    print(f"#\n# {usecase}\n#")
    for md in markdown_map.get(usecase, []):
      with open(md) as fh:
        print(fh.read())
    if print_logtypes:
      for log_type in sorted(logypes_map[usecase]):
        print(f"\t{log_type}")


def get_logtypes(usecase, entities=False):
  """Walk the subdirs in usecases and print the file base names."""
  print(f"Executing usecase: {usecase}")
  # Access common flags with FLAGS.flag_name

  entity_or_event = "ENTITIES" if entities else "EVENTS"
  usecase_dir = f"{os.path.split(__file__)[0]}/usecases/{usecase}/{entity_or_event}/"
  log_files = glob.glob(usecase_dir + "*.log")
  log_types = []
  for log_file in log_files:
    print(f"log_file: {log_file}")
    parts = os.path.split(log_file)
    log_type = os.path.splitext(parts[-1])[0]
    log_types.append(log_type)
    print(f"log_type: {log_type}")
  return log_types


def local_main(argv):
  """Parse args and call the appropriate function."""
  if len(argv) < 2:
    custom_help()
    return 1
  # parse the flags
  FLAGS(argv)
  # Some params are conditionally required
  # Check if either "usecase_replay" or "usecase_replay_logtype" is in argv
  requires_customer_and_credentials = any(
      arg in argv for arg in ["usecase_replay", "usecase_replay_logtype"]
  )
  # Check if customer_id or credentials_path is missing
  missing_customer_or_credentials = not FLAGS.customer_id or not FLAGS.credentials_path
  # Combine the conditions
  if requires_customer_and_credentials and missing_customer_or_credentials:
    # Handle the case where either customer_id or credential_path is missing
    raise ValueError(
        "The following flags must be set when using the usecase_replay and"
        " usecases_list_logtypes subcommands:\n\t--credentials_path,"
        " --customer_id, ..."
    )

  # optionality was determined above. now validate if the params are present.
  if FLAGS.credentials_path:
    flags.register_validator(
        "credentials_path",
        validate_service_account_json,
        message="--credentials_path must be JSON credentials for a Service Account",
    )
  if FLAGS.customer_id:
    flags.register_validator(
        "customer_id",
        is_valid_uuid4,
        message="--customer_id must be a UUID4",
    )
  # must parse flags again to enforce validators
  FLAGS(argv)

  # if present and valid, set as env vars
  if FLAGS.customer_id:
    os.environ["CUSTOMER_ID"] = FLAGS.customer_id
    print(f"The customer_id is: {os.environ['CUSTOMER_ID']}")

  if FLAGS.credentials_path:
    os.environ["CREDENTIALS_PATH"] = FLAGS.credentials_path
    print(f"The credentials_path is: {os.environ['CREDENTIALS_PATH']}")

  # should us -> '' logic be here or in the main.py file?
  if FLAGS.region:
    os.environ["REGION"] = FLAGS.region

  if len(argv) < 2:
    print("Usage: %s {usecases_list, command_two} [options]" % argv[0])
    return 1
  command = argv[1]
  if command == "usecases_list":
    return usecases_list()
  if command == "usecases_list_logtypes":
    return usecases_list_logtypes()
  if command == "usecases_list_available":
    return list_bucket_directories(FLAGS.usecases_bucket)
  if command == "usecase_get":
    usecase = argv[2]  # flaky?
    if not usecase:
      raise ValueError("Missing usecase argument for usecase_get")
    if usecase not in list_bucket_directories(FLAGS.usecases_bucket):
      raise ValueError(
          f"Usecase '{usecase}' not found in bucket '{FLAGS.usecases_bucket}'"
      )

    return usecase_get(FLAGS.usecases_bucket, usecase)

  # late import here due to globals in the module
  try:
    from . import main as imported_main
  except ImportError:
    import main as imported_main

  if command == "usecases_replay":
    usecases = get_usecases()
    logtypes = "*"
  elif command == "usecase_replay":
    usecase = argv[2]  # flaky?
    usecases = [
        usecase,
    ]
    logtypes = get_logtypes(usecase, entities=FLAGS.entities)
  elif command == "usecase_replay_logtype":
    usecase = argv[2]  # flaky?
    usecases = [
        usecase,
    ]
    logtypes = argv[3].split(",")
  else:
    print("Unknown command: %s" % command)
    return 1

  logstory_exe_time = datetime.datetime.now(datetime.UTC)
  for use_case in usecases:
    logstory_exe_time = _get_current_time()
    if command == "usecases_replay":
      logtypes = get_logtypes(use_case)

    old_base_time = None  # resets for each usecase
    for log_type in logtypes:
      old_base_time = None  # resets for each log_type
      log_type = log_type.strip()
      print(f"usecase: {use_case}")
      print(f"{logtypes}, |{log_type}|")
      old_base_time = imported_main.usecase_replay_logtype(
          use_case,
          log_type,
          logstory_exe_time,
          old_base_time,
          timestamp_delta=FLAGS.timestamp_delta or None,
          entities=FLAGS.entities,
      )
    print(f"""UDM Search for the loaded logs:
    metadata.ingested_timestamp.seconds >= {int(logstory_exe_time.timestamp())}
    metadata.ingestion_labels["log_replay"]="true"
    metadata.ingestion_labels["replayed_from"]="logstory"
    metadata.ingestion_labels["usecase_name"]="{use_case}"
    """)  # ToDo: get upper bound of ingested and print it?

  return "Success Events!"


def custom_help():
  help_text = """
    Usage: logstory <command> [command options]

    Commands:
      usecases_list            List the usecases

      usecases_list_logtypes   List each logtype for each usecase

      usecases_list_available  List usecases that can be downloaded

      usecase_get              Download usecase from GCP bucket

      usecases_replay          Replay all usecases

      usecase_replay           Replay a specific usecase
         examples:
           usecase_replay NETWORK_ANALYSIS
           usecase_replay RULES_SEARCH_WORKSHOP
           ...

      usecase_replay_logtype   Replay a specific usecase with a specific log type
         examples:
           usecase_replay_logtype RULES_SEARCH_WORKSHOP POWERSHELL
           usecase_replay_logtype RULES_SEARCH_WORKSHOP WINEVETLOG
           usecase_replay_logtype RULES_SEARCH_WORKSHOP POWERSHELL,WINEVETLOG # No spaces without quotes
           usecase_replay_logtype RULES_SEARCH_WORKSHOP "POWERSHELL, WINEVETLOG" # Use quotes if there are spaces
           ...

      usecase_get EDR_WORKSHOP

    Usage Examples:
      logstory usecases_list

      logstory usecases_list_logtypes

      logstory usecases_replay --flagfile=config.cfg

      logstory usecase_replay NETWORK_ANALYSIS --flagfile=config.cfg
      logstory usecase_replay NETWORK_ANALYSIS --flagfile=config.cfg --timestamp_delta=1d
      logstory usecase_replay NETWORK_ANALYSIS --flagfile=config.cfg --timestamp_delta=1d1h
      logstory usecase_replay NETWORK_ANALYSIS --flagfile=config.cfg --timestamp_delta=1d1h1m
      logstory usecase_replay NETWORK_ANALYSIS --flagfile=config.cfg --timestamp_delta=1h30m

      logstory usecase_replay_logtype RULES_SEARCH_WORKSHOP POWERSHELL,WINEVETLOG --flagfile=config.cfg
      logstory usecase_replay_logtype RULES_SEARCH_WORKSHOP "POWERSHELL, WINEVETLOG" --flagfile=config.cfg

      # change loglevel and tee output to a file
      PYTHONLOGLEVEL=debug logstory ... | tee "logstory_exe_$(date +%Y%m%d_%H%M%S).log"

      # Entities
      logstory usecase_replay NETWORK_ANALYSIS --flagfile=config.cfg --timestamp_delta=1d --entities

      logstory usecase_replay_logtype NETWORK_ANALYSIS WIONDOWS_AD --flagfile=config.cfg --entities

      logstory usecase_get EDR_WORKSHOP
    """
  print(help_text)
  print(FLAGS)


def entry_point():
  if "--help" in sys.argv:
    custom_help()
    sys.exit(1)
  app.run(local_main)  # evaluates the flags


if __name__ == "__main__":
  if "--help" in sys.argv:
    custom_help()
    sys.exit(1)
  app.run(local_main)  # evaluates the flags
