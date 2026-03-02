provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "random" {}

# Generates a cryptographically secure random webhook secret used to verify
# that incoming webhook requests originate from Telegram.
resource "random_password" "webhook_secret" {
  length  = 32
  special = false
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

variable "authorized_user_id" {
  description = "Allowed Telegram User ID (Numeric)"
  type        = string
  sensitive   = true
}

variable "enable_vpn" {
  description = "Set to true to provision VPN secrets in Secret Manager"
  type        = bool
  default     = false
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

resource "google_secret_manager_secret" "authorized_user_id" {
  secret_id = "authorized-user-id"
  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "authorized_user_id_data" {
  secret      = google_secret_manager_secret.authorized_user_id.id
  secret_data = var.authorized_user_id
}

resource "google_secret_manager_secret" "webhook_secret_token" {
  secret_id = "webhook-secret-token"
  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "webhook_secret_token_data" {
  secret      = google_secret_manager_secret.webhook_secret_token.id
  secret_data = random_password.webhook_secret.result
}

resource "google_secret_manager_secret" "vpn_user" {
  count     = var.enable_vpn ? 1 : 0
  secret_id = "vpn-user"
  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }
}

resource "google_secret_manager_secret" "vpn_pass" {
  count     = var.enable_vpn ? 1 : 0
  secret_id = "vpn-pass"
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
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.bot_sa.email}"
}

# Downloader needs to delete its own Compute Engine instance
resource "google_project_iam_member" "downloader_compute_instance_admin" {
  project = var.gcp_project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.downloader_sa.email}"
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
