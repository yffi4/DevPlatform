import json
import asyncio
from aiokafka import AIOKafkaConsumer
from typing import Dict
import os
from dotenv import load_dotenv
load_dotenv()      


class KafkaConsumerService:
    """
    Kafka consumer for listening to deployment-related events
    """

    def __init__(self, bootstrap_servers: str = "kafka.service.consul:9092", username: str = "", password: str = "", sasl_mechanism: str = "PLAIN", security_protocol: str = "SASL_PLAINTEXT"):
        self.bootstrap_servers = bootstrap_servers
        self._consumer = None
        self._running = False
        self.secrets_cache: Dict[str, Dict] = {}
        self.username = username
        self.password = password
        self.sasl_mechanism = sasl_mechanism
        self.security_protocol = security_protocol
        self.framework_cache: Dict[str, Dict] = {}
        self.user_cache: Dict[str, Dict] = {}  # access_token -> {user_id, username} mapping

    async def start(self):
        """Start Kafka consumer"""
        self._consumer = AIOKafkaConsumer(
            "deployment_requested",     # From project-service
            "secrets_stored",           # From secret-manager
            "project_framework_detected",
            "user_registered",  # From project-service
            "repos_resp",  # From project-service
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id="deployment-service-group",
            auto_offset_reset='latest',
            # SASL / Security config
            security_protocol=self.security_protocol,
            sasl_mechanism=self.sasl_mechanism,
            sasl_plain_username=self.username,
            sasl_plain_password=self.password
        )
        await self._consumer.start()
        print(f"✓ Deployment Service Kafka consumer started")
        print(f"  Listening to: deployment_requested, secrets_stored, project_framework_detected, user_registered")

        self._running = True
        asyncio.create_task(self._consume_messages())

    async def stop(self):
        """Stop Kafka consumer"""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            print("✓ Deployment Service Kafka consumer stopped")

    async def _consume_messages(self):
        """Consume messages from Kafka topics"""
        try:
            async for message in self._consumer:
                if not self._running:
                    break

                try:
                    data = message.value
                    topic = message.topic

                    if topic == "deployment_requested":
                        await self._handle_deployment_requested(data)
                    elif topic == "secrets_stored":
                        await self._handle_secrets_stored(data)
                    elif topic == "project_framework_detected":
                        await self._handle_framework_detected(data)
                    elif topic == "user_registered":
                        await self._handle_user_registered(data)

                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"❌ Error in consumer loop: {e}")

    async def _handle_deployment_requested(self, data: Dict):
        """
        Handle deployment request from project-service
        
        Expected data:
        {
            "event_type": "deployment_requested",
            "repo": "owner/repo",
            "user_id": "123",
            "framework": "nextjs",
            "language": "javascript",
            "buildpack": "nodejs",
            "has_dockerfile": false,
            "configuration": {...}
        }
        """
        print(f"📦 Received deployment request: {data.get('repo')}")
        
        # Cache this for when user triggers deployment via UI
        repo = data.get("repo")
        if repo:
            self.framework_cache[repo] = data
            print(f"  ✓ Cached framework data for {repo}")

    async def _handle_secrets_stored(self, data: Dict):
        """
        Handle secrets stored event from secret-manager
        
        Expected data:
        {
            "event_type": "secrets_stored",
            "project_id": "owner/repo",
            "user_id": "123",
            "secrets_count": 5
        }
        """
        print(f"🔐 Secrets stored for project: {data.get('project_id')}")
        
        project_id = data.get("project_id")
        if project_id:
            self.secrets_cache[project_id] = data
            print(f"  ✓ Cached secrets info for {project_id}")

    async def _handle_framework_detected(self, data: Dict):
        """
        Handle framework detection event from project-service

        Expected data:
        {
            "event_type": "project_framework_detected",
            "project_id": "owner/repo",
            "framework": "nextjs",
            "language": "javascript",
            "user_id": "123"
        }
        """
        print(f"🔍 Framework detected: {data.get('framework')} for {data.get('project_id')}")

        project_id = data.get("project_id")
        if project_id:
            self.framework_cache[project_id] = data
            print(f"  ✓ Cached framework for {project_id}")

    async def _handle_user_registered(self, data: Dict):
        """
        Handle user registration event

        Expected data:
        {
            "user": {
                "id": 123,
                "login": "username",
                "github_token": "gho_xxx"
            }
        }
        """
        user_data = data.get("user", {})
        user_id = str(user_data.get("id"))
        github_token = user_data.get("github_token")
        login = user_data.get("login")

        if user_id and github_token and login:
            self.user_cache[github_token] = {
                "user_id": user_id,
                "username": login
            }
            print(f"👤 User registered: {login} (ID: {user_id})")
            print(f"  ✓ Cached user mapping for token")

    def get_cached_secrets(self, project_id: str) -> Dict:
        """Get cached secrets data for a project"""
        return self.secrets_cache.get(project_id, {})

    def get_cached_framework(self, project_id: str) -> Dict:
        """Get cached framework data for a project"""
        return self.framework_cache.get(project_id, {})

    def get_user_id_by_token(self, access_token: str) -> str:
        """Get user ID by access token"""
        user_data = self.user_cache.get(access_token, {})
        if isinstance(user_data, dict):
            return user_data.get("user_id", "")
        return user_data  # Backward compatibility

    def get_user_info_by_token(self, access_token: str) -> Dict[str, str]:
        """Get user info (user_id and username) by access token"""
        user_data = self.user_cache.get(access_token, {})
        if isinstance(user_data, dict):
            return user_data
        # Backward compatibility - if it's a string (old format)
        return {"user_id": user_data, "username": ""}


# Global consumer instance
kafka_consumer = KafkaConsumerService(bootstrap_servers=os.getenv("KAFKA_BROKER"), 
    sasl_mechanism=os.getenv("KAFKA_SASL_MECHANISM"),
    security_protocol=os.getenv("KAFKA_SECURITY_PROTOCOL"),
    username=os.getenv("KAFKA_USERNAME"),
    password=os.getenv("KAFKA_PASSWORD"))
