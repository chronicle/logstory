resource "google_cloud_scheduler_job" "entities_scheduler-24h" {
  name             = "${var.chronicle_tenant_tla}-chronicle-replay-entities-scheduler-24h-${random_id.bucket_suffix.hex}"
  description      = "Chronicle Replay Entities Scheduler - 24h"
  schedule         = "0 3 * * *"
  time_zone        = "Europe/Madrid"
  attempt_deadline = "1800s"
  region           = var.gcp_scheduler_region

  retry_config {
    retry_count = 0
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.entities-function-24h.service_config[0].uri
    body        = base64encode("{}")

    oidc_token {
      service_account_email = google_service_account.chronicle-replay-sa.email
      audience = google_cloudfunctions2_function.entities-function-24h.service_config[0].uri
    }
  }
}

