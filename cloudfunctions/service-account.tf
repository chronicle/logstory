resource "random_id" "sa_suffix" {
  byte_length = 2
}
# Service Account for Chronicle Replay
resource "google_service_account" "chronicle-replay-sa" {
  account_id = "${var.chronicle_tenant_tla}-ch-replay-sa-${random_id.sa_suffix.hex}"
  display_name = "Chronicle Replay Service Account"
}

resource "google_project_iam_member" "chronicle-replay-roles" {
  for_each = toset([
    "roles/cloudfunctions.invoker",
    "roles/cloudscheduler.serviceAgent",
    "roles/cloudfunctions.serviceAgent",
    "roles/run.invoker",
    "roles/storage.objectViewer",
  ])
  role = each.key
  member = "serviceAccount:${google_service_account.chronicle-replay-sa.email}"
  project = var.gcp_project_number
}
