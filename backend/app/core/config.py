from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (APP_*) and .env."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: Literal["development", "production", "test"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Browsers allowed to call the API. Production must list the real site origin(s) explicitly.
    cors_origins: list[str] = ["http://localhost:5173"]

    # Limits on what a visitor can send.
    max_message_chars: int = Field(500, ge=1)
    max_body_bytes: int = Field(256 * 1024, ge=1024)

    # Per-visitor rate limits on POST /api/chat (per client address).
    rate_limit_per_minute: int = Field(10, ge=1)
    rate_limit_per_day: int = Field(100, ge=1)
    # How many reverse proxies sit in front of the app (Render's load balancer is 1). Only then is
    # X-Forwarded-For trusted; 0 means use the direct connection address. Too high lets clients
    # spoof their address, so set it to the exact number of proxies you control.
    trusted_proxy_hops: int = Field(0, ge=0, le=5)

    # Which answering engine to use. Add a value here when registering a new engine in
    # app/services/answerer.py (ENGINES).
    answerer: Literal["stub", "llm"] = "stub"
    # Where the owner's Markdown knowledge base lives. Point it outside the repo to keep it private.
    knowledge_dir: Path = BACKEND_ROOT / "knowledge"
    # Also list posts marked `draft: true`, to preview them while writing. Never in production.
    show_drafts: bool = False

    # The name the assistant uses for the site owner (it calls itself "I" and him "he" or this).
    owner_name: str = Field("Site Owner", min_length=1)

    # The hosted LLM engine (APP_ANSWERER=llm). The key belongs in .env or a secret manager only.
    llm_api_key: SecretStr | None = None
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_max_tokens: int = Field(500, ge=1, le=4096)
    # Below the frontend's 30 second timeout, so the API answers (and stops spending) first.
    llm_timeout_seconds: float = Field(15.0, gt=0)
    # How many earlier turns are sent to the model; more turns cost more input tokens per question.
    llm_history_turns: int = Field(6, ge=0, le=20)
    # Price per million tokens, used to estimate spend from the token counts the API reports.
    llm_input_usd_per_mtok: float = Field(1.0, ge=0)
    llm_output_usd_per_mtok: float = Field(5.0, ge=0)

    # Spend ceilings for LLM answers (UTC calendar month and day). At a ceiling the engine stops
    # calling the model and shows the cap message; a question with an faq.md entry gets that answer.
    monthly_budget_usd: float = Field(1.5, gt=0)
    daily_budget_usd: float = Field(0.3, gt=0)
    # Where spend is counted: memory resets on restart (development); firestore survives it.
    usage_store: Literal["memory", "firestore"] = "memory"
    usage_collection: str = "usage"

    @model_validator(mode="after")
    def _production_never_shows_drafts(self) -> Self:
        if self.env == "production" and self.show_drafts:
            raise ValueError("APP_SHOW_DRAFTS must be off in production: drafts are unpublished.")
        return self

    @model_validator(mode="after")
    def _production_llm_must_be_capped_and_keyed(self) -> Self:
        if self.env == "production" and self.answerer == "llm":
            if self.llm_api_key is None:
                raise ValueError("APP_LLM_API_KEY is required in production with APP_ANSWERER=llm.")
            if self.usage_store != "firestore":
                raise ValueError(
                    "Production needs APP_USAGE_STORE=firestore: in memory, the spend cap "
                    "would reset whenever the app restarts."
                )
        return self

    @model_validator(mode="after")
    def _daily_budget_fits_the_month(self) -> Self:
        if self.daily_budget_usd > self.monthly_budget_usd:
            raise ValueError("APP_DAILY_BUDGET_USD cannot exceed APP_MONTHLY_BUDGET_USD.")
        return self

    @model_validator(mode="after")
    def _production_must_name_its_origins(self) -> Self:
        if self.env == "production":
            unsafe = [
                o for o in self.cors_origins if o == "*" or "localhost" in o or "127.0.0.1" in o
            ]
            if unsafe:
                raise ValueError(
                    "APP_CORS_ORIGINS must list the real site origin(s) in production, "
                    f"not a wildcard or localhost: {unsafe}"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
