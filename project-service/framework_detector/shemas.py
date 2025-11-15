from pydantic import BaseModel
from typing import Optional, List, Dict


class DetectFrameworkRequest(BaseModel):
    repo_full_name: str
    folder_path: Optional[str] = ""


class DeploymentRequest(BaseModel):
    repo_full_name: str
    folder_path: Optional[str] = ""
    user_id: Optional[str] = None
    framework: Optional[str] = None  # Ручной выбор фреймворка (если пользователь хочет переопределить автодетектор)
    secrets: Optional[Dict[str, str]] = None  # Секреты пользователя (ключ-значение)


class FrameworkDetectionResponse(BaseModel):
    repo: str
    frameworks: List[str]
    primary_framework: Optional[str]
    language: Optional[str]
    has_dockerfile: bool
    buildpack: str
    folder_path: Optional[str] = ""


class FrameworkListResponse(BaseModel):
    """Список всех поддерживаемых фреймворков"""
    frameworks: List[str]