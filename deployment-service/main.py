from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from deployment_router import router as deployment_router
from deployment_kafka.kafka_producer import kafka_producer
from deployment_kafka.kafka_consumer import kafka_consumer
import os

app = FastAPI(
    title="Deployment Service",
    description="Microservice for deploying user applications to Nomad",
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

@app.on_event("startup")
async def startup():
    """Start Kafka producer and consumer on app startup"""
    await kafka_producer.start()
    await kafka_consumer.start()
    print("✓ Deployment service started - Kafka producer and consumer are running")

@app.on_event("shutdown")
async def shutdown():
    """Stop Kafka producer and consumer on app shutdown"""
    await kafka_consumer.stop()
    await kafka_producer.stop()
    print("✓ Deployment service stopped")

@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "service": "deployment-service",
        "status": "running",
        "version": "1.0.0",
        "kafka": "connected"
    }

@app.get("/health")
def health_check():
    """Health check for monitoring"""
    return {"status": "healthy"}

app.include_router(deployment_router, prefix="/api", tags=["deployments"])
