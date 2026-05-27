from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database (depuis PR1)
    database_url: str
    test_database_url: str | None = None

    # JWT
    jwt_secret: str = "dev-secret-change-me-via-env-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 900       # 15 min
    refresh_token_ttl_seconds: int = 604800   # 7 jours

    # Cookies
    cookie_secure: bool = False
    cookie_domain: str = ""
    cookie_samesite: str = "lax"

    # Email
    email_provider: str = "console"
    email_from: str = "noreply@eldenforge.local"
    resend_api_key: str = ""

    # Front (pour les liens dans les emails)
    frontend_base_url: str = "http://localhost:5173"

    # Tokens TTL
    email_verification_ttl_seconds: int = 86400  # 24h
    password_reset_ttl_seconds: int = 3600       # 1h

    # Lockout (utilisé en PR2c, mais on déclare maintenant)
    max_failed_logins: int = 5
    lockout_duration_seconds: int = 900

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()  # type: ignore[call-arg]
