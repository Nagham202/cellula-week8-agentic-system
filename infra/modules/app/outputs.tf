output "api_url" {
  value = "http://localhost:${var.api_port}"
}

output "docs_url" {
  value = "http://localhost:${var.api_port}/docs"
}

output "container_name" {
  value = docker_container.api.name
}

output "data_volume" {
  value = docker_volume.data.name
}
