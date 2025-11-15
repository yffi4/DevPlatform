FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    librdkafka-dev \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV PYTHONUNBUFFERED=1

CMD bash -c "echo '⏳ Waiting for Kafka...' && \
    while ! nc -z kafka 9092; do sleep 1; done && \
    echo '✅ Kafka is up!' && \
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload"
