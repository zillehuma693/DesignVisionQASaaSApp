from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "VisionQA"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    public_base_url: str = "http://localhost:8000"

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "visionqa"

    jwt_secret_key: str = "change-me-to-a-long-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    remember_me_expire_days: int = 30
    cookie_secure: bool = False
    frontend_url: str = "http://localhost:5173"

    resend_api_key: str = ""
    resend_from_email: str = "VisionQA <onboarding@resend.dev>"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/google/callback"
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/github/callback"

    storage_path: str = "./storage"
    screenshots_path: str = "./storage/screenshots"
    reports_path: str = "./storage/reports"

    playwright_headless: bool = True
    scan_max_pages: int = 10
    scan_timeout_ms: int = 30000

    crawl_max_nodes: int = 25
    crawl_max_actions_per_node: int = 15
    crawl_max_duration_seconds: int = 180

    responsive_max_nodes: int = 15
    responsive_max_duration_seconds: int = 150

    fill_forms_max_nodes: int = 15
    fill_forms_max_duration_seconds: int = 120

    axe_max_nodes: int = 15
    axe_timeout_ms: int = 8000

    perf_lcp_warn_ms: int = 2500
    perf_lcp_bad_ms: int = 4000
    perf_cls_warn: float = 0.1
    perf_cls_bad: float = 0.25
    perf_ttfb_warn_ms: int = 800
    perf_slow_request_ms: int = 3000

    auth_encryption_key: str = "dev-only-insecure-key-change-in-production"
    auth_session_ttl_seconds: int = 900

    ai_provider: str = "none"
    ai_enabled: bool = False
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
