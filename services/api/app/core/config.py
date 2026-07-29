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
    telemetry_endpoint: str = ""

    llm_base_url: str = "https://llm.4geeks.ai"
    llm_api_key: str = ""
    embedding_model: str = (
        "downtown-miami/openrouter/perplexity/pplx-embed-v1-0.6b"
    )
    generation_model: str = (
        "downtown-miami/openrouter/deepseek/deepseek-v4-flash"
    )
    qdrant_path: str = "./data/qdrant"
    qdrant_collection: str = "company_knowledge_base"
    rag_top_k: int = 3
    rag_min_score: float = 0.30
    feedback_path: str = "./data/eval/feedback.jsonl"
    rag_generation_temperature: float = 0.15
    rag_question_max_length: int = 1000

    # Agent → company-tools MCP (Keycloak client_credentials)
    mcp_company_tools_url: str = "http://localhost:9000/mcp"
    keycloak_token_url: str = (
        "http://localhost:8080/realms/healthcore/protocol/openid-connect/token"
    )
    keycloak_client_id: str = "agent-support"
    keycloak_client_secret: str = "agent-support-dev-secret"

    # Agent harness / guardrails (in-process; kill-switch disables IG/ISO/OG/OBS)
    guardrails_enabled: bool = True
    guardrail_classifier_enabled: bool = True
    guardrail_phi_detection_enabled: bool = True
    guardrail_preview_max_chars: int = 80

    # Agent long-term memory (Redis SoT + Qdrant recall; kill-switch disables nodes)
    memory_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    memory_qdrant_collection: str = "agent_memory"
    memory_recall_k: int = 5
    memory_entry_ttl_days: int = 90
    memory_pending_ttl_minutes: int = 30
    memory_max_entries_per_scope: int = 50
    memory_dedupe_threshold: float = 0.92
    memory_low_relevance_days: int = 30
    memory_summarize_min_cluster: int = 3

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
