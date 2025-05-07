# Create a secret for chronicle-api-key-v2
resource "google_secret_manager_secret" "chronicle-api-key-v2" {

  secret_id = "${var.chronicle_tenant_tla}-chronicle-api-key-v2-${random_id.bucket_suffix.hex}"
  replication {
    auto {}
  }
}

# Add the secret data for chronicle-api-key-v2 secret
resource "google_secret_manager_secret_version" "chronicle-api-key-v2" {
  secret = google_secret_manager_secret.chronicle-api-key-v2.id
  #secret_data = var.api_key.content
  secret_data = var.api_key
}

# Grant a user or service account IAM permissions to access the secret
resource "google_secret_manager_secret_iam_member" "chronicle_replay" {

  secret_id = google_secret_manager_secret.chronicle-api-key-v2.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.chronicle-replay-sa.email}"
}
