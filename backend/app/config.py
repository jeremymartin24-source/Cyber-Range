from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-secret-key-change-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://cyberops:cyberops_dev@db:5432/cyberops"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # Wazuh integration (all optional — set to enable live alert ingestion)
    wazuh_url: str | None = None  # e.g. https://wazuh-manager:55000
    wazuh_user: str = "wazuh-wui"
    wazuh_password: str = ""
    wazuh_verify_tls: bool = True  # set False only for self-signed certs in dev
    wazuh_ingest_secret: str = ""  # shared secret for POST /wazuh/{org_id}/ingest
    wazuh_poll_interval_seconds: int = 60  # how often the beat task polls Wazuh

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def wazuh_enabled(self) -> bool:
        return bool(self.wazuh_url)


settings = Settings()
