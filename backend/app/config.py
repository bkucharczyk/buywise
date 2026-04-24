from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BuyWise API"
    app_env: str = "development"

    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_db_name: str = "buywise"

    redis_url: str = "redis://redis:6379/0"

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "mongodb://mongodb:27017/celery_results"

    qdrant_url: str = "http://qdrant:6333"
    r2r_url: str = "http://r2r:7272"

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-large"

    google_client_id: str = ""
    google_client_secret: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
