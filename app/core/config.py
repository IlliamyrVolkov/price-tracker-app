from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class TelegramSettings(BaseModel):
    bot_token: str


class KafkaSettings(BaseModel):
    kafka_bootstrap_servers: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
    tg: TelegramSettings
    kafka: KafkaSettings


settings = Settings()
