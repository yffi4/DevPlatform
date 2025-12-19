import json
import asyncio
from aiokafka import AIOKafkaConsumer
from typing import Dict
from framework_detector.framework_detector import FrameworkDetector
from .kafka_producer import kafka_producer
import os 
from dotenv import load_dotenv

load_dotenv()

class KafkaConsumerService:
    """
    Kafka consumer for listening to deployment requests from auth-service
    """

    def __init__(self, bootstrap_servers: str, username: str = None, password: str = None):
        self.bootstrap_servers = bootstrap_servers
        self.username = username
        self.password = password
        self._consumer = None
        self._running = False

    async def start(self):
        """Start Kafka consumer"""
        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "value_deserializer": lambda m: json.loads(m.decode('utf-8')),
            "group_id": "project-service-group",
            "auto_offset_reset": 'latest'
        }

        # Используем SASL только если указаны username и password (для Nomad/Consul)
        # Иначе используем PLAINTEXT (для Docker Compose)
        if self.username and self.password:
            config.update({
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": self.username,
                "sasl_plain_password": self.password,
            })

        self._consumer = AIOKafkaConsumer(
            "user_registered",
            "repos_resp",
            **config
        )
        await self._consumer.start()
        print(f"Kafka consumer started, listening to 'user_registered' and 'repos_resp' topics")

        self._running = True
        asyncio.create_task(self._consume_messages())

    async def stop(self):
        """Stop Kafka consumer"""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            print("Kafka consumer stopped")

    async def _consume_messages(self):
        """Consume messages from Kafka topic"""
        try:
            async for message in self._consumer:
                if not self._running:
                    break

                try:
                    data = message.value
                    print(f"Received message from Kafka: {data}")

                    # Process the deployment request
                    await self._process_deployment_request(data)

                except Exception as e:
                    print(f"Error processing message: {e}")

        except Exception as e:
            print(f"Error in consumer loop: {e}")

    async def _process_deployment_request(self, data: Dict):
        """
        Process deployment request from auth-service

        Expected data structure:
        {
            "user": {"id": 123, "login": "username"},
            "repository": {
                "owner": "username",
                "name": "repo-name",
                "full_name": "username/repo-name",
                "folder_path": "path/to/folder"
            },
            "github_token": "ghp_..."
        }
        """
        try:

            user = data.get("user", {})
            repository = data.get("repository", {})
            github_token = data.get("github_token")

            repo_full_name = repository.get("full_name")
            folder_path = repository.get("folder_path", "")

            if not github_token or not repo_full_name:
                print(f"Missing required data: github_token={bool(github_token)}, repo={repo_full_name}")
                return

            print(f"Processing deployment for {repo_full_name}, folder: {folder_path or '/'}")


            detector = FrameworkDetector(github_token)

            framework_data = await detector.detect_framework(
                project_id=repo_full_name,
                repo_full_name=repo_full_name,
                folder_path=folder_path
            )

            print(f"Framework detected: {framework_data}")

            await kafka_producer.send_framework_detected({
                **framework_data,
                "user": user,
                "folder_path": folder_path
            })

            await kafka_producer.send_deployment_request(
                repo_full_name=repo_full_name,
                framework_data=framework_data,
                user_id=str(user.get("id"))
            )

            print(f"✓ Successfully processed deployment request for {repo_full_name}")

        except Exception as e:
            print(f"Error processing deployment request: {e}")
            import traceback
            traceback.print_exc()



kafka_consumer = KafkaConsumerService(bootstrap_servers=os.getenv("KAFKA_BROKER"),
                                      username=os.getenv("KAFKA_USERNAME"),  # Из Vault через Nomad
                                      password=os.getenv("KAFKA_PASSWORD"))

