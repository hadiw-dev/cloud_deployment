terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "= 4.6.0"
    }
  }
}

provider "docker" {}

resource "docker_network" "frontend" {
  name     = "cloud-deployment-platform-terraform-frontend"
  driver   = "bridge"
  internal = false

  labels {
    label = "managed-by"
    value = "terraform"
  }

  labels {
    label = "project"
    value = "cloud-deployment-platform"
  }
}

output "frontend_network_name" {
  description = "Docker network Compose uses for the API's frontend connection."
  value       = docker_network.frontend.name
}
