import asyncio
import json
from aiokafka import AIOKafkaProducer

class KafkaProducerService:
    def __init__(self, bootstrap_servers: str):
        self._producer = AIOKafkaProducer(bootstrap_servers="kafka:9092")

    async def start(self):
        await self._producer.start()

    async def stop(self):
        await self._producer.stop()

    async def send_event(self, topic: str, payload: dict):
        message = json.dumps(payload).encode("utf-8")
        await self._producer.send_and_wait(topic, message)

kafka_produser = KafkaProducerService(bootstrap_servers="kafka:9092")
