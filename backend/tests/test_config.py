import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestDefaults:
    def test_are_safe_for_local_development(self) -> None:
        settings = Settings()

        assert settings.env == "development"
        assert settings.cors_origins == ["http://localhost:5173"]
        assert settings.rate_limit_per_minute == 10
        assert settings.rate_limit_per_day == 100
        assert settings.trusted_proxy_hops == 0
        assert settings.max_body_bytes == 256 * 1024
        assert settings.llm_max_tokens == 500

    def test_come_from_the_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_RATE_LIMIT_PER_MINUTE", "3")
        monkeypatch.setenv("APP_TRUSTED_PROXY_HOPS", "1")
        settings = Settings()
        assert (settings.rate_limit_per_minute, settings.trusted_proxy_hops) == (3, 1)


class TestValidation:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"rate_limit_per_minute": 0},
            {"rate_limit_per_day": 0},
            {"trusted_proxy_hops": -1},
            {"trusted_proxy_hops": 6},
            {"max_body_bytes": 10},
            {"max_message_chars": 0},
            {"log_level": "CHATTY"},
        ],
    )
    def test_rejects_nonsense_values(self, overrides: dict[str, object]) -> None:
        with pytest.raises(ValidationError):
            Settings(**overrides)  # type: ignore[arg-type]


class TestProductionOrigins:
    @pytest.mark.parametrize(
        "origins",
        [["*"], ["http://localhost:5173"], ["http://127.0.0.1:3000"], ["https://ok.example", "*"]],
    )
    def test_production_refuses_wildcard_and_local_origins(self, origins: list[str]) -> None:
        with pytest.raises(ValidationError, match="APP_CORS_ORIGINS"):
            Settings(env="production", cors_origins=origins)

    def test_production_accepts_the_real_site_origin(self) -> None:
        settings = Settings(env="production", cors_origins=["https://site.example"])
        assert settings.cors_origins == ["https://site.example"]

    def test_production_refuses_to_start_on_the_default_origin(self) -> None:
        with pytest.raises(ValidationError):
            Settings(env="production")

    def test_development_may_use_localhost(self) -> None:
        assert Settings(env="development", cors_origins=["http://localhost:5173"])


class TestLlmSettings:
    def test_defaults_match_the_owners_budget(self) -> None:
        settings = Settings()

        assert settings.llm_model == "claude-haiku-4-5-20251001"
        assert (settings.monthly_budget_usd, settings.daily_budget_usd) == (1.5, 0.3)
        assert settings.usage_store == "memory"
        assert settings.llm_api_key is None

    def test_the_key_is_never_shown_in_reprs(self) -> None:
        settings = Settings(llm_api_key="sk-very-secret")  # type: ignore[arg-type]

        assert "sk-very-secret" not in repr(settings)

    def test_a_daily_budget_above_the_monthly_one_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="DAILY_BUDGET"):
            Settings(monthly_budget_usd=1, daily_budget_usd=2)

    @pytest.mark.parametrize(
        "overrides",
        [
            {"monthly_budget_usd": 0},
            {"llm_max_tokens": 0},
            {"llm_timeout_seconds": 0},
            {"llm_history_turns": 21},
            {"usage_store": "redis"},
            {"owner_name": ""},
        ],
    )
    def test_rejects_nonsense_values(self, overrides: dict[str, object]) -> None:
        with pytest.raises(ValidationError):
            Settings(**overrides)  # type: ignore[arg-type]

    def test_production_llm_needs_a_key(self) -> None:
        with pytest.raises(ValidationError, match="APP_LLM_API_KEY"):
            Settings(
                env="production",
                cors_origins=["https://site.example"],
                answerer="llm",
                usage_store="firestore",
            )

    def test_production_llm_needs_a_persistent_spend_store(self) -> None:
        with pytest.raises(ValidationError, match="APP_USAGE_STORE=firestore"):
            Settings(
                env="production",
                cors_origins=["https://site.example"],
                answerer="llm",
                llm_api_key="sk-test",  # type: ignore[arg-type]
            )

    def test_production_llm_with_a_key_and_firestore_is_accepted(self) -> None:
        settings = Settings(
            env="production",
            cors_origins=["https://site.example"],
            answerer="llm",
            llm_api_key="sk-test",  # type: ignore[arg-type]
            usage_store="firestore",
        )
        assert settings.usage_store == "firestore"
