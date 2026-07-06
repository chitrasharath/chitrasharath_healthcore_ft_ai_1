from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    incident_analyzer_path: str = "../../uis/incident_analyzer"
    secret_key: str
    jwt_expire_minutes: int
    email_api_key: str = ""
    frontend_url: str = "http://localhost:3001"
    database_url: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
