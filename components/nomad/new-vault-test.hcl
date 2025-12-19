job "test-vault" {
  datacenters = ["dc1"]
  
  group "app" {
    task "test" {
      driver = "docker"
      
      # Подключаем Vault
      vault {
        policies = ["nomad-workloads"]
      }
      
      # Получаем секрет из Vault и выводим в лог
      template {
        data = <<EOT
{{ with secret "secret/data/data/test" }}
SECRET_FROM_VAULT={{ .Data.data.password }}
{{ end }}
EOT
        destination = "local/secret.txt"
        env = true
      }
      
      config {
        image = "alpine:latest"
        command = "sh"
        args = [
          "-c",
          "echo '=== Проверка секретов ===' && echo 'Секрет из переменной:' $SECRET_FROM_VAULT && echo 'Секрет из файла:' && cat local/secret.txt && echo '=== Ждём 5 минут ===' && sleep 300"
        ]
      }
      
      resources {
        cpu    = 100
        memory = 128
      }
    }
  }
}
