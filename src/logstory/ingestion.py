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
"""Ingestion backend abstraction for Logstory to support multiple APIs."""

import base64
import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import requests as real_requests

from .auth import AuthHandler


class IngestionBackend(ABC):
  """Abstract base class for ingestion backends."""

  def __init__(
      self,
      auth_handler: AuthHandler,
      customer_id: str,
      region: str | None = None,
  ):
    """Initialize ingestion backend.

    Args:
      auth_handler: Authentication handler instance
      customer_id: Customer/instance ID
      region: Geographic region for the API
    """
    self.auth_handler = auth_handler
    self.customer_id = customer_id
    self.region = region or os.environ.get("LOGSTORY_REGION", "US")
    self.http_client = auth_handler.get_http_client()

  @abstractmethod
  def post_unstructured_logs(
      self,
      log_type: str,
      entries: list[dict[str, str]],
      labels: list[dict[str, str]],
  ) -> None:
    """Post unstructured log entries."""

  @abstractmethod
  def post_udm_events(
      self, entries: list[dict[str, Any]], labels: list[dict[str, str]]
  ) -> None:
    """Post UDM events."""

  @abstractmethod
  def post_entities(
      self,
      log_type: str,
      entries: list[dict[str, Any]],
      labels: list[dict[str, str]],
  ) -> None:
    """Post entity entries."""

  @abstractmethod
  def get_base_url(self) -> str:
    """Get the base URL for this backend."""


class LegacyIngestionBackend(IngestionBackend):
  """Ingestion backend for the legacy malachite API."""

  def get_base_url(self) -> str:
    """Get the base URL for legacy API."""
    # Handle region prefix
    url_prefix = f"{self.region.lower()}-" if self.region else ""
    if url_prefix == "us-":  # US region doesn't use prefix
      url_prefix = ""

    base_url = os.environ.get("INGESTION_API_BASE_URL")
    if base_url:
      return base_url

    return f"https://{url_prefix}malachiteingestion-pa.googleapis.com"

  def post_unstructured_logs(
      self,
      log_type: str,
      entries: list[dict[str, str]],
      labels: list[dict[str, str]],
  ) -> None:
    """Post unstructured log entries using legacy API."""
    uri = f"{self.get_base_url()}/v2/unstructuredlogentries:batchCreate"
    body = json.dumps({
        "customer_id": self.customer_id,
        "log_type": log_type,
        "entries": entries,
        "labels": labels,
    })

    response = self.http_client.post(uri, data=body)
    self._check_response(response)

  def post_udm_events(
      self, entries: list[dict[str, Any]], labels: list[dict[str, str]]
  ) -> None:
    """Post UDM events using legacy API."""
    # Add labels to each event's metadata
    for entry in entries:
      if "metadata" not in entry:
        entry["metadata"] = {}
      entry["metadata"]["ingestion_labels"] = labels

    uri = f"{self.get_base_url()}/v2/udmevents:batchCreate"
    data = {
        "customer_id": self.customer_id,
        "events": entries,
    }

    response = self.http_client.post(uri, json=data)
    self._check_response(response)

  def post_entities(
      self,
      log_type: str,
      entries: list[dict[str, Any]],
      labels: list[dict[str, str]],
  ) -> None:
    """Post entities using legacy API."""
    uri = f"{self.get_base_url()}/v2/entities:batchCreate"
    body = json.dumps({
        "customer_id": self.customer_id,
        "log_type": log_type,
        "entities": entries,
    })

    response = self.http_client.post(uri, data=body)
    self._check_response(response)

  def _check_response(self, response: real_requests.Response) -> None:
    """Check API response for errors."""
    try:
      response.raise_for_status()
    except real_requests.exceptions.HTTPError as err:
      try:
        response_data = response.json()
      except ValueError:
        response_data = response.text
      raise RuntimeError(f"API request failed: {response_data}") from err


class RestIngestionBackend(IngestionBackend):
  """Ingestion backend for the new Chronicle REST API."""

  def __init__(
      self,
      auth_handler: AuthHandler,
      customer_id: str,
      project_id: str,
      region: str | None = None,
      forwarder_name: str | None = None,
  ):
    """Initialize REST API ingestion backend.

    Args:
      auth_handler: Authentication handler instance
      customer_id: Customer/instance ID
      project_id: Google Cloud project ID
      region: Geographic region for the API
      forwarder_name: Optional custom forwarder name
    """
    super().__init__(auth_handler, customer_id, region)
    self.project_id = project_id
    self.forwarder_name = forwarder_name or "Logstory-REST-Forwarder"
    self._forwarder_id = None
    self._forwarder_cache = {}

  def get_base_url(self) -> str:
    """Get the base URL for REST API."""
    # Map region to Chronicle API format
    region = self.region.lower()
    if region in ["us", ""]:
      region = "us"
    elif region in ["eu", "europe"]:
      region = "europe"
    elif region in ["uk", "london"]:
      region = "europe-west2"
    elif region in ["asia", "asia-southeast1"]:
      region = "asia-southeast1"
    elif region in ["sydney", "australia-southeast1"]:
      region = "australia-southeast1"
    elif region in ["tel_aviv", "me-west1"]:
      region = "me-west1"
    elif region in ["dammam", "me-central1"]:
      region = "me-central1"
    elif region in ["paris", "europe-west9"]:
      region = "europe-west9"
    elif region in ["frankfurt", "europe-west3"]:
      region = "europe-west3"
    elif region in ["turin", "europe-west12"]:
      region = "europe-west12"
    elif region in ["zurich", "europe-west6"]:
      region = "europe-west6"

    return f"https://{region}-chronicle.googleapis.com"

  def _get_or_create_forwarder(self) -> str:
    """Get or create a forwarder for log ingestion.

    Returns:
      Forwarder ID
    """
    if self._forwarder_id:
      return self._forwarder_id

    # Check cache
    if self.forwarder_name in self._forwarder_cache:
      self._forwarder_id = self._forwarder_cache[self.forwarder_name]
      return self._forwarder_id

    parent = (
        f"projects/{self.project_id}/locations/{self.region.lower()}"
        f"/instances/{self.customer_id}"
    )

    # Try to list existing forwarders
    list_url = f"{self.get_base_url()}/v1alpha/{parent}/forwarders"
    response = self.http_client.get(list_url)

    if response.status_code == 200:
      forwarders = response.json().get("forwarders", [])
      for forwarder in forwarders:
        if forwarder.get("displayName") == self.forwarder_name:
          # Extract ID from resource name
          self._forwarder_id = forwarder["name"].split("/")[-1]
          self._forwarder_cache[self.forwarder_name] = self._forwarder_id
          return self._forwarder_id

    # Create new forwarder if not found
    create_url = f"{self.get_base_url()}/v1alpha/{parent}/forwarders"
    payload = {
        "displayName": self.forwarder_name,
        "config": {
            "uploadCompression": False,
            "metadata": {},
            "serverSettings": {
                "enabled": False,
                "httpSettings": {"routeSettings": {}},
            },
        },
    }

    response = self.http_client.post(create_url, json=payload)
    if response.status_code == 200:
      forwarder = response.json()
      self._forwarder_id = forwarder["name"].split("/")[-1]
      self._forwarder_cache[self.forwarder_name] = self._forwarder_id
      return self._forwarder_id

    # If we can't create a forwarder, try to proceed without one
    # Some endpoints may work without explicit forwarder
    return "default"

  def post_unstructured_logs(
      self,
      log_type: str,
      entries: list[dict[str, str]],
      labels: list[dict[str, str]],
  ) -> None:
    """Post unstructured log entries using REST API."""
    parent = (
        f"projects/{self.project_id}/locations/{self.region.lower()}"
        f"/instances/{self.customer_id}"
    )

    # Get or create forwarder
    forwarder_id = self._get_or_create_forwarder()
    forwarder_resource = f"{parent}/forwarders/{forwarder_id}"

    # REST API endpoint for log ingestion
    url = f"{self.get_base_url()}/v1alpha/{parent}/logTypes/{log_type}/logs:import"

    # Convert entries to REST API format
    logs = []
    for entry in entries:
      log_text = entry.get("logText", "")
      # Base64 encode the log text
      encoded_log = base64.b64encode(log_text.encode("utf-8")).decode("utf-8")

      log_entry = {
          "data": encoded_log,
          "log_entry_time": datetime.now().isoformat() + "Z",
          "collection_time": datetime.now().isoformat() + "Z",
      }

      # Add labels if provided
      if labels:
        log_entry["labels"] = {
            label["key"]: {"value": label["value"]} for label in labels
        }

      logs.append(log_entry)

    # Construct request payload
    payload = {"inline_source": {"logs": logs, "forwarder": forwarder_resource}}

    response = self.http_client.post(url, json=payload)
    self._check_response(response)

  def post_udm_events(
      self, entries: list[dict[str, Any]], labels: list[dict[str, str]]
  ) -> None:
    """Post UDM events using REST API."""
    parent = (
        f"projects/{self.project_id}/locations/{self.region.lower()}"
        f"/instances/{self.customer_id}"
    )

    url = f"{self.get_base_url()}/v1alpha/{parent}/events:import"

    # Process events
    events = []
    for entry in entries:
      # Ensure event has required metadata
      if "metadata" not in entry:
        entry["metadata"] = {}

      # Add timestamp if missing
      if "event_timestamp" not in entry["metadata"]:
        entry["metadata"]["event_timestamp"] = datetime.now().isoformat() + "Z"

      # Add ID if missing
      if "id" not in entry["metadata"]:
        entry["metadata"]["id"] = str(uuid.uuid4())

      # Add labels to metadata
      if labels:
        if "ingestion_labels" not in entry["metadata"]:
          entry["metadata"]["ingestion_labels"] = []
        entry["metadata"]["ingestion_labels"].extend(labels)

      events.append({"udm": entry})

    # Format request body
    body = {"inline_source": {"events": events}}

    response = self.http_client.post(url, json=body)
    self._check_response(response)

  def post_entities(
      self,
      log_type: str,
      entries: list[dict[str, Any]],
      labels: list[dict[str, str]],
  ) -> None:
    """Post entities using REST API.

    Note: The REST API entity ingestion may differ from legacy.
    This is a best-effort implementation based on UDM patterns.
    """
    parent = (
        f"projects/{self.project_id}/locations/{self.region.lower()}"
        f"/instances/{self.customer_id}"
    )

    # Try using a similar endpoint pattern as UDM
    # This may need adjustment based on actual API documentation
    url = f"{self.get_base_url()}/v1alpha/{parent}/entities:import"

    # Format entities for REST API
    entities = []
    for entry in entries:
      entity = {
          "entity": entry,
          "log_type": log_type,
      }
      if labels:
        entity["labels"] = {label["key"]: label["value"] for label in labels}
      entities.append(entity)

    body = {"inline_source": {"entities": entities}}

    response = self.http_client.post(url, json=body)
    self._check_response(response)

  def _check_response(self, response: real_requests.Response) -> None:
    """Check API response for errors."""
    if response.status_code >= 400:
      try:
        response_data = response.json()
      except ValueError:
        response_data = response.text
      raise RuntimeError(
          f"REST API request failed (status {response.status_code}): {response_data}"
      )


def create_ingestion_backend(
    auth_handler: AuthHandler,
    customer_id: str,
    api_type: str,
    project_id: str | None = None,
    region: str | None = None,
    forwarder_name: str | None = None,
) -> IngestionBackend:
  """Factory function to create the appropriate ingestion backend.

  Args:
    auth_handler: Authentication handler instance
    customer_id: Customer/instance ID
    api_type: "legacy" or "rest"
    project_id: Google Cloud project ID (required for REST)
    region: Geographic region
    forwarder_name: Custom forwarder name (REST only)

  Returns:
    IngestionBackend instance for the selected API type

  Raises:
    ValueError: If required parameters are missing for the specified API type
  """
  if api_type == "rest":
    if not project_id:
      raise ValueError(
          "REST API requires a Google Cloud project ID! Please set LOGSTORY_PROJECT_ID"
          " environment variable or pass --project-id parameter. Current API type:"
          f" {api_type}, Project ID: {project_id or 'NOT SET'}"
      )
    return RestIngestionBackend(
        auth_handler=auth_handler,
        customer_id=customer_id,
        project_id=project_id,
        region=region,
        forwarder_name=forwarder_name,
    )
  if api_type == "legacy":
    return LegacyIngestionBackend(
        auth_handler=auth_handler,
        customer_id=customer_id,
        region=region,
    )
  raise ValueError(f"Unknown API type: {api_type}. Use 'legacy' or 'rest'.")
