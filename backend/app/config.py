from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "霍尔木兹海峡油轮监测数据看板"
    DATABASE_URL: str = f"sqlite:///{Path(__file__).parent.parent / 'data.db'}"
    FIRMS_API_KEY: str = ""
    HTTP_PROXY: str | None = None
    HTTPS_PROXY: str | None = None
    COLLECTION_SCHEDULE_HOURS: list[int] = [6, 18]
    RISK_ASSESSMENT_HOUR: int = 8
    DATA_RETENTION_DAYS: int = 365
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
