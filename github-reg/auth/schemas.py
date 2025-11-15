from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    id: int
    username: str
    email: str
    password: str
    scope: str
    github_id: str
    github_username: str
    github_email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    id: int
    access_token: str
    access_scope: str
    token_type: str
    expires_in: int


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str

class GitHubUser(BaseModel):
    id: int
    username: str
    email: str
    access_token: str
    expires_at: datetime

class GitHubToken(BaseModel):
    access_token: str
    expires_at: datetime

class GitHubTokenCreate(BaseModel):
    access_token: str
    expires_at: datetime

class GitHubTokenUpdate(BaseModel):
    access_token: str
    expires_at: datetime

class GitHubTokenDelete(BaseModel):
    access_token: str

class DeployRequest(BaseModel):
    owner: str
    repo: str
    folder_path: str = ""  