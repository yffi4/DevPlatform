from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, DateTime    
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password: Mapped[str] = mapped_column(String, unique=True, index=True)
    tokens: Mapped[list["Token"]] = relationship("Token", back_populates="user")
    
    
    github_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    github_username: Mapped[str] = mapped_column(String, unique=True, index=True)
    github_email: Mapped[str] = mapped_column(String, unique=True, index=True)

    github_token: Mapped["GitHubToken"] = relationship("GitHubToken", back_populates="user")


class Token(Base):
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user: Mapped["User"] = relationship("User", back_populates="tokens")



class GitHubToken(Base):
    __tablename__ = "github_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    access_token: Mapped[str] = mapped_column(String, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    user: Mapped["User"] = relationship("User", back_populates="github_token")

