terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "registry.opentofu.org/hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "remote" {
    hostname     = "app.terraform.io"
    organization = "my-org"
    workspaces {
      name   = "my-workspace"
    }
  }
}
