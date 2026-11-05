from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Frameforge API"
    database_url: str = "sqlite:///./frameforge.db"
    jwt_secret: str = "development-only-change-me"
    access_token_minutes: int = 30
    cors_origins: str = "http://localhost:5173"
    media_root: str = "./media"
    media_max_bytes: int = 524288000

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]



settings = Settings()
