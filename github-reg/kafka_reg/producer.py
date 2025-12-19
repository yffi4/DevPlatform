import asyncio
import json
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
import os

load_dotenv()

class KafkaProducerService:
    def __init__(self, bootstrap_servers: str, username: str = None, password: str = None):
       
        if username and password:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                security_protocol="SASL_PLAINTEXT",
                sasl_mechanism="PLAIN",
                sasl_plain_username=username,
                sasl_plain_password=password
            )
        else:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers
            )

    async def start(self):
        await self._producer.start()

    async def stop(self):
        await self._producer.stop()

    async def send_event(self, topic: str, payload: dict):
        message = json.dumps(payload).encode("utf-8")
        await self._producer.send_and_wait(topic, message)

kafka_produser = KafkaProducerService(bootstrap_servers=os.getenv("KAFKA_BROKER"),
                                      username=os.getenv("KAFKA_USERNAME"),  # Из Vault через Nomad
                                      password=os.getenv("KAFKA_PASSWORD"))
