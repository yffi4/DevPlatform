import os
import datetime 

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import get_db
from models import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_user(db: Session, user):
    # user is a Pydantic UserCreate
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        password=hashed_password,
        email=user.email,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user(db: Session, username: str) -> User | None:
    result = db.execute(select(User).filter(User.username == username))
    return result.scalar_one_or_none()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def create_access_token(
    data: dict,
    expires_delta: datetime.timedelta | None = None,
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = get_user(db, username)
    if user is None:
        raise credentials_exception
    return user

def get_github_user(db: Session, github_id: str) -> User | None:
    result = db.execute(select(User).filter(User.github_id == github_id))
    return result.scalar_one_or_none()

def get_github_token(db: Session, user_id: int) -> str | None:
    result = db.execute(select(User.github_token).filter(User.id == user_id))
    return result.scalar_one_or_none().access_token



