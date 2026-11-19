# which Terraform and which providers (plugins) this project needs

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# talks to the Docker engine on this machine; Docker Desktop on a Mac uses ~/.docker/run/docker.sock
provider "docker" {
  host = "unix://${pathexpand(var.docker_socket)}"
}
