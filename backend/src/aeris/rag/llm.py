from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from aeris.config import Settings
from aeris.rag.errors import ConfigError

DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4o-mini"}


def build_chat_model(settings: Settings) -> BaseChatModel | None:
    """None means retrieval-only mode (no key needed)."""
    provider = settings.llm_provider
    if provider == "none":
        return None
    if settings.llm_api_key is None:
        raise ConfigError(f"LLM_PROVIDER={provider} requires LLM_API_KEY")
    model = settings.llm_model or DEFAULT_MODELS[provider]
    key = settings.llm_api_key.get_secret_value()
    try:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model, api_key=key, temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model, api_key=key, temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
    except ImportError as exc:  # pragma: no cover - optional extras
        raise ConfigError(f'Run: pip install -e ".[{provider}]"') from exc
