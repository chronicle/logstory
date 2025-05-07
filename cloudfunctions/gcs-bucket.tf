resource "random_id" "bucket_suffix" {
  byte_length = 10
}

resource "google_storage_bucket" "gcf_source_bucket_logstory" {
  name                        = "${var.chronicle_tenant_tla}-chronicle-replay-gcf-source-${random_id.bucket_suffix.hex}" # Every bucket name must be globally unique
  location                    = var.gcs_bucket_location
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "replay_usecases_bucket" {
  name                        = "${var.chronicle_tenant_tla}-chronicle-replay-use-cases-${random_id.bucket_suffix.hex}" # Every bucket name must be globally unique
  location                    = var.gcs_bucket_location
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "null_resource" "upload_chronicle_usecases_to_gcs" {
  provisioner "local-exec" {
    command = <<EOF
    gsutil rsync -r usecases gs://${google_storage_bucket.replay_usecases_bucket.name}
    EOF
  }
}

resource "google_storage_bucket" "gcf_source_bucket_rules" {
  name                        = "${var.chronicle_tenant_tla}-chronicle-rules-gcf-source-${random_id.bucket_suffix.hex}" # Every bucket name must be globally unique
  location                    = var.gcs_bucket_location
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "rules_bucket" {
  name                        = "${var.chronicle_tenant_tla}-chronicle-rules-${random_id.bucket_suffix.hex}" # Every bucket name must be globally unique
  location                    = var.gcs_bucket_location
  force_destroy               = true
  uniform_bucket_level_access = true
}

resource "null_resource" "upload_chronicle_rules_to_gcs" {
  provisioner "local-exec" {
    command = <<EOF
    gsutil rsync -r rules gs://${google_storage_bucket.rules_bucket.name}
    EOF
  }
}