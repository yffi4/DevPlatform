job "secret-manager" {
  datacenters = ["dc1"]
  type        = "service"

  group "secret-manager" {
    count = 1

    network {
      mode = "host"

      port "http" {
        static = 8002
      }
    }

    task "secret-manager" {
      driver = "docker"

      # Подключаем Vault
      vault {
        policies = ["nomad-workloads"]
      }

      config {
        image = "yffi41/secret_manager.service:latest"
        ports = ["http"]
        network_mode = "host"
        dns_servers = ["127.0.0.1", "8.8.8.8", "1.1.1.1"]
        dns_search_domains = ["service.consul"]
        extra_hosts = ["kafka.service.consul:127.0.0.1"]
      }

      

      # Получаем секреты из Vault
      template {
        data = <<EOF
{{ with secret "secret/data/data/secret_manager" }}
KAFKA_USERNAME={{ .Data.data.KAFKA_USERNAME }}
KAFKA_PASSWORD={{ .Data.data.KAFKA_PASSWORD }}
KAFKA_BROKER={{ .Data.data.KAFKA_BROKER }}
KAFKA_SASL_MECHANISM={{ .Data.data.KAFKA_SASL_MECHANISM }}
KAFKA_SECURITY_PROTOCOL={{ .Data.data.KAFKA_SECURITY_PROTOCOL }}
VAULT_ADDR={{ .Data.data.VAULT_ADDR }}
VAULT_TOKEN={{ .Data.data.VAULT_TOKEN }}
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
        name = "secret-manager"
        port = "http"

        

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