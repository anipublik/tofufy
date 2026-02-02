terraform {
  required_providers {
    aws = {
      source  = "registry.opentofu.org/hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "registry.opentofu.org/hashicorp/google"
      version = "~> 4.0"
    }
  }
}
