from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Minimal Agent Chatbot"
    debug: bool = Field(default=True, alias="DEBUG")

    api_prefix: str = "/api"

    openai_api_key: str = Field(default="lmstudio", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="http://localhost:1234/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="nvidia/nemotron-3-nano-4b", alias="OPENAI_MODEL")

    max_output_tokens: int = Field(default=1024, alias="MAX_OUTPUT_TOKENS")
    max_tool_iterations: int = Field(default=8, alias="MAX_TOOL_ITERATIONS")
    request_timeout_seconds: float = Field(default=60.0, alias="REQUEST_TIMEOUT_SECONDS")

    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")

    auth_enabled: bool = False
    dev_user_id: str = "dev-user-0001"
    dev_user_email: str = "dev@example.com"

    database_url: str = Field(default="sqlite+aiosqlite:///./dev.db", alias="DATABASE_URL")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite+")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql+")


settings = Settings()
