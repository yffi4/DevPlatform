from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import hvac
import os
from secret_input.router import router as secret_input_router
from kafka.kafka_consumer import SecretManagerKafkaConsumer

app = FastAPI(
    title="Secret Manager Service",
    description="Microservice for managing secrets in HashiCorp Vault",
    version="1.0.0"
)

# CORS configuration
origins_env = os.getenv("FRONTEND_URL", "http://localhost:3000")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vault configuration
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault:8201")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root")

# Initialize Vault client
vault_client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)

# Initialize Kafka consumer (will be started in startup event)
kafka_consumer = None





@app.on_event("startup")
async def startup():
    """Initialize Vault connection, Kafka consumer, and ensure KV engine is enabled"""
    global kafka_consumer

    try:
        # Check if Vault is sealed
        if vault_client.sys.is_sealed():
            print("⚠️  Warning: Vault is sealed")
            return

        # Try to enable KV v2 secrets engine at 'secret/' if not exists
        try:
            vault_client.sys.enable_secrets_engine(
                backend_type='kv',
                path='secret',
                options={'version': '2'}
            )
            print("✓ KV secrets engine enabled at 'secret/'")
        except Exception as e:
            # Engine might already exist, which is fine
            if "path is already in use" not in str(e):
                print(f"⚠️  Note: {str(e)}")
            else:
                print("✓ KV secrets engine already exists at 'secret/'")

        print("✓ Secret Manager service started - Vault connection established")

        # Start Kafka consumer
        try:
            kafka_bootstrap_servers = os.getenv("KAFKA_BROKER", "kafka:9092")
            kafka_consumer = SecretManagerKafkaConsumer(
                vault_client=vault_client,
                bootstrap_servers=kafka_bootstrap_servers
            )
            await kafka_consumer.start()
            print("✓ Kafka consumer started successfully")
        except Exception as e:
            print(f"⚠️  Failed to start Kafka consumer: {str(e)}")

    except Exception as e:
        print(f"❌ Failed to initialize Vault: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    """Gracefully shutdown Kafka consumer"""
    global kafka_consumer

    if kafka_consumer:
        try:
            await kafka_consumer.stop()
            print("✓ Kafka consumer stopped")
        except Exception as e:
            print(f"⚠️  Error stopping Kafka consumer: {str(e)}")


@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "service": "secret-manager-service",
        "status": "running",
        "version": "1.0.0",
        "vault_addr": VAULT_ADDR
    }


@app.get("/health")
def health_check():
    """Health check for monitoring"""
    try:
        # Check Vault health
        health = vault_client.sys.read_health_status(method='GET')
        is_sealed = vault_client.sys.is_sealed()

        return {
            "status": "healthy" if not is_sealed else "degraded",
            "vault_sealed": is_sealed,
            "vault_initialized": health.get('initialized', False)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


app.include_router(secret_input_router)