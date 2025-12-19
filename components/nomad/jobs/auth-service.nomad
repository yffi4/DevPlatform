job "auth-service" {
  datacenters = ["dc1"]
  type        = "service"

  group "github-reg" {
    count = 1
    
    network {
      mode = "host"

      port "http" {
        static = 8000
      }
    }

    task "auth-service" {
      driver = "docker"

      vault {
        policies = ["nomad-workloads"]
      }

      config {
        image = "yffi41/github-reg-service:latest"
        ports = ["http"]
        network_mode = "host"

        dns_servers = ["127.0.0.1", "8.8.8.8", "1.1.1.1"]
        dns_search_domains = ["service.consul"]
        extra_hosts = ["kafka.service.consul:127.0.0.1"]

      }

      env {
        KAFKA_ENABLED = "true"
        PORT = "8000"
      }

      template {
        data = <<EOF
{{ with secret "secret/data/data/auth-service" }}
JWT_SECRET={{ .Data.data.jwt_secret }}
CLIENT_ID={{ .Data.data.CLIENT_ID }}
CLIENT_SECRET={{ .Data.data.CLIENT_SECRET }}
REDIRECTED_URI={{ .Data.data.redirect_uri }}
FRONTEND_URL={{ .Data.data.frontend_url }}
KAFKA_USERNAME={{ .Data.data.KAFKA_USERNAME }}
KAFKA_PASSWORD={{ .Data.data.KAFKA_PASSWORD }}
KAFKA_BROKER={{ .Data.data.KAFKA_BROKER }}
KAFKA_SASL_MECHANISM={{ .Data.data.KAFKA_SASL_MECHANISM }}
KAFKA_SECURITY_PROTOCOL={{ .Data.data.KAFKA_SECURITY_PROTOCOL }}
{{ end }}
EOF

        destination = "secrets/app.env"
        env         = true
      }

      resources {
        cpu    = 500
        memory = 512
      }

      service {
        name = "auth-service"
        port = "http"

        tags = [
          "traefik.enable=true",

          # router
          "traefik.http.routers.auth.rule=Host(`auth.localhost`)",
          "traefik.http.routers.auth.entrypoints=web",

          # service
          "traefik.http.services.auth.loadbalancer.server.port=8000"
        ]

        check {
          type     = "http"
          path     = "/docs"
          port     = "http"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }
  }
}
