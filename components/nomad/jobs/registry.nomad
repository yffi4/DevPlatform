job "docker-registry" {
  datacenters = ["dc1"]
  type        = "service"

  group "registry" {
    count = 1

    network {
      mode = "host"

      port "http" {
        static = 5000
      }
    }

    task "registry" {
      driver = "docker"

      config {
        image = "registry:2"
        network_mode = "host"

        # Mount volume for persistent storage
        volumes = [
          "/var/lib/nomad/registry:/var/lib/registry"
        ]
      }

      resources {
        cpu    = 500
        memory = 512
      }

      service {
        name = "docker-registry"
        port = "http"

        tags = [
          "registry",
          "docker",
          "traefik.enable=true",
          "traefik.http.routers.registry.rule=Host(`registry.docker.localhost`)",
          "traefik.http.routers.registry.entrypoints=web",
          "traefik.http.services.registry.loadbalancer.server.port=5000",
        ]

        check {
          type     = "http"
          path     = "/v2/"
          port     = "http"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }

    # Ensure registry volume directory exists
    task "prepare-volume" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = false
      }

      config {
        image = "alpine:latest"
        command = "sh"
        args = ["-c", "mkdir -p /data && chmod 777 /data"]

        volumes = [
          "/var/lib/nomad/registry:/data"
        ]
      }

      resources {
        cpu    = 100
        memory = 64
      }
    }
  }
}
