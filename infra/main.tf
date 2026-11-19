module "api" {
  source = "./modules/app"

  name               = var.app_name
  build_context      = "${path.root}/.."
  api_port           = var.api_port
  memory_mb          = var.memory_mb
  groq_api_key       = var.groq_api_key
  openrouter_api_key = var.openrouter_api_key
}
