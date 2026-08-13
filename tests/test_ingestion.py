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

"""Comprehensive tests for ingestion backends in logstory."""

import json
from unittest.mock import MagicMock

import pytest
import requests

from logstory.auth import LegacyAuthHandler, RestAuthHandler
from logstory.ingestion import (
    LegacyIngestionBackend,
    RestIngestionBackend,
    create_ingestion_backend,
)


class TestLegacyIngestionBackend:
  """Test suite for LegacyIngestionBackend."""

  def test_get_base_url_regions(self):
    """Test regional URL resolution for legacy API."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)

    us_backend = LegacyIngestionBackend(mock_auth, "c1", region="us")
    assert "malachiteingestion-pa.googleapis.com" in us_backend.get_base_url()

    eu_backend = LegacyIngestionBackend(mock_auth, "c1", region="europe")
    assert "europe-malachiteingestion-pa.googleapis.com" in eu_backend.get_base_url()

    asia_backend = LegacyIngestionBackend(mock_auth, "c1", region="asia-southeast1")
    assert (
        "asia-southeast1-malachiteingestion-pa.googleapis.com"
        in asia_backend.get_base_url()
    )

    unknown_backend = LegacyIngestionBackend(mock_auth, "c1", region="unknown_region")
    assert "malachiteingestion-pa.googleapis.com" in unknown_backend.get_base_url()

  def test_http_client_caching(self):
    """Test http_client property caching."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    mock_client = MagicMock()
    mock_auth.get_http_client.return_value = mock_client

    backend = LegacyIngestionBackend(mock_auth, "c1")
    client1 = backend.http_client
    client2 = backend.http_client

    assert client1 == mock_client
    assert client2 == mock_client
    mock_auth.get_http_client.assert_called_once()

  def test_post_unstructured_logs_with_labels(self):
    """Test posting unstructured logs with labels."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    mock_session = MagicMock()
    mock_resp = MagicMock(status_code=200)
    mock_session.post.return_value = mock_resp
    mock_auth.get_http_client.return_value = mock_session

    backend = LegacyIngestionBackend(mock_auth, "cust-123")
    entries = [{"logText": "sample log message"}]
    labels = [{"key": "env", "value": "test"}]

    backend.post_unstructured_logs("LINUX_SYSLOG", entries, labels)

    mock_session.post.assert_called_once()
    args, kwargs = mock_session.post.call_args
    assert "/v2/unstructuredlogentries:batchCreate" in args[0]
    payload = json.loads(kwargs["data"])
    assert payload["customer_id"] == "cust-123"
    assert payload["log_type"] == "LINUX_SYSLOG"
    assert payload["entries"] == [{"logText": "sample log message"}]
    assert payload["labels"] == [{"key": "env", "value": "test"}]

  def test_post_udm_events(self):
    """Test posting UDM events with legacy API."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    mock_session = MagicMock()
    mock_resp = MagicMock(status_code=200)
    mock_session.post.return_value = mock_resp
    mock_auth.get_http_client.return_value = mock_session

    backend = LegacyIngestionBackend(mock_auth, "cust-123")
    events = [{"metadata": {"event_type": "PROCESS_LAUNCH"}}]
    labels = [{"key": "source", "value": "edr"}]

    backend.post_udm_events(events, labels)

    mock_session.post.assert_called_once()
    args, kwargs = mock_session.post.call_args
    assert "/v2/udmevents:batchCreate" in args[0]
    payload = json.loads(kwargs["data"])
    assert payload["events"] == events
    assert payload["labels"] == labels

  def test_post_entities(self):
    """Test posting entities with legacy API."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    mock_session = MagicMock()
    mock_resp = MagicMock(status_code=200)
    mock_session.post.return_value = mock_resp
    mock_auth.get_http_client.return_value = mock_session

    backend = LegacyIngestionBackend(mock_auth, "cust-123")
    entities = [{"entity": {"hostname": "host1"}}]

    backend.post_entities("ASSET", entities, labels=[])

    mock_session.post.assert_called_once()
    args, kwargs = mock_session.post.call_args
    assert "/v2/entities:batchCreate" in args[0]
    payload = json.loads(kwargs["data"])
    assert payload["log_type"] == "ASSET"
    assert payload["entities"] == entities

  def test_check_response_error_handling(self):
    """Test check_response error handling for JSON and non-JSON error responses."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    backend = LegacyIngestionBackend(mock_auth, "c1")

    # Success
    resp_ok = MagicMock(spec=requests.Response, status_code=200)
    backend._check_response(resp_ok)

    # JSON error
    resp_json_err = MagicMock(spec=requests.Response, status_code=400)
    resp_json_err.json.return_value = {"error": "bad request"}
    with pytest.raises(RuntimeError, match="Legacy API request failed.*bad request"):
      backend._check_response(resp_json_err)

    # Text error (non-JSON)
    resp_text_err = MagicMock(spec=requests.Response, status_code=500)
    resp_text_err.json.side_effect = ValueError("Not JSON")
    resp_text_err.text = "Internal Server Error"
    with pytest.raises(
        RuntimeError, match="Legacy API request failed.*Internal Server Error"
    ):
      backend._check_response(resp_text_err)


class TestRestIngestionBackend:
  """Test suite for RestIngestionBackend."""

  def test_get_base_url_regions(self):
    """Test regional URL resolution for REST API."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    backend = RestIngestionBackend(mock_auth, "c1", "p1", region="europe")
    assert "europe-west1-chronicle.googleapis.com" in backend.get_base_url()

    backend_us = RestIngestionBackend(mock_auth, "c1", "p1", region="us")
    assert "us-central1-chronicle.googleapis.com" in backend_us.get_base_url()

  def test_forwarder_creation_flow(self):
    """Test forwarder listing, caching, and creation fallback."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    mock_session = MagicMock()

    # Case 1: Found in existing list
    mock_list_resp = MagicMock(status_code=200)
    mock_list_resp.json.return_value = {
        "forwarders": [{
            "displayName": "Logstory-REST-Forwarder",
            "name": "projects/p1/locations/us/instances/c1/forwarders/fwd-found-123",
        }]
    }
    mock_session.get.return_value = mock_list_resp
    mock_auth.get_http_client.return_value = mock_session

    backend = RestIngestionBackend(mock_auth, "c1", "p1", region="us")
    fwd_id = backend._get_or_create_forwarder()
    assert fwd_id == "fwd-found-123"

    # Cached access
    assert backend._get_or_create_forwarder() == "fwd-found-123"

    # Case 2: Not found in list, create succeeds
    backend_create = RestIngestionBackend(
        mock_auth, "c1", "p1", region="us", forwarder_name="Custom-Fwd"
    )
    mock_list_empty = MagicMock(status_code=200)
    mock_list_empty.json.return_value = {"forwarders": []}
    mock_create_resp = MagicMock(status_code=200)
    mock_create_resp.json.return_value = {
        "name": "projects/p1/locations/us/instances/c1/forwarders/fwd-created-456"
    }

    mock_session.get.return_value = mock_list_empty
    mock_session.post.return_value = mock_create_resp

    created_id = backend_create._get_or_create_forwarder()
    assert created_id == "fwd-created-456"

    # Case 3: Create fails, fallback to default
    backend_fail = RestIngestionBackend(
        mock_auth, "c1", "p1", region="us", forwarder_name="Fail-Fwd"
    )
    mock_create_fail = MagicMock(status_code=500)
    mock_session.post.return_value = mock_create_fail

    fallback_id = backend_fail._get_or_create_forwarder()
    assert fallback_id == "default"

  def test_post_udm_events_rest(self):
    """Test post_udm_events with metadata generation and labels."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    mock_auth.get_http_client.return_value = mock_session

    backend = RestIngestionBackend(mock_auth, "c1", "p1", region="us")

    # Test entry without metadata (should generate timestamp and UUID)
    entries = [{"principal": {"hostname": "host1"}}]
    labels = [{"key": "env", "value": "prod"}]

    backend.post_udm_events(entries, labels)

    mock_session.post.assert_called_once()
    payload = mock_session.post.call_args.kwargs["json"]
    udm_event = payload["inline_source"]["events"][0]["udm"]
    assert "metadata" in udm_event
    assert "event_timestamp" in udm_event["metadata"]
    assert "id" in udm_event["metadata"]
    assert udm_event["metadata"]["ingestion_labels"] == labels

  def test_post_entities_rest(self):
    """Test post_entities with REST API."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    mock_auth.get_http_client.return_value = mock_session

    backend = RestIngestionBackend(mock_auth, "c1", "p1", region="us")
    entries = [{"hostname": "host1", "ip": "10.0.0.1"}]
    labels = [{"key": "dept", "value": "eng"}]

    backend.post_entities("ASSET", entries, labels)

    mock_session.post.assert_called_once()
    payload = mock_session.post.call_args.kwargs["json"]
    entity_entry = payload["inline_source"]["entities"][0]
    assert entity_entry["log_type"] == "ASSET"
    assert entity_entry["labels"] == {"dept": "eng"}

  def test_check_response_error_handling(self):
    """Test check_response error handling on REST backend."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    backend = RestIngestionBackend(mock_auth, "c1", "p1", region="us")

    resp_json_err = MagicMock(spec=requests.Response, status_code=403)
    resp_json_err.json.return_value = {"error": "forbidden"}
    with pytest.raises(RuntimeError, match="REST API request failed.*forbidden"):
      backend._check_response(resp_json_err)

    resp_text_err = MagicMock(spec=requests.Response, status_code=502)
    resp_text_err.json.side_effect = ValueError()
    resp_text_err.text = "Bad Gateway"
    with pytest.raises(RuntimeError, match="REST API request failed.*Bad Gateway"):
      backend._check_response(resp_text_err)


class TestCreateIngestionBackend:
  """Test create_ingestion_backend factory function."""

  def test_create_rest_backend_success(self):
    """Test creating REST backend with valid project ID."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    backend = create_ingestion_backend(
        auth_handler=mock_auth,
        customer_id="cust1",
        api_type="rest",
        project_id="proj1",
        region="us",
    )
    assert isinstance(backend, RestIngestionBackend)
    assert backend.project_id == "proj1"

  def test_create_rest_backend_missing_project_id_raises(self):
    """Test creating REST backend without project ID raises ValueError."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    with pytest.raises(ValueError, match="REST API requires a Google Cloud project ID"):
      create_ingestion_backend(
          auth_handler=mock_auth, customer_id="cust1", api_type="rest", project_id=None
      )

  def test_create_legacy_backend(self):
    """Test creating Legacy backend."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    backend = create_ingestion_backend(
        auth_handler=mock_auth, customer_id="cust1", api_type="legacy", region="us"
    )
    assert isinstance(backend, LegacyIngestionBackend)

  def test_create_unknown_api_type_raises(self):
    """Test creating backend with invalid API type raises ValueError."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    with pytest.raises(ValueError, match="Unknown API type: custom"):
      create_ingestion_backend(
          auth_handler=mock_auth, customer_id="cust1", api_type="custom"
      )

  def test_legacy_post_unstructured_non_dict_entries(self):
    """Test legacy post_unstructured_logs with non-dict entry."""
    mock_auth = MagicMock(spec=LegacyAuthHandler)
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    mock_auth.get_http_client.return_value = mock_session

    backend = LegacyIngestionBackend(mock_auth, "cust1")
    backend.post_unstructured_logs("LINUX_SYSLOG", ["raw string entry"], labels=[])
    mock_session.post.assert_called_once()

  def test_rest_http_client_property(self):
    """Test rest http_client property initialization."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    mock_client = MagicMock()
    mock_auth.get_http_client.return_value = mock_client

    backend = RestIngestionBackend(mock_auth, "c1", "p1")
    assert backend.http_client == mock_client

  def test_rest_post_unstructured_with_labels(self):
    """Test REST post_unstructured_logs with labels."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    mock_session = MagicMock()
    mock_session.get.return_value = MagicMock(
        status_code=200,
        json=lambda: {
            "forwarders": [{
                "displayName": "Logstory-REST-Forwarder",
                "name": "projects/p/locations/us/instances/c/forwarders/fwd1",
            }]
        },
    )
    mock_session.post.return_value = MagicMock(status_code=200)
    mock_auth.get_http_client.return_value = mock_session

    backend = RestIngestionBackend(mock_auth, "c1", "p1")
    entries = [{"logText": "test line"}]
    labels = [{"key": "env", "value": "staging"}]
    backend.post_unstructured_logs("SYSLOG", entries, labels=labels)

    post_call = mock_session.post.call_args_list[-1]
    logs = post_call.kwargs["json"]["inline_source"]["logs"]
    assert logs[0]["labels"] == {"env": {"value": "staging"}}

  def test_rest_post_udm_events_with_existing_metadata(self):
    """Test REST post_udm_events when metadata, timestamp, id, and labels already exist."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    mock_auth.get_http_client.return_value = mock_session

    backend = RestIngestionBackend(mock_auth, "c1", "p1")
    existing_event = {
        "metadata": {
            "event_timestamp": "2026-01-01T00:00:00Z",
            "id": "existing-uuid-123",
            "ingestion_labels": [{"key": "existing", "value": "true"}],
        }
    }
    backend.post_udm_events([existing_event], labels=[{"key": "extra", "value": "val"}])

    post_call = mock_session.post.call_args
    event_out = post_call.kwargs["json"]["inline_source"]["events"][0]["udm"]
    assert event_out["metadata"]["id"] == "existing-uuid-123"
    assert len(event_out["metadata"]["ingestion_labels"]) == 2

  def test_rest_post_entities_without_labels(self):
    """Test REST post_entities without labels."""
    mock_auth = MagicMock(spec=RestAuthHandler)
    mock_session = MagicMock()
    mock_session.post.return_value = MagicMock(status_code=200)
    mock_auth.get_http_client.return_value = mock_session

    backend = RestIngestionBackend(mock_auth, "c1", "p1")
    backend.post_entities("ASSET", [{"hostname": "host1"}], labels=[])

    post_call = mock_session.post.call_args
    entity_out = post_call.kwargs["json"]["inline_source"]["entities"][0]
    assert "labels" not in entity_out
