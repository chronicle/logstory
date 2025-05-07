resource "google_cloud_scheduler_job" "events_scheduler-24h" {
  name             = "${var.chronicle_tenant_tla}-chronicle-replay-events-scheduler-24h-${random_id.bucket_suffix.hex}"
  description      = "Chronicle Replay Events Scheduler - 24h"
  schedule         = "0 8 * * *"
  time_zone        = "Europe/Madrid"
  attempt_deadline = "1800s"
  region           = var.gcp_scheduler_region

  retry_config {
    retry_count = 0
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.events-function-24h.service_config[0].uri
    body        = base64encode("{}")

    oidc_token {
      service_account_email = google_service_account.chronicle-replay-sa.email
      audience = google_cloudfunctions2_function.events-function-24h.service_config[0].uri
    }
  }
}