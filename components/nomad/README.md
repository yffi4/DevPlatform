# Nomad + Consul + Traefik Setup

Эта конфигурация настраивает оркестрацию контейнеров с использованием Nomad, service discovery через Consul и автоматический reverse proxy через Traefik.

## Архитектура

```
┌─────────────┐
│   Traefik   │ ◄── HTTP requests from users
│  (Port 80)  │
└──────┬──────┘
       │
       │ Queries services
       ▼
┌─────────────┐
│   Consul    │ ◄── Service registry
│  (Port 8500)│
└──────┬──────┘
       │
       │ Registers services
       ▼
┌─────────────┐
│    Nomad    │ ◄── Orchestrates containers
│  (Port 4646)│
└──────┬──────┘
       │
       │ Deploys
       ▼
┌─────────────────────────────────┐
│  User Applications & Services   │
└─────────────────────────────────┘
```

## Компоненты

### 1. Consul (Service Discovery)
- **UI**: http://localhost:8500
- Автоматически регистрирует все сервисы из Nomad
- Хранит конфигурацию в KV store
- Обеспечивает health checking

### 2. Nomad (Orchestration)
- **UI**: http://localhost:4646
- Запускает и управляет контейнерами
- Автоматически регистрирует сервисы в Consul
- Поддерживает auto-scaling

### 3. Traefik (Reverse Proxy)
- **Dashboard**: http://localhost:8081
- **HTTP**: http://localhost:80
- Автоматически получает маршруты из Consul
- Динамически обновляет конфигурацию при изменении сервисов

## Быстрый старт

### 1. Запуск инфраструктуры

```bash
# Из корня проекта
cd /home/yffi/study/devops-final

# Запустить Consul, Nomad и Traefik
docker-compose -f docker-compose-infrastructure.yml up -d

# Проверить статус
docker-compose -f docker-compose-infrastructure.yml ps
```

### 2. Инициализация Consul

```bash
# Загрузить переменные окружения
source .env

# Инициализировать конфигурацию в Consul
cd nomad
./init-consul.sh
```

### 3. Сборка образов сервисов

```bash
# Вернуться в корень
cd ..

# Собрать образы
docker build -t github-reg-service:latest ./github-reg
docker build -t project-service:latest ./project-service
docker build -t secret-manager:latest ./secret_manager_service
```

### 4. Деплой сервисов через Nomad

```bash
cd nomad

# Развернуть все сервисы
./deploy-jobs.sh

# Или развернуть конкретный сервис
nomad job run jobs/auth-service.nomad
nomad job run jobs/project-service.nomad
nomad job run jobs/secret-manager.nomad
```

## Проверка работы

### Доступ к UI

- **Consul UI**: http://localhost:8500/ui
- **Nomad UI**: http://localhost:4646/ui
- **Traefik Dashboard**: http://localhost:8081/dashboard/

### Проверка сервисов

```bash
# Список всех сервисов в Consul
curl http://localhost:8500/v1/catalog/services | jq

# Список всех Nomad jobs
nomad job status

# Проверка здоровья сервиса
curl http://localhost:8500/v1/health/service/auth-service | jq
```

### Доступ к API

После деплоя сервисы будут доступны через Traefik:

- **Auth API**: http://api.localhost/auth
- **Project API**: http://api.localhost/projects
- **Secret Manager API**: http://api.localhost/secrets

**Примечание**: Для работы с `*.localhost` доменами в Linux может потребоваться добавить их в `/etc/hosts`:

```bash
echo "127.0.0.1 api.localhost kafka-ui.localhost" | sudo tee -a /etc/hosts
```

## Деплой пользовательских приложений

### Через API

```bash
# Деплой приложения
curl -X POST http://api.localhost/projects/api/deploy \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_JWT_TOKEN" \
  -d '{
    "repo_full_name": "user/repo",
    "app_name": "my-app",
    "docker_image": "my-app:latest",
    "port": 3000,
    "domain": "my-app.localhost",
    "env_vars": {
      "NODE_ENV": "production"
    }
  }'

# Список деплоев пользователя
curl http://api.localhost/projects/api/deployments \
  -H "Cookie: session=YOUR_JWT_TOKEN"

# Логи приложения
curl http://api.localhost/projects/api/deployments/user123-my-app/logs \
  -H "Cookie: session=YOUR_JWT_TOKEN"

# Удалить деплой
curl -X DELETE http://api.localhost/projects/api/deployments/user123-my-app \
  -H "Cookie: session=YOUR_JWT_TOKEN"
```

### Вручную через Nomad

```bash
# Использовать шаблон
cp jobs/user-app-template.nomad jobs/my-app.nomad

# Отредактировать переменные
vim jobs/my-app.nomad

# Деплой
nomad job run jobs/my-app.nomad
```

## Автоматическая регистрация в Consul и Traefik

Когда Nomad запускает сервис, он автоматически:

1. **Регистрирует сервис в Consul** с указанными тегами
2. **Consul уведомляет Traefik** о новом сервисе
3. **Traefik создает маршрут** на основе тегов `traefik.*`

Пример тегов для автоматической маршрутизации:

```hcl
tags = [
  "traefik.enable=true",
  "traefik.http.routers.myapp.rule=Host(`myapp.localhost`)",
  "traefik.http.routers.myapp.entrypoints=web",
]
```

## Мониторинг и отладка

### Логи Nomad job

```bash
# Статус job
nomad job status auth-service

# Логи конкретной аллокации
nomad alloc logs <allocation-id>

# Статус аллокации
nomad alloc status <allocation-id>
```

### Проверка регистрации в Consul

```bash
# Все сервисы
consul catalog services

# Детали сервиса
consul catalog nodes -service=auth-service

# Health check
consul watch -type=service -service=auth-service
```

### Traefik маршруты

```bash
# Все маршруты
curl http://localhost:8081/api/http/routers | jq

# Все сервисы
curl http://localhost:8081/api/http/services | jq
```

## Управление

### Остановка сервиса

```bash
# Остановить Nomad job
nomad job stop auth-service

# Полностью удалить job
nomad job stop -purge auth-service
```

### Обновление сервиса

```bash
# Отредактировать job файл
vim jobs/auth-service.nomad

# Применить изменения
nomad job run jobs/auth-service.nomad

# Nomad выполнит rolling update
```

### Масштабирование

```bash
# Масштабировать вручную (изменить count в job файле)
nomad job run jobs/my-app.nomad

# Или через API
nomad job scale auth-service 3
```

## Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# Database
ASYNC_DATABASE_URL=postgresql://user:pass@db:5432/devops

# JWT
JWT_SECRET=your-secret-key

# GitHub OAuth
CLIENT_ID=your-github-client-id
CLIENT_SECRET=your-github-client-secret
REDIRECTED_URI=http://localhost:8000/auth/github/callback

# Frontend
FRONTEND_URL=http://localhost:3000

# Vault
VAULT_TOKEN=root

# Consul & Nomad
CONSUL_ADDR=http://localhost:8500
NOMAD_ADDR=http://localhost:4646
```

## Troubleshooting

### Сервисы не регистрируются в Consul

```bash
# Проверить связь Nomad с Consul
nomad server members
nomad node status

# Проверить логи Nomad
docker logs nomad
```

### Traefik не создает маршруты

```bash
# Проверить, что Consul catalog provider работает
docker logs traefik

# Проверить теги сервиса в Consul
curl http://localhost:8500/v1/catalog/service/auth-service | jq '.[].ServiceTags'
```

### Контейнер не запускается

```bash
# Проверить статус аллокации
nomad job status <job-name>

# Посмотреть логи
nomad alloc logs -stderr <alloc-id>

# Проверить events
nomad alloc status <alloc-id>
```

## Полезные команды

```bash
# Перезапустить инфраструктуру
docker-compose -f docker-compose-infrastructure.yml restart

# Очистить всё и начать заново
nomad job stop -purge -yes $(nomad job status -short | tail -n +2 | awk '{print $1}')
docker-compose -f docker-compose-infrastructure.yml down -v
docker-compose -f docker-compose-infrastructure.yml up -d

# Экспорт job в JSON
nomad job inspect auth-service > auth-service.json

# Валидация job файла
nomad job validate jobs/auth-service.nomad
```

## Дополнительные ресурсы

- [Nomad Documentation](https://www.nomadproject.io/docs)
- [Consul Documentation](https://www.consul.io/docs)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
