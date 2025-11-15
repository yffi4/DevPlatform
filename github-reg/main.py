from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth.router import router as auth_router
from kafka_reg import producer
import os
app = FastAPI()

# CORS configuration
origins_env = os.getenv("FRONTEND_URL")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.on_event("startup")
async def startup():
    await producer.kafka_produser.start()

@app.on_event("shutdown")
async def shutdown():
    await producer.kafka_produser.stop()

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

