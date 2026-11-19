variable "name" {
  description = "Name for the container, the image and the data volume"
  type        = string
}

variable "build_context" {
  description = "Folder that holds the Dockerfile (the project root)"
  type        = string
}

variable "api_port" {
  description = "Port on the host machine for the API"
  type        = number
}

variable "memory_mb" {
  description = "Memory limit for the container, in MB"
  type        = number
}

variable "groq_api_key" {
  description = "Groq API key"
  type        = string
  sensitive   = true
}

variable "openrouter_api_key" {
  description = "OpenRouter API key"
  type        = string
  sensitive   = true
}
