import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Eve Healthcare Assignment API"
    ENV: str = "development"
    DEBUG: bool = True

    # Database
    POSTGRES_USER: str = "eve_user"
    POSTGRES_PASSWORD: str = "eve_password"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "eve_healthcare_db"
    DATABASE_URL: str = "postgresql://eve_user:eve_password@localhost:5432/eve_healthcare_db"

    # Security
    SECRET_KEY: str = "supersecretkeyforlocaldevonly1234567890!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
