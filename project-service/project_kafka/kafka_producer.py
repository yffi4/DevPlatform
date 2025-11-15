import json
from aiokafka import AIOKafkaProducer
from typing import Dict


class KafkaProducerService:
    """
    Kafka producer for sending events to CI/CD pipeline service
    """

    def __init__(self, bootstrap_servers: str = "kafka:9092"):
        self.bootstrap_servers = bootstrap_servers
        self._producer = None

    async def start(self):
        """Start Kafka producer"""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self._producer.start()
        print(f"Kafka producer started: {self.bootstrap_servers}")

    async def stop(self):
        """Stop Kafka producer"""
        if self._producer:
            await self._producer.stop()
            print("Kafka producer stopped")

    async def send_framework_detected(self, data: Dict):
        """
        Send framework detection event to CI/CD pipeline service

        Args:
            data: Framework detection result
        """
        topic = "framework_detected"

        event = {
            "event_type": "framework_detected",
            "repo": data.get("repo"),
            "frameworks": data.get("frameworks", []),
            "primary_framework": data.get("primary_framework"),
            "language": data.get("language"),
            "has_dockerfile": data.get("has_dockerfile", False),
            "buildpack": data.get("buildpack"),
            "metadata": {
                "all_frameworks": data.get("frameworks", []),
            }
        }

        await self._producer.send_and_wait(topic, event)
        print(f"Sent event to topic '{topic}': {event}")

    async def send_deployment_request(self, repo_full_name: str, framework_data: Dict, user_id: str = None):
        """
        Send deployment request to CI/CD pipeline service

        Args:
            repo_full_name: Full repository name
            framework_data: Detected framework information
            user_id: Optional user identifier
        """
        topic = "deployment_requested"

        event = {
            "event_type": "deployment_requested",
            "repo": repo_full_name,
            "user_id": user_id,
            "framework": framework_data.get("primary_framework"),
            "language": framework_data.get("language"),
            "buildpack": framework_data.get("buildpack"),
            "has_dockerfile": framework_data.get("has_dockerfile"),
            "configuration": {
                "frameworks": framework_data.get("frameworks", []),
                "auto_deploy": True,
                "environment": "production"
            }
        }

        await self._producer.send_and_wait(topic, event)
        print(f"Sent deployment request to topic '{topic}': {event}")


# Global producer instance
kafka_producer = KafkaProducerService(bootstrap_servers="kafka:9092")
