job "deployment-service" {
  datacenters = ["dc1"]
  type        = "service"

  group "deployment-service" {
    count = 1

    network {
      mode = "host"

      port "http" {
        static = 8003
      }
    }

    task "deployment-service" {
      driver = "docker"

      # Подключаем Vault
      vault {
        policies = ["nomad-workloads"]
      }

      config {
        image = "yffi41/deployment-service:latest"
        ports = ["http"]
        network_mode = "host"
        dns_servers = ["127.0.0.1", "8.8.8.8", "1.1.1.1"]
        dns_search_domains = ["service.consul"]
        extra_hosts = ["kafka.service.consul:127.0.0.1"]
      }

      env {
        KAFKA_ENABLED = "true"
        NOMAD_ADDR = "http://127.0.0.1:4646"
        SECRET_MANAGER_URL = "http://127.0.0.1:8002"
      }

      # Получаем секреты из Vault
      template {
        data = <<EOF
  {{ with secret "secret/data/data/deployment-service" }}
  FRONTEND_URL={{ .Data.data.FRONTEND_URL }}
  KAFKA_USERNAME={{ .Data.data.kafka_username }}
  KAFKA_PASSWORD={{ .Data.data.kafka_password }}
  KAFKA_BROKER={{ .Data.data.kafka_broker }}
  KAFKA_SASL_MECHANISM={{ .Data.data.kafka_sasl }}
  KAFKA_SECURITY_PROTOCOL={{ .Data.data.kafka_protocol }}
  NEXUS_URL={{ .Data.data.nexus_url }}
  NEXUS_USER={{ .Data.data.nexus_user }}
  NEXUS_PASSWORD={{ .Data.data.nexus_password }}
  SECRET_MANAGER_URL={{ .Data.data.secret_manager_url }}
  {{ end }}

  EOF

        destination = "secrets/app.env"
        env         = true
      }

      resources {
        cpu    = 500
        memory = 512
      }

      # Регистрация в Consul для DNS
      service {
        name = "deployment-service"
        port = "http"

        tags = [
          "api",
          "deployment"
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