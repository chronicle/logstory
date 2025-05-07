resource "google_storage_bucket_object" "chronicle-replay-entities-3day" {
  name   = "chronicle-replay-entities-source-3day.zip"
  bucket = google_storage_bucket.gcf_source_bucket_logstory.name
  source = "cloudfunction-code/entities-function-3day/chronicle-replay-entities-source-3day.zip"
}

resource "google_cloudfunctions2_function" "entities-function-3day" {
  name        = "${var.chronicle_tenant_tla}-chronicle-replay-entities-3day-${random_id.bucket_suffix.hex}"
  location    = var.gcp_region
  description = "Chronicle Replay Entities Function - 3day"

  build_config {
    runtime     = "python310"
    entry_point = "main"
    environment_variables = {
        GOOGLE_RUNTIME_VERSION = "3.10.12"
        GOOGLE_PYTHON_VERSION = "3.10.12"
    }
    source {
      storage_source {
        bucket = google_storage_bucket.gcf_source_bucket_logstory.name
        object = google_storage_bucket_object.chronicle-replay-entities-3day.name
      }
    }
  }

  service_config {
    max_instance_count  = 100
    min_instance_count = 1
    available_memory    = "512M"
    timeout_seconds     = 3600
    environment_variables = {
        BUCKET_NAME = google_storage_bucket.replay_usecases_bucket.name
        CUSTOMER_ID = var.chronicle_customer_id
        ENTITIES = true
        INGESTION_API_BASE_URL = var.ingestion_api_base_url
        SECRET_MANAGER_CREDENTIALS = google_secret_manager_secret.chronicle-api-key-v2.id
    }
    ingress_settings = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
    service_account_email = google_service_account.chronicle-replay-sa.email
  }
}
