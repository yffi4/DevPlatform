# Используем лёгкий базовый образ Python
FROM python:3.11-slim

# Устанавливаем системные зависимости для aiokafka и Kafka клиентской библиотеки
RUN apt-get update && apt-get install -y \
    librdkafka-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё приложение
COPY . .

# Добавляем переменные окружения для Kafka
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV PYTHONUNBUFFERED=1

# Добавляем ожидание Kafka перед стартом приложения (чтобы не падало при старте)

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]