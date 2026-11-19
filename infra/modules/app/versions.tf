# every module must say where its providers come from, or Terraform guesses hashicorp/docker (which doesn't exist)

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}
