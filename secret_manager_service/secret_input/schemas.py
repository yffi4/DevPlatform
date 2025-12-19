from pydantic import BaseModel
from typing import Dict, Optional


class SecretRequest(BaseModel):
    """Request model for storing secrets"""
    project_id: str  
    secrets: Dict[str, str]  
    user_id: Optional[str] = None


class SecretResponse(BaseModel):
    """Response model for secret operations"""
    status: str
    message: str
    project_id: str
    secrets_count: int