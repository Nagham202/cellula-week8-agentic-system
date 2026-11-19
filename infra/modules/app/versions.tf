# without this terraform looks for hashicorp/docker, which doesn't exist
terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}
