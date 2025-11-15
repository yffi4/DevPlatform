from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from framework_detector.router import router as project_router
import os
from project_kafka.kafka_producer import kafka_producer
from project_kafka.kafka_consumer import kafka_consumer





app = FastAPI(
    title="Project Service",
    description="Microservice for detecting project frameworks and triggering CI/CD pipelines",
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
    print("✓ Project service started - Kafka producer and consumer are running")

@app.on_event("shutdown")
async def shutdown():
    """Stop Kafka producer and consumer on app shutdown"""
    await kafka_consumer.stop()
    await kafka_producer.stop()
    print("✓ Project service stopped")

@app.get("/")
def read_root():
    """Health check endpoint"""
    return {
        "service": "project-service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    """Health check for monitoring"""
    return {"status": "healthy"}

app.include_router(project_router)
