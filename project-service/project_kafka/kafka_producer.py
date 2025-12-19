import json
from aiokafka import AIOKafkaProducer
from typing import Dict
from dotenv import load_dotenv
import os

load_dotenv()

class KafkaProducerService:
    """
    Kafka producer for sending events to CI/CD pipeline service
    """

    def __init__(self, bootstrap_servers: str, username: str = None, password: str = None):

        if username and password:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                security_protocol="SASL_PLAINTEXT",
                sasl_mechanism="PLAIN",
                sasl_plain_username=username,
                sasl_plain_password=password
            )
        else:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )

    async def start(self):
        """Start Kafka producer"""
        await self._producer.start()
        

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
            "folder_path": framework_data.get("folder_path", ""),
            "configuration": {
                "frameworks": framework_data.get("frameworks", []),
                "auto_deploy": True,
                "environment": "production"
            }
        }

        await self._producer.send_and_wait(topic, event)
        print(f"Sent deployment request to topic '{topic}': {event}")

    async def send_project_framework_detected(self, repo_full_name: str, framework: str, language: str, user_id: str = None):
        """
        Send project framework detection event to Secret Manager service

        Args:
            repo_full_name: Full repository name (e.g., "owner/repo")
            framework: Detected framework
            language: Detected language
            user_id: Optional user identifier
        """
        topic = "project_framework_detected"

        event = {
            "event_type": "project_framework_detected",
            "project_id": repo_full_name,
            "framework": framework,
            "language": language,
            "user_id": user_id
        }

        await self._producer.send_and_wait(topic, event)
        print(f"Sent project framework detected to topic '{topic}': {event}")


# Global producer instance
kafka_producer = KafkaProducerService(bootstrap_servers=os.getenv("KAFKA_BROKER"),
                                      username=os.getenv("KAFKA_USERNAME"),  # Из Vault через Nomad
                                      password=os.getenv("KAFKA_PASSWORD"))
