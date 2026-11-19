# settings that can change without editing the code; real values go in terraform.tfvars (git-ignored)

variable "docker_socket" {
  description = "Path to the Docker engine socket. Docker Desktop on macOS: ~/.docker/run/docker.sock, Linux: /var/run/docker.sock"
  type        = string
  default     = "~/.docker/run/docker.sock"
}

variable "app_name" {
  description = "Name used for the container, the image and the data volume"
  type        = string
  default     = "docs-chat-api"
}

variable "api_port" {
  description = "Port on this machine where the API will be reachable"
  type        = number
  default     = 8000

  validation {
    condition     = var.api_port >= 1024 && var.api_port <= 65535
    error_message = "api_port must be between 1024 and 65535."
  }
}

variable "memory_mb" {
  description = "Most memory the container may use, in MB (the embedding and reranker models need about 1 GB)"
  type        = number
  default     = 2048
}

variable "groq_api_key" {
  description = "Groq API key (main LLM provider)"
  type        = string
  sensitive   = true
}

variable "openrouter_api_key" {
  description = "OpenRouter API key (backup LLM provider); leave empty to use Groq only"
  type        = string
  sensitive   = true
  default     = ""
}
