provider "google" {
  credentials = file(var.gcp_credential_file)
  project     = var.gcp_project_id
  region      = var.gcp_region
}
