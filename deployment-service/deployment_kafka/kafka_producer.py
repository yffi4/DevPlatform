import json
from aiokafka import AIOKafkaProducer
from typing import Dict, Optional
import os
from dotenv import load_dotenv
load_dotenv()

class KafkaProducerService:
    """
    Kafka producer for sending deployment events
    """

    def __init__(self, bootstrap_servers: str = "kafka.service.consul:9092", username: str = "", password: str = "", sasl_mechanism: str = "PLAIN", security_protocol: str = "SASL_PLAINTEXT"):
        self.bootstrap_servers = bootstrap_servers
        self.username = username
        self.password = password
        self.sasl_mechanism = sasl_mechanism
        self.security_protocol = security_protocol
        self._producer = None

    async def start(self):
        """Start Kafka producer"""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.loads(v).encode('utf-8') if isinstance(v, str) else json.dumps(v).encode('utf-8'),
            sasl_mechanism=self.sasl_mechanism,
            security_protocol=self.security_protocol,
            sasl_plain_username=self.username,
            sasl_plain_password=self.password
        )
        await self._producer.start()
        print(f"✓ Deployment Service Kafka producer started: {self.bootstrap_servers}")

    async def stop(self):
        """Stop Kafka producer"""
        if self._producer:
            await self._producer.stop()
            print("✓ Deployment Service Kafka producer stopped")

    async def send_deployment_started(
        self,
        app_name: str,
        repo_full_name: str,
        user_id: str,
        framework: Optional[str] = None
    ):
        """
        Send deployment started event
        """
        topic = "deployment_started"

        event = {
            "event_type": "deployment_started",
            "app_name": app_name,
            "repo": repo_full_name,
            "user_id": user_id,
            "framework": framework,
            "status": "building"
        }

        try:
            await self._producer.send_and_wait(topic, event)
            print(f"📤 Sent event to topic '{topic}': {app_name}")
        except Exception as e:
            print(f"⚠️ Failed to send event to topic '{topic}': {e}")

    async def send_deployment_completed(
        self,
        app_name: str,
        repo_full_name: str,
        user_id: str,
        domain: str,
        framework: Optional[str] = None
    ):
        """
        Send deployment completed event
        """
        topic = "deployment_completed"

        event = {
            "event_type": "deployment_completed",
            "app_name": app_name,
            "repo": repo_full_name,
            "user_id": user_id,
            "framework": framework,
            "domain": domain,
            "url": f"http://{domain}",
            "status": "running"
        }

        try:
            await self._producer.send_and_wait(topic, event)
            print(f"✓ Sent event to topic '{topic}': {app_name} -> {domain}")
        except Exception as e:
            print(f"⚠️ Failed to send event to topic '{topic}': {e}")

    async def send_deployment_failed(
        self,
        app_name: str,
        repo_full_name: str,
        user_id: str,
        error: str,
        framework: Optional[str] = None
    ):
        """
        Send deployment failed event
        """
        topic = "deployment_failed"

        event = {
            "event_type": "deployment_failed",
            "app_name": app_name,
            "repo": repo_full_name,
            "user_id": user_id,
            "framework": framework,
            "error": error,
            "status": "failed"
        }

        try:
            await self._producer.send_and_wait(topic, event)
            print(f"❌ Sent event to topic '{topic}': {app_name} - {error}")
        except Exception as e:
            print(f"⚠️ Failed to send event to topic '{topic}': {e}")

    async def request_secrets(self, project_id: str, user_id: str):
        """
        Request secrets from secret manager service
        """
        topic = "secrets_requested"

        event = {
            "event_type": "secrets_requested",
            "project_id": project_id,
            "user_id": user_id,
            "requested_by": "deployment-service"
        }

        try:
            await self._producer.send_and_wait(topic, event)
            print(f"🔐 Requested secrets for project: {project_id}")
        except Exception as e:
            print(f"⚠️ Failed to send event to topic '{topic}': {e}")


# Global producer instance
kafka_producer = KafkaProducerService(bootstrap_servers=os.getenv("KAFKA_BROKER"), 
    username=os.getenv("KAFKA_USERNAME"),
    password=os.getenv("KAFKA_PASSWORD"),
    sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM", "PLAIN"),
    security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL", "SASL_PLAINTEXT"))
