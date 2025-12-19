import json
import asyncio
from aiokafka import AIOKafkaConsumer
import hvac


class SecretManagerKafkaConsumer:
    """
    Kafka consumer for Secret Manager service
    Listens to project framework detection events and creates default secrets
    """

    def __init__(self, vault_client: hvac.Client):
        self.vault_client = vault_client
        self.bootstrap_servers = None
        self.username = None
        self.password = None
        self._fetch_kafka_credentials()
        self._consumer = None
        self._running = False

    def _fetch_kafka_credentials(self):
        """Fetch Kafka credentials from Vault using KV v2"""
        try:
            # For KV v2; adjust mount_point as needed (assuming 'secret' is the mount point)
            secret = self.vault_client.secrets.kv.v2.read_secret_version(
                path='secret_manager',
                mount_point='secret'
            )
            data = secret['data']['data']
            self.bootstrap_servers = data['broker']
            self.username = data['username']
            self.password = data['password']
            print("✓ Fetched Kafka credentials from Vault (KV v2)")
        except Exception as e:
            print(f"❌ Error fetching Kafka credentials from Vault: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def start(self):
        """Start Kafka consumer"""
        config = {
            "bootstrap_servers": self.bootstrap_servers,
            "value_deserializer": lambda m: json.loads(m.decode('utf-8')),
            "group_id": "secret-manager-service-group",
            "auto_offset_reset": 'latest'
        }

        # Use SASL only if username and password are available (from Vault)
        if self.username and self.password:
            config.update({
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": self.username,
                "sasl_plain_password": self.password,
            })

        self._consumer = AIOKafkaConsumer(
            "framework_detected",
            "user_registered",
            **config
        )
        await self._consumer.start()
        print(f"✓ Kafka consumer started, listening to 'framework_detected' topic")

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
                    print(f"📨 Received event: {data}")

                    # NOTE: Automatic default secrets creation has been disabled
                    # Users must explicitly save secrets via POST /secrets endpoint
                    # This prevents overwriting user-defined secrets with defaults
                    print(f"ℹ️  Event received but automatic secret creation is disabled")

                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"❌ Error in consumer loop: {e}")


# Global consumer instance (will be initialized in main.py)
kafka_consumer = None