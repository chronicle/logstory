resource "google_cloud_scheduler_job" "entities_scheduler-3day" {
  name             = "${var.chronicle_tenant_tla}-chronicle-replay-entities-scheduler-3day-${random_id.bucket_suffix.hex}"
  description      = "Chronicle Replay Entities Scheduler - 3day"
  schedule         = "0 3 */3 * *"
  time_zone        = "Europe/Madrid"
  attempt_deadline = "1800s"
  region           = var.gcp_scheduler_region

  retry_config {
    retry_count = 0
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.entities-function-3day.service_config[0].uri
    body        = base64encode("{}")

    oidc_token {
      service_account_email = google_service_account.chronicle-replay-sa.email
      audience = google_cloudfunctions2_function.entities-function-3day.service_config[0].uri
    }
  }
}

