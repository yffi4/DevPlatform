# Template for user-deployed applications
# Variables will be replaced by the deployment service:
# - {{APP_NAME}} - unique app name
# - {{USER_ID}} - user ID
# - {{REPO_NAME}} - repository name
# - {{DOCKER_IMAGE}} - built docker image
# - {{PORT}} - application port
# - {{DOMAIN}} - custom domain or subdomain

job "{{APP_NAME}}" {
  datacenters = ["dc1"]
  type        = "service"

  meta {
    user_id    = "{{USER_ID}}"
    repo_name  = "{{REPO_NAME}}"
    app_type   = "user-application"
  }

  group "app" {
    count = 1

    network {
      mode = "bridge"

      port "http" {
        to = {{PORT}}
      }
    }

    task "app" {
      driver = "docker"

      config {
        image = "{{DOCKER_IMAGE}}"
        ports = ["http"]
      }

      # User's environment variables from Vault
      template {
        data = <<EOF
{{ENVIRONMENT_VARIABLES}}
EOF

        destination = "secrets/app.env"
        env         = true
      }

      resources {
        cpu    = 500
        memory = 512
      }

      service {
        name = "{{APP_NAME}}"
        port = "http"

        tags = [
          "user-app",
          "user-{{USER_ID}}",
          "traefik.enable=true",
          "traefik.http.routers.{{APP_NAME}}.rule=Host(`{{DOMAIN}}`)",
          "traefik.http.routers.{{APP_NAME}}.entrypoints=web",
          "traefik.http.services.{{APP_NAME}}.loadbalancer.server.port={{PORT}}",
        ]

        meta {
          user_id   = "{{USER_ID}}"
          repo_name = "{{REPO_NAME}}"
        }

        check {
          type     = "tcp"
          port     = "http"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }

    # Enable auto-scaling based on CPU usage
    scaling {
      enabled = true
      min     = 1
      max     = 5

      policy {
        cooldown            = "1m"
        evaluation_interval = "10s"

        check "cpu_usage" {
          source = "prometheus"
          query  = "avg(cpu_usage)"

          strategy "target-value" {
            target = 70
          }
        }
      }
    }
  }
}
