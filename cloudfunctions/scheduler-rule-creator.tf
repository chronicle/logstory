resource "google_cloud_scheduler_job" "rule_creator_scheduler" {
  name             = "${var.chronicle_tenant_tla}-chronicle-rules-creator-scheduler-${random_id.bucket_suffix.hex}"
  description      = "Chronicle Rules Creator Scheduler"
  schedule         = "0 6 * * *"
  time_zone        = "Europe/Madrid"
  attempt_deadline = "1800s"
  region           = var.gcp_scheduler_region
  paused           = var.rule_creator_paused

  retry_config {
    retry_count = 0
  }

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.rule-creator-function.service_config[0].uri
    body        = base64encode("{}")

    oidc_token {
      service_account_email = google_service_account.chronicle-replay-sa.email
      audience = google_cloudfunctions2_function.rule-creator-function.service_config[0].uri
    }
  }
}