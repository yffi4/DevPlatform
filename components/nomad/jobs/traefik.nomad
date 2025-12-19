job "traefik" {
  datacenters = ["dc1"]
  type        = "system"  # Или "service" если нужен только на одной ноде

  group "traefik" {
    count = 1

    network {
      port "http" {
        static = 80
      }
      port "https" {
        static = 443
      }
      port "api" {
        static = 8080
      }
    }

    task "traefik" {
      driver = "docker"

      config {
        image = "traefik:v2.11"
        
        ports = ["http", "https", "api"]
        
        network_mode = "host"
        args = [
          "--api.dashboard=true",
          "--api.insecure=true",
          "--ping=true",
          "--entrypoints.web.address=:80",
          "--entrypoints.websecure.address=:443",
          "--entrypoints.traefik.address=:8080",
          "--providers.consulcatalog=true",
          "--providers.consulcatalog.endpoint.address=127.0.0.1:8500",
          "--providers.consulcatalog.exposedByDefault=false",
        ]

        # Доступ к Docker socket (если нужен Docker provider)
        # volumes = [
        #   "/var/run/docker.sock:/var/run/docker.sock"
        # ]
      }

      resources {
        cpu    = 500
        memory = 256
      }

      service {
        name = "traefik"
        port = "http"

        tags = [
          "traefik",
          "http",
        ]

        check {
          type     = "http"
          path     = "/ping"
          port     = "api"
          interval = "10s"
          timeout  = "2s"
        }
      }

      service {
        name = "traefik-api"
        port = "api"
        
        tags = [
          "traefik.enable=true",
          "traefik.http.routers.dashboard.rule=Host(`traefik.localhost`)",
        ]
      }
    }
  }
}