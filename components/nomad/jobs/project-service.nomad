job "project-service" {
  datacenters = ["dc1"]
  type        = "service"

  group "project-service" {
    count = 1

    network {
      mode = "host"

      port "http" {
        static = 8001
      }
    }

    task "project-service" {
      driver = "docker"

      # Подключаем Vault
      vault {
        policies = ["nomad-workloads"]
      }

      config {
        image = "yffi41/project-service:latest"
        ports = ["http"]
        network_mode = "host"

        dns_servers = ["127.0.0.1", "8.8.8.8", "1.1.1.1"]
        dns_search_domains = ["service.consul"]
        extra_hosts = ["kafka.service.consul:127.0.0.1"]
      }

      env {
        KAFKA_ENABLED       = "true"
        KAFKA_BROKER        = "kafka.service.consul:9092"
        
      }

      # Секреты из Vault
      template {
        data = <<EOF
{{ with secret "secret/data/data/project-service" }}
JWT_SECRET={{ .Data.data.jwt_secret }}
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
        cpu    = 1000
        memory = 1024
      }

      # Регистрация в Consul
      service {
        name = "project-service"
        port = "http"

        tags = [
          "api",
          "projects"
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
