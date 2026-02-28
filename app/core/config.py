from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramSettings(BaseModel):
    bot_token: str


class KafkaSettings(BaseModel):
    kafka_bootstrap_servers: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_file_encoding="utf-8"
        # env_nested_delimiter="__",
        # env_prefix="APP_CONFIG__"
    )
    tg: TelegramSettings = TelegramSettings()
    kafka: KafkaSettings = KafkaSettings()


settings = Settings()