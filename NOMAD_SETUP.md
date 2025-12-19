# 🚀 Nomad + Consul + Traefik - Полное руководство

## Что мы настроили

Ваша платформа теперь использует современный стек для оркестрации и service discovery:

### 🎯 Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      Internet / Users                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   Traefik    │  Reverse Proxy
                  │   :80, :443  │  (Auto-routing)
                  └──────┬───────┘
                         │
                         │ Discovers services
                         ▼
                  ┌──────────────┐
                  │    Consul    │  Service Discovery
                  │    :8500     │  (Service Registry + KV Store)
                  └──────┬───────┘
                         │
                         │ Services register here
                         ▼
                  ┌──────────────┐
                  │    Nomad     │  Container Orchestration
                  │    :4646     │  (Schedules & runs containers)
                  └──────┬───────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   ┌─────────┐    ┌─────────┐    ┌─────────────┐
   │  Auth   │    │ Project │    │   Secret    │
   │ Service │    │ Service │    │  Manager    │
   └─────────┘    └─────────┘    └─────────────┘
                         │
                         │ Deploys user apps
                         ▼
        ┌────────────────┴────────────────┐
        ▼                                  ▼
   ┌─────────┐                      ┌─────────┐
   │ User    │                      │ User    │
   │ App #1  │  ...                 │ App #N  │
   └─────────┘                      └─────────┘
```

### 📦 Компоненты

1. **Consul** - Service Discovery & Configuration
   - Автоматически регистрирует все сервисы
   - Хранит конфигурацию (секреты, настройки)
   - Health checking
   - DNS для внутренних сервисов

2. **Nomad** - Container Orchestration
   - Запускает и управляет контейнерами
   - Auto-scaling
   - Health checks & restarts
   - Rolling updates

3. **Traefik** - Reverse Proxy
   - Автоматически создает маршруты из Consul
   - Load balancing
   - Автоматические SSL сертификаты (опционально)
   - Metrics & monitoring

## 🚀 Быстрый старт

### 1. Запуск всей системы одной командой

```bash
make setup
```

Эта команда:
- ✅ Запустит Consul, Nomad, Traefik
- ✅ Инициализирует конфигурацию в Consul
- ✅ Соберет все Docker образы
- ✅ Задеплоит все сервисы

### 2. Или пошагово

```bash
# Шаг 1: Запустить инфраструктуру
make infrastructure

# Шаг 2: Настроить Consul
make init-consul

# Шаг 3: Собрать образы
make build

# Шаг 4: Задеплоить сервисы
make deploy-services
```

### 3. Проверка

```bash
# Посмотреть статус всех сервисов
make status

# Открыть все UI в браузере
make ui
```

## 🎮 Основные команды

```bash
# Посмотреть все доступные команды
make help

# Посмотреть статус
make status

# Посмотреть логи
make logs

# Остановить всё
make stop

# Полностью очистить
make clean
```

## 🌐 Доступ к интерфейсам

После запуска доступны:

- **Consul UI**: http://localhost:8500
  - Все зарегистрированные сервисы
  - Health статус
  - KV store

- **Nomad UI**: http://localhost:4646
  - Все jobs и allocations
  - Логи контейнеров
  - Ресурсы

- **Traefik Dashboard**: http://localhost:8081
  - Активные роуты
  - Бэкенды
  - Метрики

## 🔧 Как это работает

### Деплой пользовательского приложения

Когда пользователь через ваш сервис деплоит свое приложение:

#### 1. Пользователь делает запрос

```bash
curl -X POST http://api.localhost/projects/api/deploy \
  -H "Content-Type: application/json" \
  -H "Cookie: session=JWT_TOKEN" \
  -d '{
    "repo_full_name": "username/my-app",
    "app_name": "my-awesome-app",
    "docker_image": "my-awesome-app:v1.0",
    "port": 3000,
    "domain": "my-app.example.com"
  }'
```

#### 2. Project Service создает Nomad Job

```python
# В project-service/deployment_router.py
deployment_result = await nomad_client.deploy_user_app(
    app_name="user123-my-awesome-app",
    user_id="123",
    repo_name="username/my-app",
    docker_image="my-awesome-app:v1.0",
    port=3000,
    domain="my-app.example.com"
)
```

#### 3. Nomad запускает контейнер

Nomad:
- Скачивает образ
- Запускает контейнер
- Выделяет ресурсы (CPU, RAM)
- Пробрасывает порты

#### 4. Автоматическая регистрация в Consul

Nomad автоматически регистрирует сервис в Consul с тегами:

```hcl
tags = [
  "traefik.enable=true",
  "traefik.http.routers.my-app.rule=Host(`my-app.example.com`)",
  "traefik.http.routers.my-app.entrypoints=web"
]
```

#### 5. Traefik получает уведомление

Traefik:
- Подписан на изменения в Consul
- Видит новый сервис с тегами `traefik.*`
- Автоматически создает маршрут
- Начинает проксировать трафик

#### 6. Приложение доступно!

Теперь приложение доступно по адресу: `http://my-app.example.com`

### Диаграмма потока

```
User → POST /deploy → Project Service
                           ↓
                    Nomad Client
                           ↓
                     Create Job
                           ↓
                    Nomad Scheduler
                           ↓
                  Start Container
                           ↓
                   Register in Consul
                           ↓
                  Traefik detects change
                           ↓
                   Create route
                           ↓
              App is live! 🎉
```

## 📊 Управление деплоями через API

### Список всех деплоев пользователя

```bash
curl http://api.localhost/projects/api/deployments \
  -H "Cookie: session=JWT_TOKEN"
```

Ответ:
```json
{
  "user_id": "123",
  "deployments": [
    {
      "app_name": "user123-my-app",
      "domain": "my-app.example.com",
      "instances": 1,
      "healthy_instances": 1,
      "tags": ["user-app", "user-123", "traefik.enable=true", ...]
    }
  ],
  "total": 1
}
```

### Информация о конкретном деплое

```bash
curl http://api.localhost/projects/api/deployments/user123-my-app \
  -H "Cookie: session=JWT_TOKEN"
```

### Логи приложения

```bash
curl http://api.localhost/projects/api/deployments/user123-my-app/logs \
  -H "Cookie: session=JWT_TOKEN"
```

### Удаление деплоя

```bash
curl -X DELETE http://api.localhost/projects/api/deployments/user123-my-app \
  -H "Cookie: session=JWT_TOKEN"
```

## 🔍 Мониторинг и отладка

### Через Nomad UI

1. Открыть http://localhost:4646
2. Jobs → Выбрать job → View allocations
3. Allocation → Logs → stdout/stderr

### Через CLI

```bash
# Список всех jobs
nomad job status

# Статус конкретного job
nomad job status user123-my-app

# Логи последнего allocation
nomad job status user123-my-app | grep -A1 "Allocations" | tail -1 | awk '{print $1}' | xargs nomad alloc logs

# Или через наш Makefile
make logs-project
```

### Через Consul

```bash
# Все сервисы пользователя
curl http://localhost:8500/v1/catalog/services | jq

# Health check сервиса
curl http://localhost:8500/v1/health/service/user123-my-app | jq
```

## 🛠️ Интеграция в ваш код

### В project-service уже добавлено:

1. **nomad_client.py** - клиент для работы с Nomad API
   - Создание jobs
   - Управление деплоями
   - Получение логов

2. **consul_client.py** - клиент для работы с Consul API
   - Регистрация сервисов
   - Получение списка сервисов пользователя
   - KV store

3. **deployment_router.py** - API endpoints для деплоя
   - `POST /api/deploy` - задеплоить приложение
   - `GET /api/deployments` - список деплоев
   - `GET /api/deployments/{name}` - детали деплоя
   - `DELETE /api/deployments/{name}` - удалить деплой
   - `GET /api/deployments/{name}/logs` - логи

### Пример использования в коде

```python
from nomad_client import nomad_client
from consul_client import consul_client

# Деплой приложения
result = await nomad_client.deploy_user_app(
    app_name=f"user{user_id}-{app_name}",
    user_id=user_id,
    repo_name=repo_full_name,
    docker_image=docker_image,
    port=8080,
    domain=f"{app_name}.yourdomain.com",
    env_vars={
        "DATABASE_URL": "postgres://...",
        "API_KEY": "secret"
    },
    cpu=500,
    memory=512
)

# Получить все сервисы пользователя из Consul
services = await consul_client.get_user_services(user_id)

# Получить адрес сервиса
address = await consul_client.get_service_address("my-service")
# Returns: "http://10.0.1.5:8080"
```

## 🔐 Секреты и конфигурация

Секреты хранятся в Consul KV:

```bash
# Добавить секрет
curl -X PUT http://localhost:8500/v1/kv/config/my-app/api-key \
  -d "secret-value"

# Получить секрет
curl http://localhost:8500/v1/kv/config/my-app/api-key?raw
```

В Nomad job файлах используйте templates:

```hcl
template {
  data = <<EOF
API_KEY="{{ key "config/my-app/api-key" }}"
DATABASE_URL="{{ key "config/my-app/database-url" }}"
EOF
  destination = "secrets/app.env"
  env         = true
}
```

## 🎯 Production готовность

Для production окружения рекомендуется:

### 1. Multi-node Consul кластер

```bash
# Вместо dev mode, запустите 3+ сервера
consul agent -server -bootstrap-expect=3 ...
```

### 2. Multi-node Nomad кластер

```bash
# Отдельные server и client ноды
nomad agent -server ...
nomad agent -client ...
```

### 3. HTTPS в Traefik

Добавить в `docker-compose-infrastructure.yml`:

```yaml
command:
  - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
  - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
  - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
```

### 4. ACL в Consul

```bash
consul acl bootstrap
# Создать токены для сервисов
```

### 5. Мониторинг

Добавить:
- Prometheus для метрик
- Grafana для дашбордов
- Alertmanager для алертов

## 📚 Полезные ресурсы

- [Nomad Docs](https://www.nomadproject.io/docs)
- [Consul Docs](https://www.consul.io/docs)
- [Traefik Docs](https://doc.traefik.io/traefik/)
- [Подробный README](./nomad/README.md)

## 🆘 Troubleshooting

### Проблема: Сервис не регистрируется в Consul

**Решение:**
```bash
# Проверить связь Nomad с Consul
nomad server members

# Проверить логи
docker logs nomad
```

### Проблема: Traefik не создает маршруты

**Решение:**
```bash
# Проверить теги в Consul
curl http://localhost:8500/v1/catalog/service/my-service | jq '.[].ServiceTags'

# Убедиться что есть: traefik.enable=true
```

### Проблема: Контейнер не запускается

**Решение:**
```bash
# Проверить аллокацию
nomad job status my-job

# Посмотреть логи
nomad alloc logs -stderr <alloc-id>
```

## 🎉 Готово!

Теперь у вас есть полностью настроенная платформа для деплоя пользовательских приложений с:

✅ Автоматической оркестрацией (Nomad)
✅ Service discovery (Consul)
✅ Автоматическим routing (Traefik)
✅ API для управления деплоями
✅ Мониторингом и логами

Когда пользователи будут деплоить свои приложения через ваш сервис, они автоматически:
- Запустятся в Nomad
- Зарегистрируются в Consul
- Станут доступны через Traefik по заданному домену

Все это происходит автоматически! 🚀
