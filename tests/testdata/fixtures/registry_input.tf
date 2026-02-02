terraform {
  required_providers {
    aws = {
      source  = "registry.terraform.io/hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "registry.terraform.io/hashicorp/google"
      version = "~> 4.0"
    }
  }
}
