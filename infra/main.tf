provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

variable "gcp_project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "The GCP Region"
  type        = string
  default     = "us-central1"
}

# 1. Enable Required APIs
resource "google_project_service" "cloudrun" {
  service = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "compute" {
  service = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  service = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# 2. Secret Manager (Bot Token, VPN Creds)
resource "google_secret_manager_secret" "telegram_token" {
  secret_id = "telegram-bot-token"
  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }
}

# 3. Cloud Storage Bucket for Large Files
resource "google_storage_bucket" "archive_bucket" {
  name          = "${var.gcp_project_id}-pfirsichfest-archive"
  location      = var.gcp_region
  force_destroy = true
  uniform_bucket_level_access = true
}

# 4. Service Accounts
resource "google_service_account" "bot_sa" {
  account_id   = "pfirsichfest-bot-sa"
  display_name = "Pfirsichfest Telegram Bot SA"
}

resource "google_service_account" "downloader_sa" {
  account_id   = "pfirsichfest-downloader-sa"
  display_name = "Pfirsichfest Downloader VM SA"
}

# 5. IAM Permissions
# Bot needs to spin up VMs and read secrets
resource "google_project_iam_member" "bot_compute_admin" {
  project = var.gcp_project_id
  role    = "roles/compute.admin"
  member  = "serviceAccount:${google_service_account.bot_sa.email}"
}

# Downloader needs to read secrets, write to GCS, and delete itself
resource "google_storage_bucket_iam_member" "downloader_storage" {
  bucket = google_storage_bucket.archive_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.downloader_sa.email}"
}

# 6. Bot Cloud Run Service
resource "google_cloud_run_v2_service" "bot" {
  name     = "pfirsichfest-bot"
  location = var.gcp_region

  template {
    service_account = google_service_account.bot_sa.email
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder until first build
      env {
        name  = "BUCKET_NAME"
        value = google_storage_bucket.archive_bucket.name
      }
    }
  }
}

# Allow unauthenticated invocation for the Webhook (Telegram will hit an obscure path or use secret token)
resource "google_cloud_run_service_iam_member" "public_invoker" {
  location = google_cloud_run_v2_service.bot.location
  project  = google_cloud_run_v2_service.bot.project
  service  = google_cloud_run_v2_service.bot.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
