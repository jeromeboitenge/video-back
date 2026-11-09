from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Frameforge API"
    environment: str = "development"
    database_url: str = "sqlite:///./frameforge.db"
    jwt_secret: str = "development-only-change-me"
    access_token_minutes: int = 30
    cors_origins: str = "http://localhost:5173"
    media_root: str = "./media"
    media_max_bytes: int = 524288000

    @model_validator(mode="after")
    def validate_runtime_security(self):
        env = self.environment.lower()
        if env not in {"development", "test", "staging", "production"}:
            raise ValueError("ENVIRONMENT must be one of: development, test, staging, production")

        if env in {"production", "staging"} and self.jwt_secret == "development-only-change-me":
            raise ValueError("JWT_SECRET must be configured to a unique secret in staging and production")
        if env in {"production", "staging"} and self.database_url.startswith("sqlite"):
            raise ValueError("Production deployments must use a non-SQLite database URL")
        if env in {"production", "staging"} and "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS cannot include wildcard '*' in production-like environments")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
