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

import requests
import time
import json
import base64
import re
import datetime
import os
import urllib
import yaml
import sys
from google.oauth2 import service_account
from google.cloud import secretmanager
from google.cloud import storage
from google.auth.transport.requests import AuthorizedSession
from googleapiclient import _auth

# Constants
DETECTION_API_BASE_URL = os.environ.get('DETECTION_API_BASE_URL')
SCOPES = ['https://www.googleapis.com/auth/chronicle-backstory']

BUCKET_NAME = os.environ.get('BUCKET_NAME')
SECRET_MANAGER_CREDENTIALS = os.environ.get('SECRET_MANAGER_CREDENTIALS')
CUSTOMER_ID = os.environ.get('CUSTOMER_ID')

secretmanager_client = secretmanager.SecretManagerServiceClient()
storage_client = storage.Client()

request = {"name": f"{SECRET_MANAGER_CREDENTIALS}/versions/latest"}

response = secretmanager_client.access_secret_version(request)
ret = response.payload.data.decode("UTF-8")

# Create a credential using Google Developer Service Account Credential and Backstory API Scope.
credentials = service_account.Credentials.from_service_account_info(json.loads(ret), scopes=SCOPES)

# Build an HTTP client which can make authorized OAuth requests.
http_client = _auth.authorized_http(credentials)

def _rule_diff(a, b):
  a_s = a.splitlines()
  b_s = b.splitlines()
  previous = [x for x in a_s if x not in b_s]
  new = [x for x in b_s if x not in a_s]
  return previous, new

def batch_create_rules():

    # check which rules exist
    uri_get = f"{DETECTION_API_BASE_URL}/v2/detect/rules?page_size=1000"
    response = http_client.request(uri_get, 'GET')
    existing_rules = json.loads(response[1].decode("utf-8"))

    # determine intersection and new rules
    existing_unchanged = []
    existing_modified = {}
    net_new = []

    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = list(storage_client.list_blobs(BUCKET_NAME))

    for blob in blobs:
        file_object = bucket.get_blob(blob.name)
        with file_object.open("r") as f:
            rule_text = f.read()
        if "rules" in existing_rules and len(existing_rules["rules"]) > 0:
            for existing_rule in existing_rules["rules"]:
                if blob.name == existing_rule["ruleName"]:  # overlap
                    prev, new = _rule_diff(existing_rule["ruleText"], rule_text)
                    if prev and new:
                        existing_modified[existing_rule["ruleId"]] = blob
                    else:
                        existing_unchanged.append(blob)
                    break
            else:
                net_new.append(blob)
        else:
            net_new.append(blob)

    if existing_unchanged:  # don't push rules which already exist
        print("\nThe following rules already exist unchanged and will not be created:\n -",
            "\n - ".join(f.name for f in existing_unchanged), "\n")

    if not (existing_modified or net_new):  # make sure there's actually changes
        print("\nINFO: No new rules to create/modify.\n")
        return "No new rules"


    if existing_modified:
        print(
            "\nThe following rules exist, but have been modified:\n -",
            "\n - ".join(f.name for f in existing_modified.values()))

    if net_new:
        print(
            "\nThe following rules will be newly created:\n -",
            "\n - ".join(f.name for f in net_new))

    success = []
    failed = []

    # interactive merge conflicts
    for rule_id, blob in existing_modified.items():
        file_object = bucket.get_blob(blob.name)
        print(rule_id + " " + blob.name)
        if file_object is not None:
            with file_object.open("r") as f:
                rule_text = f.read()
                request_body = {"rule_text": rule_text}
                uri_to_post = f"{DETECTION_API_BASE_URL}/v2/detect/rules/{rule_id}:createVersion"
                response = http_client.request(uri_to_post, 'POST', body=json.dumps(request_body))
                print(response)

    # create new rules
    for blob in net_new:
        file_object = bucket.get_blob(blob.name)
        if file_object is not None:
            with file_object.open("r") as f:
                rule_text = f.read()
                request_body = {"rule_text": rule_text}
                uri_to_post = f"{DETECTION_API_BASE_URL}/v2/detect/rules"
                response = http_client.request(uri_to_post, "POST", body=json.dumps(request_body))
                print(response)


        if response[0]["status"] == "200":
            success.append(blob.name)
        else:
            failed.append(blob.name)

    if success:
        print(f"Successfully created {len(success)} new rule(s).\n")

    if failed:
        print(f"Failed to create {len(failed)} rule(s):\n",
            "\n".join(f.name for f in failed), "\n", sep="")

    return "FINISHED PROCESSING..."

def batch_enable_alerting_rules():
    uri_get = f"{DETECTION_API_BASE_URL}/v2/detect/rules?page_size=1000"
    list_rules = http_client.request(uri_get, 'GET')
    existing_rules = json.loads(list_rules[1].decode("utf-8"))

    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = list(storage_client.list_blobs(BUCKET_NAME))

    for blob in blobs:
        file_object = bucket.get_blob(blob.name)
        for existing_rule in existing_rules["rules"]:
            if blob.name == existing_rule["ruleName"]:  # overlap
                rule_id = existing_rule["ruleId"]
                rule_name = existing_rule["ruleName"]
                if "liveRuleEnabled" not in existing_rule:
                    uri_to_enable = f"{DETECTION_API_BASE_URL}/v2/detect/rules/{rule_id}:enableLiveRule"
                    enable_rule = http_client.request(uri_to_enable, 'POST')
                    print("Rule enabled: " + rule_name)
                if "alertingEnabled" not in existing_rule:
                    uri_to_alerting = f"{DETECTION_API_BASE_URL}/v2/detect/rules/{rule_id}:enableAlerting"
                    alerting_rule = http_client.request(uri_to_alerting, 'POST')
                    print("Rule alerting: " + rule_name)

    return "Rules enabled and alerting"

def rule_creator(request):
    batch_create_rules()
    batch_enable_alerting_rules()
    return "Finished successfully"