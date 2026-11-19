# everything one copy of the API needs: the image, a volume for its data, and the container

# built from our Dockerfile; rebuilt when the Dockerfile, requirements or code change
resource "docker_image" "api" {
  name         = "${var.name}:latest"
  keep_locally = true

  build {
    context = var.build_context
  }

  triggers = {
    code_hash = sha1(join("", [
      for file in sort(concat(
        ["Dockerfile", "requirements.txt", "config.py"],
        tolist(fileset(var.build_context, "src/**/*.py")),
        tolist(fileset(var.build_context, "api/**/*.py")),
      )) : filesha1("${var.build_context}/${file}")
    ]))
  }
}

# Qdrant, the answer cache and the reports live here, so they survive when the container is replaced
resource "docker_volume" "data" {
  name = "${var.name}-data"
}

resource "docker_container" "api" {
  name    = var.name
  image   = docker_image.api.image_id
  restart = "unless-stopped"
  memory  = var.memory_mb

  ports {
    internal = 8000
    external = var.api_port
  }

  # the keys are given when the container starts, they are never inside the image
  env = [
    "GROQ_API_KEY=${var.groq_api_key}",
    "OPENROUTER_API_KEY=${var.openrouter_api_key}",
  ]

  volumes {
    volume_name    = docker_volume.data.name
    container_path = "/app/data"
  }

  healthcheck {
    test         = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
    interval     = "30s"
    timeout      = "5s"
    start_period = "30s"
    retries      = 3
  }
}
