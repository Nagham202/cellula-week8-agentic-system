# Infrastructure as Code (Terraform)

This folder describes the infrastructure the API needs, using Terraform and the
[Docker provider](https://registry.terraform.io/providers/kreuzwerker/docker/latest). The configuration is
checked with `terraform init`, `validate` and `plan`. **No cloud account is used and nothing is deployed.**

## Infrastructure design

```
                     terraform plan / apply
                              │
                              ▼
   ┌──────────────────── module "api" (modules/app) ────────────────────┐
   │                                                                    │
   │  docker_image.api        built from ../Dockerfile                  │
   │        │                 rebuilt when Dockerfile / requirements /   │
   │        │                 src/*.py / api/*.py change (hash trigger)  │
   │        ▼                                                           │
   │  docker_container.api ── port var.api_port → 8000                  │
   │        │                 env: GROQ_API_KEY, OPENROUTER_API_KEY      │
   │        │                      (sensitive variables, never in image) │
   │        │                 healthcheck: GET /health every 30 s        │
   │        │                 restart: unless-stopped, memory limit      │
   │        ▼                                                           │
   │  docker_volume.data ──── mounted at /app/data                      │
   │                          (Qdrant database, answer cache, reports)   │
   └────────────────────────────────────────────────────────────────────┘
```

| Need of the app | Terraform resource |
|---|---|
| The packaged app (Python 3.12, libraries, code, models) | `docker_image.api` |
| A running process reachable on a port, with a health check and restart policy | `docker_container.api` |
| Storage that survives when the container is replaced (local Qdrant needs a disk) | `docker_volume.data` |
| Secret API keys | sensitive variables passed as container environment variables |

**Why one container:** local Qdrant can only be opened by one process, so the API runs as one container
with one worker. Moving to a Qdrant server would allow several API containers. That would need a second container
resource in the module, and a small change in `src/pipeline/store.py` to connect by URL instead of a folder.

**Why the Docker provider:** `plan` (and `apply`, if wanted) runs against the local Docker engine with no cloud
account. The same design maps directly to a cloud: the image goes to a registry, the container becomes a
container service or VM, the volume becomes a disk, and the keys move to a secrets manager.

## Files

```
infra/
├── providers.tf              Terraform version, the Docker provider, and the Docker socket to use
├── variables.tf              inputs (see the table below)
├── main.tf                   calls the module once: one deployment of the API
├── outputs.tf                URLs and names printed after apply
├── terraform.tfvars.example  template for your values (copy to terraform.tfvars)
├── .terraform.lock.hcl       pins the provider version for everyone
├── results/                  saved outputs of fmt, init, validate and plan
└── modules/app/              everything one copy of the API needs
    ├── main.tf               docker_image, docker_volume, docker_container
    ├── variables.tf          module inputs
    ├── outputs.tf            module outputs
    └── versions.tf           provider source for the module
```

## Variables

| Name | Type | Default | Required | Description |
|---|---|---|---|---|
| `groq_api_key` | string, sensitive | none | **yes** | Groq API key (main LLM provider) |
| `openrouter_api_key` | string, sensitive | `""` | no | OpenRouter API key (backup provider) |
| `app_name` | string | `docs-chat-api` | no | Name of the container, image and volume |
| `api_port` | number | `8000` | no | Host port for the API (validated: 1024 to 65535) |
| `memory_mb` | number | `2048` | no | Container memory limit in MB |
| `docker_socket` | string | `~/.docker/run/docker.sock` | no | Docker engine socket (Linux: `/var/run/docker.sock`) |

## Outputs

| Name | Example |
|---|---|
| `api_url` | `http://localhost:8000` |
| `docs_url` | `http://localhost:8000/docs` |
| `container_name` | `docs-chat-api` |
| `data_volume` | `docs-chat-api-data` |

## How to initialize and validate

Requirements: Terraform 1.5 or newer, and Docker (Docker Desktop on macOS) running. The Docker provider
connects to the engine even for `plan`.

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # then put your keys in terraform.tfvars

terraform fmt -recursive    # format the files
terraform init              # download the Docker provider (version from .terraform.lock.hcl)
terraform validate          # check the configuration
terraform plan              # preview: should show "Plan: 3 to add, 0 to change, 0 to destroy"
```

To check the configuration without real keys:

```bash
TF_VAR_groq_api_key=placeholder terraform plan
```

## Secrets

- Key values live only in `terraform.tfvars`, which is git-ignored like `.env`.
- The key variables are `sensitive`, so they appear as `(sensitive value)` in every plan.
- `*.tfstate` files and saved plans are git-ignored, because Terraform state can contain secret values.
- The keys are never copied into the Docker image (`.dockerignore` excludes `.env`).

## Results (saved in `results/`)

| Command | Result |
|---|---|
| `terraform fmt -recursive -check` | exit 0, all files formatted |
| `terraform init` | installed `kreuzwerker/docker v3.9.0`, lock file created |
| `terraform validate` | `Success! The configuration is valid.` |
| `terraform plan` | `Plan: 3 to add, 0 to change, 0 to destroy`, keys shown as `(sensitive value)` |
| `plan -var api_port=9000 -var app_name=docs-chat-api-test` | all names, the port and `api_url` change |
| `plan -var api_port=80` | rejected: `api_port must be between 1024 and 65535.` |

## Applying (optional, local only)

`terraform apply` is **not** part of this task. With the Docker provider, it would only create a container on
the local machine, never in a cloud. If you try it, stop any local uvicorn or Streamlit first. The new data
volume starts empty, so upload documents through `POST /upload`. `terraform destroy` removes the container
**and the data volume, with everything stored in it**. The image stays on the machine (`keep_locally = true`).
