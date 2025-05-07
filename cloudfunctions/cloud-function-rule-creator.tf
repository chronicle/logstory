resource "google_storage_bucket_object" "chronicle-rule-creator" {
  name   = "chronicle-rule-creator-source.zip"
  bucket = google_storage_bucket.gcf_source_bucket_rules.name
  source = "cloudfunction-code/rule-creator/chronicle-rule-creator-source.zip"
}

resource "google_cloudfunctions2_function" "rule-creator-function" {
  name        = "${var.chronicle_tenant_tla}-chronicle-rule-creator-${random_id.bucket_suffix.hex}"
  location    = var.gcp_region
  description = "Chronicle Rule Creator Function"

  build_config {
    runtime     = "python310"
    entry_point = "rule_creator"
    environment_variables = {
        GOOGLE_RUNTIME_VERSION = "3.10.12"
        GOOGLE_PYTHON_VERSION = "3.10.12"
    }
    source {
      storage_source {
        bucket = google_storage_bucket.gcf_source_bucket_rules.name
        object = google_storage_bucket_object.chronicle-rule-creator.name
      }
    }
  }

  service_config {
    max_instance_count  = 2
    min_instance_count = 1
    available_memory    = "256M"
    timeout_seconds     = 300
    environment_variables = {
        BUCKET_NAME= google_storage_bucket.rules_bucket.name
        CUSTOMER_ID= var.chronicle_customer_id
        DETECTION_API_BASE_URL= var.detection_api_base_url
        SECRET_MANAGER_CREDENTIALS= google_secret_manager_secret.chronicle-api-key-v2.id
    }
    ingress_settings = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
    service_account_email = google_service_account.chronicle-replay-sa.email
  }
}