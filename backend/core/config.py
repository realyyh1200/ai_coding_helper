from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Coding Website"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ai_coding.db")

    ANTHROPIC_API_BASE: str = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
