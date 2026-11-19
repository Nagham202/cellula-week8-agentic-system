output "api_url" {
  description = "Base URL of the API"
  value       = module.api.api_url
}

output "docs_url" {
  description = "Interactive API documentation (Swagger UI)"
  value       = module.api.docs_url
}

output "container_name" {
  description = "Name of the running container (for docker logs / docker stop)"
  value       = module.api.container_name
}

output "data_volume" {
  description = "Docker volume that keeps the Qdrant database, the answer cache and reports"
  value       = module.api.data_volume
}
