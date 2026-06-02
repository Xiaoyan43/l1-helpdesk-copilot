"""集中配置。从环境变量 / .env 读取。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM (Claude) ---
    anthropic_api_key: str | None = None
    classify_model: str = "claude-haiku-4-5"   # 分类用便宜快的 Haiku；想更准可换 claude-sonnet-4-6 / claude-opus-4-8
    respond_model: str = "claude-sonnet-4-6"   # 写回复用 Sonnet
    use_mock_llm: bool = True   # True=本地规则基线，不调用 API

    # --- Microsoft Graph (lab 租户) ---
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: str | None = None
    graph_dry_run: bool = True  # True=只演练，不真的修改租户

    # --- 路径 ---
    kb_dir: str = "kb"
    audit_log_path: str = "audit_log.jsonl"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        # 让 .env 优先于进程环境变量：避免外部空的 ANTHROPIC_API_KEY 等盖住 .env。
        return init_settings, dotenv_settings, env_settings, file_secret_settings


@lru_cache
def get_settings() -> Settings:
    return Settings()
