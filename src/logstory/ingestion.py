# Copyright 2026 Google LLC
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
"""Ingestion backend abstraction for Logstory supporting multiple APIs."""

import base64
import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import requests as real_requests

from .auth import AuthHandler

LOGGER = logging.getLogger(__name__)

HTTP_STATUS_OK = 200
HTTP_STATUS_BAD_REQUEST = 400

LEGACY_REGION_URL_MAP = {
    "us": "https://malachiteingestion-pa.googleapis.com",
    "usa": "https://malachiteingestion-pa.googleapis.com",
    "europe": "https://europe-malachiteingestion-pa.googleapis.com",
    "eu": "https://europe-malachiteingestion-pa.googleapis.com",
    "asia": "https://asia-southeast1-malachiteingestion-pa.googleapis.com",
    "asia-southeast1": "https://asia-southeast1-malachiteingestion-pa.googleapis.com",
    "uk": "https://europe-west2-malachiteingestion-pa.googleapis.com",
    "europe-west2": "https://europe-west2-malachiteingestion-pa.googleapis.com",
    "sydney": "https://australia-southeast1-malachiteingestion-pa.googleapis.com",
    "australia-southeast1": (
        "https://australia-southeast1-malachiteingestion-pa.googleapis.com"
    ),
    "tel-aviv": "https://me-west1-malachiteingestion-pa.googleapis.com",
    "me-west1": "https://me-west1-malachiteingestion-pa.googleapis.com",
    "doha": "https://me-central1-malachiteingestion-pa.googleapis.com",
    "me-central1": "https://me-central1-malachiteingestion-pa.googleapis.com",
    "paris": "https://europe-west9-malachiteingestion-pa.googleapis.com",
    "europe-west9": "https://europe-west9-malachiteingestion-pa.googleapis.com",
    "frankfurt": "https://europe-west3-malachiteingestion-pa.googleapis.com",
    "europe-west3": "https://europe-west3-malachiteingestion-pa.googleapis.com",
    "turin": "https://europe-west12-malachiteingestion-pa.googleapis.com",
    "europe-west12": "https://europe-west12-malachiteingestion-pa.googleapis.com",
    "zurich": "https://europe-west6-malachiteingestion-pa.googleapis.com",
    "europe-west6": "https://europe-west6-malachiteingestion-pa.googleapis.com",
}

REST_REGION_NAME_MAP = {
    "us": "us-central1",
    "usa": "us-central1",
    "us-central1": "us-central1",
    "europe": "europe-west1",
    "eu": "europe-west1",
    "europe-west1": "europe-west1",
    "asia": "asia-southeast1",
    "asia-southeast1": "asia-southeast1",
    "uk": "europe-west2",
    "europe-west2": "europe-west2",
    "sydney": "australia-southeast1",
    "australia-southeast1": "australia-southeast1",
    "tel-aviv": "me-west1",
    "me-west1": "me-west1",
    "doha": "me-central1",
    "me-central1": "me-central1",
    "paris": "europe-west9",
    "europe-west9": "europe-west9",
    "frankfurt": "europe-west3",
    "europe-west3": "europe-west3",
    "turin": "europe-west12",
    "europe-west12": "europe-west12",
    "zurich": "europe-west6",
    "europe-west6": "europe-west6",
}


def sanitize_log_text(text: str) -> str:
  """Sanitize special characters in log text to prevent API gateway timeouts.

  Removes or replaces trademark, copyright, and non-standard symbols that
  cause Chronicle Malachite Ingestion API timeouts.

  Args:
    text: The raw log text string to sanitize.

  Returns:
    Sanitized log text string safe for API ingestion.
  """
  if not text:
    return text

  # Strip registered trademark (\u00ae), copyright (\u00a9), trademark (\u2122)
  return text.replace("\u00ae", "").replace("\u00a9", "").replace("\u2122", "")


class IngestionBackend(ABC):
  """Abstract base class for Chronicle ingestion backends."""

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
      region: Geographic region for API endpoints
    """
    self.auth_handler = auth_handler
    self.customer_id = customer_id
    self.region = region or "US"
    self._http_client = None

  @property
  def http_client(self):
    """Get authenticated HTTP client."""
    if not self._http_client:
      self._http_client = self.auth_handler.get_http_client()
    return self._http_client

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
    """Post entities."""

  @abstractmethod
  def get_base_url(self) -> str:
    """Get the base URL for API calls."""


class LegacyIngestionBackend(IngestionBackend):
  """Ingestion backend for the legacy Malachite Ingestion API."""

  def get_base_url(self) -> str:
    """Get the base URL for legacy API based on region.

    Returns:
      Base URL string for the regional legacy API endpoint.
    """
    region = self.region.lower() if self.region else "us"
    return LEGACY_REGION_URL_MAP.get(
        region, "https://malachiteingestion-pa.googleapis.com"
    )

  def post_unstructured_logs(
      self,
      log_type: str,
      entries: list[dict[str, str]],
      labels: list[dict[str, str]],
  ) -> None:
    """Post unstructured log entries using legacy API."""
    uri = f"{self.get_base_url()}/v2/unstructuredlogentries:batchCreate"
    sanitized_entries = []
    for entry in entries:
      if isinstance(entry, dict) and "logText" in entry:
        sanitized_entries.append({"logText": sanitize_log_text(entry["logText"])})
      else:
        sanitized_entries.append(entry)

    body = {
        "customer_id": self.customer_id,
        "log_type": log_type,
        "entries": sanitized_entries,
    }
    if labels:
      body["labels"] = labels

    payload = json.dumps(body, ensure_ascii=True)
    headers = {"Content-Type": "application/json"}
    response = self.http_client.post(uri, data=payload, headers=headers)
    self._check_response(response)

  def post_udm_events(
      self, entries: list[dict[str, Any]], labels: list[dict[str, str]]
  ) -> None:
    """Post UDM events using legacy API."""
    uri = f"{self.get_base_url()}/v2/udmevents:batchCreate"
    body = {
        "customer_id": self.customer_id,
        "events": entries,
    }
    if labels:
      body["labels"] = labels

    payload = json.dumps(body, ensure_ascii=True)
    headers = {"Content-Type": "application/json"}
    response = self.http_client.post(uri, data=payload, headers=headers)
    self._check_response(response)

  def post_entities(
      self,
      log_type: str,
      entries: list[dict[str, Any]],
      labels: list[dict[str, str]],  # noqa: ARG002
  ) -> None:
    """Post entities using legacy API."""
    uri = f"{self.get_base_url()}/v2/entities:batchCreate"
    body = {
        "customer_id": self.customer_id,
        "log_type": log_type,
        "entities": entries,
    }

    payload = json.dumps(body, ensure_ascii=True)
    headers = {"Content-Type": "application/json"}
    response = self.http_client.post(uri, data=payload, headers=headers)
    self._check_response(response)

  def _check_response(self, response: real_requests.Response) -> None:
    """Check API response for errors."""
    if response.status_code >= HTTP_STATUS_BAD_REQUEST:
      try:
        response_data = response.json()
      except ValueError:
        response_data = response.text
      raise RuntimeError(
          f"Legacy API request failed (status {response.status_code}): {response_data}"
      )


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
    """Initialize REST ingestion backend.

    Args:
      auth_handler: Authentication handler instance
      customer_id: Customer/instance ID
      project_id: Google Cloud project ID
      region: Geographic region for API endpoints
      forwarder_name: Name of the forwarder to use/create
    """
    super().__init__(auth_handler, customer_id, region)
    self.project_id = project_id
    self.forwarder_name = forwarder_name or "Logstory-REST-Forwarder"
    self._forwarder_id = None
    self._forwarder_cache = {}

  def get_base_url(self) -> str:
    """Get the base URL for REST API based on region.

    Returns:
      Base URL string for the regional REST API endpoint.
    """
    region = self.region.lower() if self.region else "us"
    resolved_region = REST_REGION_NAME_MAP.get(region, region)
    return f"https://{resolved_region}-chronicle.googleapis.com"

  def _get_or_create_forwarder(self) -> str:
    """Get or create a forwarder for log ingestion.

    Returns:
      Forwarder ID string.
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

    if response.status_code == HTTP_STATUS_OK:
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
    if response.status_code == HTTP_STATUS_OK:
      forwarder = response.json()
      self._forwarder_id = forwarder["name"].split("/")[-1]
      self._forwarder_cache[self.forwarder_name] = self._forwarder_id
      return self._forwarder_id

    # If we cannot create a forwarder, try to proceed with default
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
      sanitized_log = sanitize_log_text(log_text)
      # Base64 encode the log text
      encoded_log = base64.b64encode(sanitized_log.encode("utf-8")).decode("utf-8")

      log_entry = {
          "data": encoded_log,
          "log_entry_time": datetime.now(UTC).isoformat(),
          "collection_time": datetime.now(UTC).isoformat(),
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
        entry["metadata"]["event_timestamp"] = datetime.now(UTC).isoformat()

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
    if response.status_code >= HTTP_STATUS_BAD_REQUEST:
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
